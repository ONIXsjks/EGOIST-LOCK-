import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import TOKEN
from db import init_db, engine
from handlers import router
from sqlalchemy import text

async def relationship_loop():
    while True:
        try:
            with engine.begin() as conn:
                conn.execute(text("UPDATE social_edges SET trust=GREATEST(50, trust-1) WHERE trust > 50"))
                conn.execute(text("UPDATE social_edges SET grudge=GREATEST(0, grudge-1) WHERE grudge > 0"))
        except Exception as e:
            print(f"Loop error: {e}")
        await asyncio.sleep(300)

async def health_check(request):
    return web.Response(text="OK")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    print(f"🌐 Web server started on port {port}")

async def main():
    init_db()
    print("🚀 Starting bot...")
    
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    # پاک کردن وب‌هوک‌های قبلی (برای جلوگیری از تداخل)
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Webhook deleted. Starting polling...")

    # اجرای وب‌سرور در پس‌زمینه (برای زنده نگه داشتن رندر)
    asyncio.create_task(start_web_server())
    
    # اجرای لوپ روابط
    asyncio.create_task(relationship_loop())

    # شروع Polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())