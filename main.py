import os
import asyncio
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
        print(f"✅ Webhook set successfully to: {BASE_URL}{WEBHOOK_PATH}")
    else:
        print("⚠️ WARNING: RENDER_EXTERNAL_URL is empty. Webhook not set!")

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()

async def relationship_loop():
    """حلقه تغییر روابط (اعتماد و کینه) هر ۵ دقیقه یک بار"""
    while True:
        try:
            with engine.begin() as conn:
                conn.execute(text("UPDATE social_edges SET trust=GREATEST(50, trust-1) WHERE trust > 50"))
                conn.execute(text("UPDATE social_edges SET grudge=GREATEST(0, grudge-1) WHERE grudge > 0"))
        except Exception as e:
            print(f"Loop error: {e}")
        await asyncio.sleep(300)

async def health_check(request):
    """برای اینکه UptimeRobot بتواند بات را بیدار نگه دارد"""
    return web.Response(text="OK")

async def main():
    # ساخت جدول‌ها در دیتابیس
    init_db()
    
    # تنظیمات ربات
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # راه‌اندازی وب‌سرور
    app = web.Application()
    app.router.add_get("/health", health_check)
    
    # اتصال وب‌هوک تلگرام به وب‌سرور
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    # اجرای لوپ پس‌زمینه
    asyncio.create_task(relationship_loop())

    # اجرای سرور روی پورت رندر
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    print(f"🚀 Server started on port {port}")
    
    # نگه داشتن برنامه در حال اجرا
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
