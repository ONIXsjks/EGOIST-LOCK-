import os, asyncio, random
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import TOKEN
from db import init_db, engine
from handlers import router
from sqlalchemy import text

# لیست رویدادهایی که به صورت خودکار میان
EVENTS = [
    "⚔️ **خبر امنیتی:** نگهبانان شهر یک دزد را دستگیر کردند. به پاس تلاش‌های شهروندان، به همه ۱۰ سکه پاداش تعلق گرفت.",
    "💰 **خبر اقتصادی:** یک تاجر ثروتمند وارد شهر شد. همه شهروندان ۲۰ سکه جایزه گرفتند!",
    "🌙 **شب آرام:** شب آرامی در شهر است. همه شهروندان ۲۰ واحد انرژی اضافه دریافت کردند.",
    "🦠 **هشدار پزشکی:** یک بیماری در شهر شیوع پیدا کرده! سلامتی همه ۵ واحد کاهش یافت."
]

async def chicken_loop(bot: Bot):
    """جوجه‌ها بی‌صدا دونه جمع می‌کنن و هر ۳۰ دقیقه یه رویداد خودکار میاد"""
    await asyncio.sleep(60)
    tick_count = 0
    while True:
        try:
            with engine.begin() as conn:
                # ۱. جمع کردن دونه توسط جوجه‌ها (بی‌صدا)
                chats = conn.execute(text("SELECT DISTINCT chat_id FROM players")).fetchall()
                for (chat_id,) in chats:
                    conn.execute(text("UPDATE players SET chicken_eggs = chicken_eggs + (chicken_level * 3) WHERE chat_id=:c"), {"c": chat_id})
                
                # ۲. هر ۳۰ دقیقه (۶ بار تیک ۵ دقیقه‌ای) یه رویداد میاد
                tick_count += 1
                if tick_count >= 6:
                    tick_count = 0
                    event_msg = random.choice(EVENTS)
                    
                    # اعمال اثرات رویداد
                    if "۱۰ سکه پاداش" in event_msg:
                        conn.execute(text("UPDATE players SET coins=coins+10"))
                    elif "۲۰ سکه" in event_msg:
                        conn.execute(text("UPDATE players SET coins=coins+20"))
                    elif "۲۰ واحد انرژی" in event_msg:
                        conn.execute(text("UPDATE players SET energy=LEAST(100, energy+20)"))
                    elif "سلامتی همه" in event_msg:
                        conn.execute(text("UPDATE players SET health=GREATEST(0, health-5)"))

                    # ارسال پیام رویداد به گروه‌ها
                    for (chat_id,) in chats:
                        try: await bot.send_message(chat_id, event_msg)
                        except: pass
        except Exception as e: print(f"Loop Error: {e}")
        await asyncio.sleep(300) # هر ۵ دقیقه

async def health_check(request): return web.Response(text="OK")

async def main():
    init_db()
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)

    app = web.Application()
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
    await site.start()

    asyncio.create_task(chicken_loop(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())