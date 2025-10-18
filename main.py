import copy
import telegramify_markdown
import openai
import json
from faq_rag.faq_rag import ask_faq
from saving_strategies import generate_saving_strategies
import logging
from dotenv import load_dotenv
import os
import telegram
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import asyncio

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is missing in .env")

app = ApplicationBuilder().token(BOT_TOKEN).build()

tools = [
    {
        "type": "function",
        "strict": True,
        "name": "generate_savings_strategies",
        "description": "Generate saving strategies based on bank's services.",
        "parameters": {
            "type": "object",
            "properties": {
                "financial_goal": {
                    "type": "integer",
                    "description": "The client's financial goal in KZT.",
                },
                "current_balance": {
                    "type": "integer",
                    "description": "The client's current balance in KZT.",
                },
                "monthly_savings": {
                    "type": "integer",
                    "description": "How much the client saves monthly.",
                },
            },
            "required": ["financial_goal", "current_balance", "monthly_savings"],
            "additionalProperties": False,
        },
    },
]


class Conversation:
    SYSTEM_PROMPT = "Ты цифровой ассистент банка ZamanBank. Твоя цель помочь клиенту банка. Отвечай на вопросы клиента как справочник: напрямую и полностью, без введения или заключения. Пытайся использовать functions если это уместно. Если не хватает данных для вызовы функции, спроси их у пользователя. При запросе данных у пользователя спрашивай по одному полю за раз и не предлагай контекстных действий."

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.history: list[dict[str, str]] = []
        self.is_new_conversation = True
        self._initialize_history()

    def _initialize_history(self):
        """Initialize conversation with system prompt."""
        self.add_developer_message(self.SYSTEM_PROMPT)

    def add_user_message(self, content: str):
        """Add a user message to the conversation history."""
        self.history.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str):
        """Add an assistant message to the conversation history."""
        self.history.append({"role": "assistant", "content": content})

    def add_developer_message(self, content: str):
        """Add a developer message to the conversation history."""
        self.history.append({"role": "developer", "content": content})

    def add_function_call_output(self, call_id: str, output: str):
        """Add a function call output to the conversation history."""
        self.history.append(
            {
                "type": "function_call_output",
                "call_id": call_id,
                "output": output,
            }
        )

    def get_history_copy(self) -> list[dict]:
        """Return a deep copy of the conversation history."""
        return copy.deepcopy(self.history)

    def get_recent_history(self, n: int = 10) -> list[dict]:
        """Return a deep copy of the last n elements from conversation history."""
        return copy.deepcopy(self.history[-n:] if n > 0 else self.history)

    def mark_as_returning(self):
        """Mark conversation as no longer new."""
        self.is_new_conversation = False

    def should_greet(self) -> bool:
        """Check if this is a new conversation that needs greeting."""
        return self.is_new_conversation

    def get_serializable_history(self) -> list[dict]:
        """Return a JSON-serializable version of the history."""
        serializable = []
        for item in self.history:
            if isinstance(item, dict):
                # Only include simple dict items, not complex API response objects
                if all(
                    isinstance(v, (str, int, float, bool, type(None)))
                    for v in item.values()
                ):
                    serializable.append(item)
        return serializable


conversations: dict[int, Conversation] = {}


def create_quick_replies(options: list[str]) -> ReplyKeyboardMarkup:
    """Create reply keyboard markup from quick reply options."""
    if not options:
        return ReplyKeyboardRemove()

    keyboard = []
    row = []
    for i, opt in enumerate(options):
        if opt and opt.strip():  # Only add non-empty options
            row.append(KeyboardButton(text=opt))
            # Add row when we have 2 buttons or it's the last option
            if len(row) == 2 or i == len(options) - 1:
                keyboard.append(row)
                row = []

    return (
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        if keyboard
        else ReplyKeyboardRemove()
    )


def get_or_create_conversation(user_id: int) -> Conversation:
    """Get existing conversation or create a new one."""
    if user_id not in conversations:
        conversations[user_id] = Conversation(user_id)
    return conversations[user_id]


async def process_user_input(user_id: int, text: str) -> tuple[str, list[str]]:
    conversation = get_or_create_conversation(user_id)

    conversation.add_user_message(text)

    reply = await generate_reply(conversation)
    conversation.add_assistant_message(reply)

    quick_options = await generate_quick_replies(conversation)

    logging.debug(json.dumps(conversation.get_serializable_history()))
    return reply, quick_options


async def generate_reply(conversation: Conversation) -> str:
    instructions = None

    if conversation.should_greet():
        instructions = 'Start your response with a greeting like "Здравствуйте!"'
        conversation.mark_as_returning()

    messages = conversation.get_recent_history(10)

    try:
        # Run FAQ retrieval in executor to avoid blocking
        loop = asyncio.get_event_loop()
        faq_reply = await loop.run_in_executor(
            None, ask_faq, messages[-1]["content"]
        )
        faq_reply = str(faq_reply)
    except Exception as e:
        logging.error(f"FAQ retrieval error: {e}")
        faq_reply = "No FAQ information available."

    messages.append({"role": "developer", "content": "FAQ RAG: " + faq_reply})

    # Create async OpenAI client
    client = openai.AsyncOpenAI(api_key=openai.api_key)
    
    response = await client.responses.create(
        model="gpt-5-mini",
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
    await app.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING
    )
    reply, quick_options = await process_user_input(
        update.effective_user.id, "Здравствуйте! Я клиент банка."
    )
    await update.message.reply_text(
        reply,
        reply_markup=create_quick_replies(quick_options),
        parse_mode="MarkdownV2",
    )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await app.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING
    )
    reply, quick_options = await process_user_input(
        update.effective_user.id, update.message.text
    )
    await update.message.reply_text(
        reply,
        reply_markup=create_quick_replies(quick_options),
        parse_mode="MarkdownV2",
    )


async def generate_quick_replies(conversation: Conversation) -> list[str]:
    messages = conversation.get_recent_history()

    try:
        # Run FAQ retrieval in executor to avoid blocking
        loop = asyncio.get_event_loop()
        faq_input = (messages[-1]["content"]) + "\n" + (messages[-2]["content"])
        faq_reply = await loop.run_in_executor(None, ask_faq, faq_input)
        faq_reply = str(faq_reply)
    except Exception as e:
        logging.error(f"FAQ retrieval error: {e}")
        faq_reply = "No FAQ information available."

    messages.append({"role": "developer", "content": "FAQ RAG: " + faq_reply})

    # Create async OpenAI client
    client = openai.AsyncOpenAI(api_key=openai.api_key)
    
    response = await client.responses.create(
        model="gpt-5-mini",
        tools=tools,
        instructions="Your next reply is not visible to the user. Generate contextual text actions to respond with. Each on new line. 1-5 words per option. Only letters. No punctuation or numeration. These will be used as button labels. Only add relevant contextual actions.",
        input=messages,
    )

    options = [
        x.capitalize()
        for x in response.output_text.replace(".", "").replace("- ", "").split("\n")
        if x.strip()
    ]

    return options


def main():
    logging.basicConfig(level=logging.INFO)
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(MessageHandler(filters.ALL, message_handler))
    print("🚀 Bot is starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
