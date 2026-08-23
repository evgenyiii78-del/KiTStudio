import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.database import Database
from app.handlers.chat import router as chat_router
from app.handlers.common import router as common_router
from app.handlers.images import router as images_router
from app.services.ai import AIService


async def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    settings.validate()
    settings.ensure_directories()

    bot = Bot(
        settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    db = Database(settings.database_path)
    await db.init()
    ai = AIService(settings)

    dp = Dispatcher(storage=MemoryStorage())
    dp["db"] = db
    dp["ai"] = ai
    dp["settings"] = settings
    dp.include_router(common_router)
    dp.include_router(images_router)
    dp.include_router(chat_router)

    me = await bot.get_me()
    bot_username = (me.username or "").lower()
    dp["bot_username"] = bot_username

    logging.info("CakeHub AI Bot 3.4 started as @%s", me.username)
    logging.info("AITunnel API key: loaded")
    logging.info("Chat model: %s | Vision model: %s | Image model: %s", settings.chat_model, settings.vision_model, settings.image_model)
    logging.info("Database: %s", settings.database_path)

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await ai.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
