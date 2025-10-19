from sqlalchemy import text
import asyncio
import time
import telegramify_markdown
import openai
import random
from db import engine
import json
from faq_rag.faq_rag import ask_faq
from saving_strategies import generate_saving_strategies
import logging
from dotenv import load_dotenv
import os
import telegram
from telegram import Update,InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import openai_client
from conversation import Conversation
from llm_tools import tools
from quick_replies import create_quick_replies, generate_quick_replies
from analytics import get_user_financial_summary
from pydub import AudioSegment
from investment_advice import generate_investment_recommendations, get_risk_level_str
from user_grouping import prepare_knn_and_aggregated_data, find_relevant_goal_comparisons


load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is missing in .env")

nn = None
X = None
features = None
bank_user_id = None
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

    reply_text, images = await generate_reply_text(conversation)
    conversation.add_assistant_message(reply_text)

    quick_options = await generate_quick_replies(conversation)

    logging.debug(json.dumps(conversation.get_serializable_history()))
    return reply_text, images, quick_options


async def generate_reply_text(conversation: Conversation) -> str:
    images = None

    logging.info("=== generate_reply_text START ===")

    instructions = None
    is_conversation_start = conversation.should_greet()
    logging.info(f"is_conversation_start: {is_conversation_start}")

    if is_conversation_start:
        instructions = 'Start your response with "Здравствуйте!"'
        conversation.mark_as_returning()

    messages = conversation.get_recent_history(10)
    messages = [
        msg
        for msg in messages
        if isinstance(msg, dict) and "content" in msg and msg["content"] is not None
    ]

    try:
        loop = asyncio.get_event_loop()
        last_message = next(
            (msg["content"] for msg in reversed(messages)),
            "",
        )

        faq_query = last_message
        start = time.time()
        faq_reply = await loop.run_in_executor(None, ask_faq, faq_query)
        end = time.time()
        print(f"It took {start - end} seconds to ask_faq")
        faq_reply = str(faq_reply)
        logging.info(f"FAQ reply: {faq_reply}")
    except Exception as e:
        logging.error(f"FAQ retrieval error: {e}")
        raise e
        faq_reply = "No FAQ information available."

    messages.append({"role": "developer", "content": "FAQ RAG: " + faq_reply})
    logging.info(f"Messages after FAQ append: {messages}")

    try:
        print()
        print("FIRST CALL", messages)
        print()
        start = time.time()
        response = await openai_client.client.responses.create(
            model="gpt-4o-mini",
            tools=tools,
            instructions=instructions,
            input=messages,
        )
        end = time.time()
        print(
            f"It took {start - end} seconds to do first openai call"
        )  # regular output if no function
        logging.info(f"Raw OpenAI response: {response}")
    except Exception as e:
        logging.error(f"OpenAI API call failed: {e}")
        return "Error generating response."

    messages = conversation.get_history_copy()
    messages += response.output

    has_function_call = False
    for item in response.output:
        logging.info(f"Processing response item: {item}")
        if item.type == "function_call":
            has_function_call = True
            logging.info(f"Detected function call: {item.name}")
            if item.name == "generate_saving_strategies":
                loop = asyncio.get_event_loop()
                args = json.loads(item.arguments)

                start = time.time()
                strategies = await loop.run_in_executor(
                    None,
                    generate_saving_strategies,
                    args["financial_goal"],
                    args["current_balance"],
                    args["monthly_savings"],
                )
                end = time.time()
                print(f"It took {start - end} seconds to do generate_saving_strategy")
                logging.info(f"Function call result: {strategies}")
                messages.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps({"strategies": strategies}),
                    }
                )
                logging.info("Re-generating response after function call output")
            elif item.name == "get_user_financial_summary":
                args = json.loads(item.arguments)
                analytics = await get_user_financial_summary(bank_user_id, args["last_n_days"])
                print(analytics)
                print(analytics["graphs"])
                images = [analytics["graphs"]["pie_chart"], analytics["graphs"]["line_chart"]]
                analytics["graphs"] = None
                messages.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps({"analytics": analytics}),
                    }
                )
            elif item.name == "get_investment_recommendations":
                args = json.loads(item.arguments)
                recommendations = await generate_investment_recommendations(
                    get_risk_level_str(args["risk_level"])
                )
                messages.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps({"recommendations": recommendations}),
                    }
                )
            elif item.name == "compare_goals":
                args = json.loads(item.arguments)
                goals = await find_relevant_goal_comparisons(
                    bank_user_id, nn, X, features
                )
                messages.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps({"top_3_relevant_goals": goals}),
                    }
                )


    if has_function_call:
        start = time.time()
        response = await openai_client.client.responses.create(
            model="gpt-4o-mini",
            tools=tools,
            instructions="Present the result of the function call in the context of the conversation. Derive insights from the data and make calls to action for the user.",
            input=messages,
        )
        end = time.time()
        print(
            f"It took {start - end} seconds to ask chatgpt to present the function call result"
        )
        logging.info(f"Final response after function call: {response}")

    output_text = response.output_text if hasattr(response, "output_text") else ""
    logging.info(f"Final output_text before markdownify: {output_text}")

    markdown_text = telegramify_markdown.markdownify(
        output_text, max_line_length=None, normalize_whitespace=False
    )
    logging.info(f"Final markdown_text: {markdown_text}")
    logging.info("=== generate_reply_text END ===")

    return markdown_text, images


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stop_event = asyncio.Event()
    typing_task = asyncio.create_task(
        send_typing_action_periodically(update.effective_chat.id, stop_event)
    )

    try:
        reply, _, quick_options = await generate_reply(
            update.effective_user.id, "Список функционала"
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
        reply, images, quick_options = await generate_reply(
            update.effective_user.id, update.message.text
        )
        if images:
            await update.message.reply_media_group(
                [InputMediaPhoto(media=x) for x in images],
                caption=reply,
                parse_mode="MarkdownV2",
            )
        else:
            await update.message.reply_text(
                reply,
                reply_markup=create_quick_replies(quick_options),
                parse_mode="MarkdownV2",
            )
    finally:
        stop_event.set()
        await typing_task


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stop_event = asyncio.Event()
    typing_task = asyncio.create_task(
        send_typing_action_periodically(update.effective_chat.id, stop_event)
    )

    try:
        voice = update.message.voice
        if not voice:
            return

        # Download voice message
        file = await context.bot.get_file(voice.file_id)
        ogg_path = f"./media/voice_{voice.file_unique_id}.ogg"
        await file.download_to_drive(ogg_path)

        if not os.path.exists(ogg_path):
            print("[ERROR] Downloaded file does not exist!")
            return

        # Convert OGG to WAV (Whisper can handle OGG too, but WAV is safer)
        wav_path = f"./media/voice_{voice.file_unique_id}.wav"
        AudioSegment.from_ogg(ogg_path).export(wav_path, format="wav")

        if not os.path.exists(wav_path):
            print("[ERROR] WAV file was not created!")
            return

        wav_size = os.path.getsize(wav_path)
        print(f"[INFO] WAV file size: {wav_size} bytes")
        if wav_size == 0:
            print("[ERROR] WAV file is empty!")
            return

        # Transcribe with Whisper
        audio_file = open(wav_path, "rb")

        transcript = openai.audio.transcriptions.create(
            model="whisper-1", file=audio_file
        )
        logging.info("Voice transcript:", transcript.text)

        reply, quick_options = await generate_reply(
            update.effective_user.id, transcript.text
        )
        await update.message.reply_text(
            reply,
            reply_markup=create_quick_replies(quick_options),
            parse_mode="MarkdownV2",
        )
    except Exception as e:
        raise e
    finally:
        stop_event.set()
        await typing_task


async def main():
    global bank_user_id

    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT id FROM users OFFSET 51 LIMIT 1"))
        bank_user_id = result.scalar()
    nn, X, features = await prepare_knn_and_aggregated_data()
    logging.basicConfig(level=logging.INFO)
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    app.add_handler(MessageHandler(filters.TEXT, message_handler))
    print("🚀 Bot is starting...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    # Keep running until interrupted
    await asyncio.Event().wait()

    # Cleanup
    await app.updater.stop()
    await app.stop()
    await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
