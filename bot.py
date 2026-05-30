import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db
from handlers import routers

async def main():
    init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    for r in routers:
        dp.include_router(r)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

