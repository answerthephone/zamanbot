import json
import asyncio
import logging
from faq_rag.faq_rag import ask_faq, async_check_faq_has
from conversation import Conversation
import openai
from llm_tools import tools
from telegram import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


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
        tools=[
            {
                "type": "function",
                "strict": True,
                "name": "provide_replies",
                "description": "Provide replies here.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "replies": {
                            "type": "array",
                            "items": {
                                "type": "string",
                            },
                            "description": "List of reply messages",
                        },
                    },
                    "required": ["replies"],
                    "additionalProperties": False,
                },
            }
        ],
        instructions="Your next reply is not visible to the user. Suggest 0-8 things for the user to reply with. Only add relevant contextual buttons. These will be used as button labels. 1-5 words per option. Only letters. No punctuation or numeration. End your response with a JSON array of strings.",
        input=messages,
    )

    replies = []
    for item in response.output:
        if item.type == "function_call":
            if item.name == "provide_replies":
                replies = json.loads(item.arguments)

    replies = [x.capitalize().replace(".", "").replace("- ", "") for x in replies]
    related_replies = await asyncio.gather(*(async_check_faq_has(x) for x in replies))

    return [x for i, x in enumerate(replies) if related_replies[i]]
