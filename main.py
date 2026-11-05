import os, asyncio, random
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
    "⚔️ **خبر امنیتی:** نگهبانان شهر یک دزد را دستگیر کردند. به پاس تلاش‌های شهروندان، به همه ۱۰ سکه پاداش تعلق گرفت.",
    "💰 **خبر اقتصادی:** یک تاجر ثروتمند وارد شهر شد. همه شهروندان ۲۰ سکه جایزه گرفتند!",
    "🌙 **شب آرام:** شب آرامی در شهر است. همه شهروندان ۲۰ واحد انرژی اضافه دریافت کردند.",
    "🦠 **هشدار پزشکی:** یک بیماری در شهر شیوع پیدا کرده! سلامتی همه ۵ واحد کاهش یافت."
]

async def game_loop(bot: Bot):
    """حلقه اصلی بازی: هر ۵ دقیقه یک بار اجرا می‌شود"""
    await asyncio.sleep(60)
    tick_count = 0
    
    while True:
        try:
            with engine.begin() as conn:
                # گرفتن لیست گروه‌هایی که بازیکن دارن
                chats = conn.execute(text("SELECT DISTINCT chat_id FROM players")).fetchall()
                
                # ۱. تولید دونه توسط جوجه‌ها (بی‌صدا)
                for (chat_id,) in chats:
                    conn.execute(text("""
                        UPDATE players 
                        SET chicken_eggs = chicken_eggs + (
                            CASE 
                                WHEN house_level >= 3 THEN chicken_level * 6 
                                ELSE chicken_level * 3 
                            END
                        ) 
                        WHERE chat_id=:c
                    """), {"c": chat_id})
                
                # ۲. هر ۳۰ دقیقه (۶ بار تیک ۵ دقیقه‌ای) یک رویداد میاد
                tick_count += 1
                if tick_count >= 6:
                    tick_count = 0
                    event_msg = random.choice(EVENTS)
                    
                    # اعمال اثرات رویداد
                    if "۱۰ سکه" in event_msg:
                        conn.execute(text("UPDATE players SET coins=coins+10"))
                    elif "۲۰ سکه" in event_msg:
                        conn.execute(text("UPDATE players SET coins=coins+20"))
                    elif "۲۰ واحد انرژی" in event_msg:
                        conn.execute(text("UPDATE players SET energy=LEAST(100, energy+20)"))
                    elif "سلامتی همه" in event_msg:
                        conn.execute(text("UPDATE players SET health=GREATEST(0, health-5)"))

                    # ارسال پیام رویداد به گروه‌ها
                    for (chat_id,) in chats:
                        try: 
                            await bot.send_message(chat_id, event_msg)
                        except: 
                            pass
        except Exception as e: 
            print(f"Game Loop Error: {e}")
            
        # ۳۰۰ ثانیه = ۵ دقیقه
        await asyncio.sleep(300)

async def health_check(request): 
    return web.Response(text="OK")

async def main():
    # ساخت جدول‌ها در دیتابیس
    init_db()
    
    # تنظیمات ربات
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    
    # پاک کردن وب‌هوک‌های قبلی
    await bot.delete_webhook(drop_pending_updates=True)

    # راه‌اندازی وب‌سرور برای بیدار ماندن Render
    app = web.Application()
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
    await site.start()

    # اجرای حلقه بازی در پس‌زمینه
    asyncio.create_task(game_loop(bot))
    
    # شروع به کار ربات
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())