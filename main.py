import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings, telegram_token_candidates
from app.database import Database
from app.handlers.chat import router as chat_router
from app.handlers.common import router as common_router
from app.handlers.images import router as images_router
from app.services.ai import AIService


async def connect_telegram() -> tuple[Bot, object, str]:
    """Try Bothost token variables without ever logging the secret token."""
    last_error: Exception | None = None

    for source, token in telegram_token_candidates():
        bot_id = token.split(":", 1)[0]
        logging.info(
            "Checking Telegram token from %s: bot_id=%s, length=%s",
            source,
            bot_id,
            len(token),
        )

        bot = Bot(
            token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        try:
            me = await bot.get_me()
            logging.info("Telegram token from %s accepted", source)
            return bot, me, source
        except Exception as exc:
            last_error = exc
            logging.warning(
                "Telegram token from %s rejected by Telegram: %s",
                source,
                type(exc).__name__,
            )
            await bot.session.close()

    raise RuntimeError(
        "Telegram не принял ни BOT_TOKEN, ни TELEGRAM_BOT_TOKEN. "
        "Проверь токен бота в настройках Bothost."
    ) from last_error


async def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    settings.validate()
    settings.ensure_directories()

    bot: Bot | None = None
    ai: AIService | None = None

    try:
        bot, me, token_source = await connect_telegram()

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

        bot_username = (me.username or "").lower()
        dp["bot_username"] = bot_username

        logging.info("CakeHub AI Bot 3.4.2 started as @%s", me.username)
        logging.info("Telegram token source: %s", token_source)
        logging.info("AITunnel API key: loaded")
        logging.info(
            "Chat model: %s | Vision model: %s | Image model EFFECTIVE: %s",
            settings.chat_model or "<empty>",
            settings.vision_model or "<empty>",
            settings.image_model,
        )
        logging.info("Database: %s", settings.database_path)

        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        if ai is not None:
            await ai.close()
        if bot is not None:
            await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
