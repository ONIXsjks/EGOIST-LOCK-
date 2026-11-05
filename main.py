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

async def chicken_loop(bot: Bot):
    """حلقه جیک جیک کردن هر ۵ دقیقه"""
    await asyncio.sleep(60)
    while True:
        try:
            with engine.begin() as conn:
                # پیدا کردن همه گروه‌های فعال
                chats = conn.execute(text("SELECT DISTINCT chat_id FROM players")).fetchall()
                for (chat_id,) in chats:
                    # دادن دونه به بازیکن‌های این گروه بر اساس لول جوجه
                    conn.execute(text("UPDATE players SET chicken_eggs = chicken_eggs + (chicken_level * 3) WHERE chat_id=:c"), {"c": chat_id})
                
                # ارسال پیام به گروه‌ها
                for (chat_id,) in chats:
                    try:
                        await bot.send_message(chat_id, "🐥 **جیک جیک!**\nجوجه‌ها اینقدر دونه گرفتن! (برای برداشت به «جوجه من» بروید)")
                    except:
                        pass
        except Exception as e:
            print(f"Chicken Loop Error: {e}")
        await asyncio.sleep(300) # هر ۵ دقیقه

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

async def main():
    init_db()
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(start_web_server())
    asyncio.create_task(chicken_loop(bot))

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())