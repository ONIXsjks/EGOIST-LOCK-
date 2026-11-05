import os, asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from config import TOKEN, RENDER_EXTERNAL_URL
from db import init_db, engine
from handlers import router
from sqlalchemy import text

WEBHOOK_PATH = f"/webhook/{TOKEN}"
BASE_URL = RENDER_EXTERNAL_URL.rstrip("/")

async def on_startup(bot: Bot):
    if BASE_URL:
        await bot.set_webhook(f"{BASE_URL}{WEBHOOK_PATH}")
        print(f"Webhook set: {BASE_URL}{WEBHOOK_PATH}")
    else:
        print("RENDER_EXTERNAL_URL خالی است.")

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()

async def relationship_loop():
    while True:
        try:
            with engine.begin() as conn:
                conn.execute(text("UPDATE social_edges SET trust=GREATEST(50, trust-1) WHERE trust > 50"))
                conn.execute(text("UPDATE social_edges SET grudge=GREATEST(0, grudge-1) WHERE grudge > 0"))
        except Exception as e:
            print(f"Loop error: {e}")
        await asyncio.sleep(300)

async def main():
    init_db()
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    asyncio.create_task(relationship_loop())

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
    await site.start()
    print(f"Server started on port {os.environ.get('PORT', 10000)}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())