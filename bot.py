
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    MenuButtonWebApp
)

from app.config import settings


logging.basicConfig(level=logging.INFO)

dp = Dispatcher()


def get_app_keyboard():
    if not settings.webapp_url:
        return None

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Открыть MarketPilot",
                    web_app=WebAppInfo(url=settings.webapp_url)
                )
            ]
        ]
    )


@dp.message(CommandStart())
async def start_handler(message: Message):
    keyboard = get_app_keyboard()

    await message.answer(
        "👋 Добро пожаловать в MarketPilot!\n\n"
        "Платформа для управления Telegram-сообществами.\n\n"
        "Здесь ты сможешь управлять инструментами модерации, "
        "автоматизацией публикаций и аналитикой.",
        reply_markup=keyboard
    )


@dp.message(Command("panel"))
async def panel_handler(message: Message):
    keyboard = get_app_keyboard()

    if not keyboard:
        await message.answer(
            "Ссылка на Mini App пока не настроена. "
            "Добавь WEBAPP_URL в файл .env."
        )
        return

    await message.answer(
        "Открывай панель управления MarketPilot:",
        reply_markup=keyboard
    )


@dp.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        "📚 Команды MarketPilot:\n\n"
        "/start — запуск бота\n"
        "/panel — открыть панель управления\n"
        "/help — список команд"
    )


async def main():
    if not settings.bot_token:
        raise RuntimeError(
            "BOT_TOKEN не указан в файле .env"
        )

    bot = Bot(token=settings.bot_token)

    if settings.webapp_url:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="MarketPilot",
                web_app=WebAppInfo(url=settings.webapp_url)
            )
        )

    logging.info("MarketPilot bot is starting...")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
