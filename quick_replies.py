import asyncio
import logging
from faq_rag.faq_rag import ask_faq
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
