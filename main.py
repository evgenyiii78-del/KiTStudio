import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings, telegram_token_candidates
from app.database import Database
from app.handlers.common import router as common_router
from app.handlers.images import router as images_router
from app.handlers.video import router as video_router
from app.services.ai import AIService
from app.services.video_ai import VideoAIService

async def connect_telegram() -> tuple[Bot, object, str]:
    last_error=None
    for source, token in telegram_token_candidates():
        bot_id=token.split(":",1)[0]
        logging.info("Checking Telegram token from %s: bot_id=%s, length=%s", source, bot_id, len(token))
        bot=Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        try:
            me=await bot.get_me(); logging.info("Telegram token from %s accepted", source); return bot,me,source
        except Exception as exc:
            last_error=exc; logging.warning("Telegram token from %s rejected: %s",source,type(exc).__name__); await bot.session.close()
    raise RuntimeError("Telegram не принял ни BOT_TOKEN, ни TELEGRAM_BOT_TOKEN. Проверь токен.") from last_error

async def main() -> None:
    logging.basicConfig(level=getattr(logging,settings.log_level.upper(),logging.INFO),format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    settings.validate(); settings.ensure_directories()
    bot=None; ai=None
    try:
        bot,me,token_source=await connect_telegram()
        db=Database(settings.database_path); await db.init()
        ai=AIService(settings); video_ai=VideoAIService(settings)
        dp=Dispatcher(storage=MemoryStorage())
        dp["db"]=db; dp["ai"]=ai; dp["video_ai"]=video_ai; dp["settings"]=settings
        dp.include_router(common_router); dp.include_router(video_router); dp.include_router(images_router)
        logging.info("KiTstudio AI Bot 3.6.0 started as @%s",me.username)
        logging.info("Telegram token source: %s",token_source)
        logging.info("AITunnel API key: loaded")
        logging.info("Image model: %s",settings.image_model)
        logging.info("Video model: %s",settings.video_model)
        logging.info("Database: %s",settings.database_path)
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot,allowed_updates=dp.resolve_used_update_types())
    finally:
        if ai is not None: await ai.close()
        if bot is not None: await bot.session.close()

if __name__ == "__main__": asyncio.run(main())
