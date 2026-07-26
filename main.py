import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings
from app.database import Database
from app.handlers.common import router as common_router
from app.handlers.chat import router as chat_router
from app.handlers.images import router as images_router
from app.services.ai import AIService

async def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    settings.validate()
    settings.ensure_directories()

    bot = Bot(settings.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    db = Database(settings.database_path)
    await db.init()
    ai = AIService(settings)

    dp = Dispatcher()
    dp["db"] = db
    dp["ai"] = ai
    dp.include_router(common_router)
    dp.include_router(images_router)
    dp.include_router(chat_router)

    me = await bot.get_me()
    logging.info("CakeHub AI Bot 3.4 started as @%s", me.username)
    logging.info("AITunnel key: loaded")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, bot_username=(me.username or "").lower())

if __name__ == "__main__":
    asyncio.run(main())
