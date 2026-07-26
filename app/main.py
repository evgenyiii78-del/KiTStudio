import asyncio,logging
from aiogram import Bot,Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.config import settings
from app.db.database import init_db
from app.handlers.main import router,queue

async def main():
    settings.ensure_dirs(); logging.basicConfig(level=getattr(logging,settings.log_level.upper(),logging.INFO),format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.info("AITunnel key: %s", "loaded" if settings.aitunnel_api_key else "NOT SET")
    await init_db(); await queue.start()
    bot=Bot(settings.telegram_bot_token,default=DefaultBotProperties(parse_mode=ParseMode.HTML)); dp=Dispatcher(); dp.include_router(router)
    try: await dp.start_polling(bot)
    finally: await queue.stop(); await bot.session.close()
if __name__=="__main__": asyncio.run(main())
