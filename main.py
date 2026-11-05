import os
import asyncio
import random
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import TOKEN
from db import init_db, engine
from handlers import router
from sqlalchemy import text

# لیست رویدادهای خودکار شهر
EVENTS = [
    "🚨 **خبر فوری:** یک غار باستانی در کوه‌های شهر باز شده! اولین کسی که دستور `/dig` را بزند شانس پیدا کردن گنج طلایی را دارد!",
    "💰 **خبر اقتصادی:** یک تاجر ثروتمند وارد شهر شد. به ۳ نفر اولی که الان دستور `/work` را بزنند ۳۰ سکه جایزه می‌دهد!",
    "🦠 **هشدار پزشکی:** یک بیماری در شهر شیوع پیدا کرده! سلامتی همه شهروندان ۵ واحد کاهش یافت. اگر زخمی شده‌اید به دکتر مراجعه کنید.",
    "⚔️ **خبر امنیتی:** نگهبانان شهر یک دزد را دستگیر کردند. به پاس تلاش‌های شهروندان، به همه ۱۰ سکه پاداش تعلق گرفت.",
    "🌙 **شب آرام:** شب آرامی در شهر است. همه شهروندان ۱۵ واحد انرژی اضافه دریافت کردند."
]

async def event_loop(bot: Bot):
    """حلقه‌ای که هر ۳ ساعت یک رویداد تصادفی به گروه‌ها می‌فرستد"""
    await asyncio.sleep(60) # صبر کردن تا ربات کامل بالا بیاید
    while True:
        try:
            with engine.begin() as conn:
                # گرفتن لیست گروه‌هایی که بازیکن دارن
                chats = conn.execute(text("SELECT DISTINCT chat_id FROM players")).fetchall()
                
                if chats:
                    event_msg = random.choice(EVENTS)
                    
                    # اگر رویداد مربوط به انرژی یا سلامتی بود، تغییرات رو تو دیتابیس اعمال کن
                    if "سلامتی همه" in event_msg:
                        conn.execute(text("UPDATE players SET health=GREATEST(0, health-5)"))
                    elif "انرژی اضافه" in event_msg:
                        conn.execute(text("UPDATE players SET energy=LEAST(100, energy+15)"))
                    elif "۱۰ سکه پاداش" in event_msg:
                        conn.execute(text("UPDATE players SET coins=coins+10"))

                    # ارسال پیام به همه گروه‌ها
                    for (chat_id,) in chats:
                        try:
                            await bot.send_message(chat_id, event_msg)
                        except Exception:
                            pass
        except Exception as e:
            print(f"Event Loop Error: {e}")
            
        # هر ۳ ساعت (۱۰۸۰۰ ثانیه) یک بار تکرار شود
        await asyncio.sleep(10800) 

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

    # پاک کردن وب‌هوک‌های قبلی
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Webhook deleted. Starting polling...")

    # اجرای وب‌سرور (برای بیدار ماندن رندر)
    asyncio.create_task(start_web_server())
    
    # اجرای حلقه رویدادهای تصادفی شهر
    asyncio.create_task(event_loop(bot))

    # شروع Polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())