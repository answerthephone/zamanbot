import copy
import telegramify_markdown
import openai
import json
from aiogram import Router, flags
from aiogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)
from aiogram.filters import Command
from faq_rag.faq_rag import ask_faq
from saving_strategies import generate_saving_strategies

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

router = Router()


class Conversation:
    def __init__(self, user_id):
        self.user_id = user_id
        self.history: list[dict[str, str]] = [
            {
                "role": "developer",
                "content": "Ты цифровой ассистент банка ZamanBank. Твоя цель помочь клиенту банка. Отвечай на вопросы клиента как справочник: напрямую и полностью, без введения или заключения. Пытайся использовать functions если это уместно. Если не хватает данных для вызовы функции, спроси их у пользователя.",
            },
        ]
        self.quick_options = []  # max length = 4


conversations: dict[int, Conversation] = {}


def create_quick_replies(options: list[str]) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for i, opt in enumerate(options):
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=opt, callback_data=f"quick_{i}")]
        )
    return keyboard


def process_user_input(user_id: int, text: str) -> tuple[str, list[str]]:
    if user_id not in conversations:
        conversations[user_id] = Conversation(user_id)
    conversation = conversations[user_id]

    conversation.history.append({"role": "user", "content": text})
    faq_reply = str(ask_faq(text))
    conversation.history.append({"role": "developer", "content": faq_reply})
    reply = generate_reply(conversation)
    conversation.history.append({"role": "assistant", "content": reply})
    conversation.quick_options = generate_quick_replies(conversation)
    return reply, conversation.quick_options


def generate_reply(conversation: Conversation) -> str:
    response = openai.responses.create(
        model="gpt-4o-mini",
        temperature=0.7,
        input=conversation.history
    )
    conversation.history += response.output

    has_function_call = False
    for item in response.output:
        if item.type == "function_call":
            has_function_call = True
            if item.name == "generate_saving_strategies":
                result = generate_saving_strategies(json.loads(item.arguments))
                conversation.history.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(result),
                    }
                )

    if has_function_call:
        response = openai.responses.create(
            model="gpt-4o-mini",
            instructions="Present the result of the function call in the context of the conversation.",
            temperature=0.7,
            input=conversation.history
        )

    return telegramify_markdown.markdownify(
        response.output_text, max_line_length=None, normalize_whitespace=False
    )


@router.message(Command("start"))
async def start_handler(message: Message):
    conversations[message.from_user.id] = Conversation(message.from_user.id)
    await message.answer("👋 Здравствуйте!")


@router.message()
@flags.chat_action("typing")
async def message_handler(message: Message):
    reply, quick_options = process_user_input(message.from_user.id, message.text)
    await message.answer(
        reply,
        tools=tools,
        reply_markup=create_quick_replies(quick_options),
        parse_mode="MarkdownV2",
    )


def generate_quick_replies(conversation):
    messages = copy.deepcopy(conversation.history)
    messages.append(
        {
            "role": "developer",
            "content": "Your next reply is not visible to the user. It will be sent to a RAG system. Query it to generate 1-4 contextual text actions to respond with. It will NOT have access to the conversation history so include necessary details in the query.",
        }
    )
    rag_query_response = openai.responses.create(
        model="gpt-4o-mini",
        temperature=0.7,
        input=messages,
    )
    faq_reply = str(ask_faq(rag_query_response.output_text))
    messages = copy.deepcopy(conversation.history)
    messages.append(
        {
            "role": "developer",
            "content": "Generate 1-4 contextual text actions to respond with. Each on new line. 1-5 words per option. Only letters. No punctuation or numeration. These will be used as button labels. RAG info:\n"
            + faq_reply,
        }
    )
    response = openai.responses.create(
        model="gpt-4o-mini",
        temperature=0.7,
        input=messages,
    )
    return [
        x.capitalize() for x in response.output_text.replace(".", "").replace("- ", "").split("\n")
    ]


@router.callback_query(lambda c: c.data and c.data.startswith("quick_"))
@flags.chat_action("typing")
async def quick_reply_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    index = int(callback.data.split("_")[1])
    conversation = conversations.get(user_id)
    selected_text = conversation.quick_options[index]
    reply, new_quick_options = process_user_input(user_id, selected_text)
    await callback.answer()
    await callback.message.answer(
        reply,
        reply_markup=create_quick_replies(new_quick_options),
        parse_mode="MarkdownV2",
    )
