import telegramify_markdown
import openai
import json
from faq_rag.faq_rag import ask_faq
from saving_strategies import generate_saving_strategies
import logging
from dotenv import load_dotenv
import os
import telegram
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import asyncio
from conversation import Conversation
from llm_tools import tools
from quick_replies import create_quick_replies, generate_quick_replies

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is missing in .env")

app = ApplicationBuilder().token(BOT_TOKEN).build()

conversations: dict[int, Conversation] = {}

def get_or_create_conversation(user_id: int) -> Conversation:
    """Get existing conversation or create a new one."""
    if user_id not in conversations:
        conversations[user_id] = Conversation(user_id)
    return conversations[user_id]


async def send_typing_action_periodically(chat_id: int, stop_event: asyncio.Event):
    """Send typing action every 3 seconds until stop_event is set."""
    while not stop_event.is_set():
        try:
            await app.bot.send_chat_action(
                chat_id=chat_id, action=telegram.constants.ChatAction.TYPING
            )
        except Exception as e:
            logging.error(f"Error sending typing action: {e}")
        
        # Wait 3 seconds or until stop_event is set
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            continue


async def generate_reply(user_id: int, text: str) -> tuple[str, list[str]]:
    conversation = get_or_create_conversation(user_id)

    conversation.add_user_message(text)

    reply_text = await generate_reply_text(conversation)
    conversation.add_assistant_message(reply_text)

    quick_options = await generate_quick_replies(conversation)

    logging.debug(json.dumps(conversation.get_serializable_history()))
    return reply_text, quick_options


async def generate_reply_text(conversation: Conversation) -> str:
    instructions = None
    is_conversation_start = conversation.should_greet()

    if conversation.should_greet():
        instructions = 'Start your response with a greeting like "Здравствуйте!"'
        conversation.mark_as_returning()

    messages = conversation.get_recent_history(10)

    try:
        # Run FAQ retrieval in executor to avoid blocking
        loop = asyncio.get_event_loop()
        last_message = messages[-1]["content"]
        faq_query = last_message
        if is_conversation_start:
            faq_query = "Перечисли услуги банка и основные вопросы"
        faq_reply = await loop.run_in_executor(None, ask_faq, faq_query)
        faq_reply = str(faq_reply)
    except Exception as e:
        logging.error(f"FAQ retrieval error: {e}")
        faq_reply = "No FAQ information available."

    messages.append({"role": "developer", "content": "FAQ RAG: " + faq_reply})

    # Create async OpenAI client
    client = openai.AsyncOpenAI(api_key=openai.api_key)

    response = await client.responses.create(
        model="gpt-4o-mini",
        tools=tools,
        instructions=instructions,
        input=messages,
    )

    has_function_call = False
    for item in response.output:
        if item.type == "function_call":
            has_function_call = True
            if item.name == "generate_saving_strategies":
                # Run function in executor to avoid blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, generate_saving_strategies, json.loads(item.arguments)
                )
                conversation.add_function_call_output(
                    call_id=item.call_id, output=json.dumps(result)
                )

    if has_function_call:
        response = await client.responses.create(
            model="gpt-4o-mini",
            tools=tools,
            instructions="Present the result of the function call in the context of the conversation.",
            input=conversation.get_recent_history(5),
        )

    return telegramify_markdown.markdownify(
        response.output_text, max_line_length=None, normalize_whitespace=False
    )


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stop_event = asyncio.Event()
    typing_task = asyncio.create_task(
        send_typing_action_periodically(update.effective_chat.id, stop_event)
    )
    
    try:
        reply, quick_options = await generate_reply(
            update.effective_user.id, "Здравствуйте! Я клиент банка."
        )
        await update.message.reply_text(
            reply,
            reply_markup=create_quick_replies(quick_options),
            parse_mode="MarkdownV2",
        )
    finally:
        stop_event.set()
        await typing_task


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stop_event = asyncio.Event()
    typing_task = asyncio.create_task(
        send_typing_action_periodically(update.effective_chat.id, stop_event)
    )
    
    try:
        reply, quick_options = await generate_reply(
            update.effective_user.id, update.message.text
        )
        await update.message.reply_text(
            reply,
            reply_markup=create_quick_replies(quick_options),
            parse_mode="MarkdownV2",
        )
    finally:
        stop_event.set()
        await typing_task


def main():
    logging.basicConfig(level=logging.INFO)
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(MessageHandler(filters.ALL, message_handler))
    print("🚀 Bot is starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
