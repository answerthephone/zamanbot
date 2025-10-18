import asyncio
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from faq_rag.faq_rag import ask_faq

import logging
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
import os

# Import routers from handlers
from bot.handlers.start import start_router

# Load environment variables
load_dotenv()

# Initialize bot and dispatcher
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is missing in .env")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Register routers
dp.include_router(start_router)

faq_router = Router()

@faq_router.message(Command("faq"))
async def faq_handler(message: Message):
    await message.answer(str(ask_faq(message.text)))

dp.include_router(faq_router)

# Entry point
async def main():
    logging.basicConfig(level=logging.INFO)
    print("🚀 Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
