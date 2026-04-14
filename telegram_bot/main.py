#!/usr/bin/env python3
"""
Точка входа для Telegram-бота на aiogram.
Поддерживает прокси (обязательно для PythonAnywhere).
"""

import asyncio
import logging
import os
import sys

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

# ✅ СТРОКА, ТРЕБУЕМАЯ УЧИТЕЛЕМ
session = AiohttpSession(proxy='http://proxy.server:3128')

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
from database import db
from bot import router  # импортируем роутер с хендлерами

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    # ✅ ПРАВИЛЬНАЯ ПРОВЕРКА ТОКЕНА
    if config.BOT_TOKEN == "ЗАМЕНИ_НА_НОВЫЙ_ТОКЕН":
        logger.error("❌ Токен бота не установлен в config.py!")
        sys.exit(1)

    # Инициализация БД (таблицы создадутся при импорте db)
    _ = db

    # Используем глобальную сессию с прокси
    logger.info("Используется прокси: http://proxy.server:3128")

    # Создаём бота с глобальной сессией
    bot = Bot(
        token=config.BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Подключаем роутер с хендлерами
    dp.include_router(router)

    # Удаляем вебхук и запускаем поллинг
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Бот запущен и готов к работе!")

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
    finally:
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())