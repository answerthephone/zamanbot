import openai
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from faq_rag.faq_rag import ask_faq

router = Router()


class Conversation:
    def __init__(self, user_id):
        self.user_id = user_id
        self.history: list[int, str] = [
            ("developer", "Ты цифровой ассистент банка ZamanBank."),
        ]


conversations: dict[int, Conversation] = {}


@router.message(Command("start"))
async def start_handler(message: Message):
    user_id = message.from_user.id
    conversations[user_id] = Conversation(user_id)
    await message.answer("👋 Здравсвуйте!")


@router.message()
async def message_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in conversations:
        conversations[user_id] = Conversation(user_id)

    conversation = conversations[user_id]

    conversation.history.append(("user", message.text))
    conversation.history.append(("developer", str(ask_faq(message.text))))
    reply = await generate_reply(conversation)
    await message.answer(reply)
    conversation.history.append(("assistant", reply))

async def handle_message(text, user_id, message):
    if user_id not in conversations:
        conversations[user_id] = Conversation(user_id)

    conversation = conversations[user_id]

    conversation.history.append(("user", text))
    conversation.history.append(("developer", str(ask_faq(text))))
    reply = await generate_reply(conversation)
    await message.answer(reply)
    conversation.history.append(("assistant", reply))


async def generate_reply(conversation: Conversation) -> str:
    messages = []
    for role, text in conversation.history:
        messages.append({"role": role, "content": text})

    print(messages)

    response = openai.responses.create(
        model="gpt-4o-mini",
        temperature=0.7,
        input=messages,
    )
    reply = response.output_text
    return reply
