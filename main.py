# main.py
import asyncio
from bot.highrise_bot import MyHighriseBot
from config.settings import HIGHRISE_API_TOKEN, HIGHRISE_ROOM_ID

async def main():
    bot = MyHighriseBot()
    await bot.run_bot(HIGHRISE_ROOM_ID, HIGHRISE_API_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
