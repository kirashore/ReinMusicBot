import asyncio
import sys
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

class MyBot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension('music')

bot = MyBot(command_prefix='r!', intents=intents)

@bot.event
async def on_ready():
    print(f'✅ Bot {bot.user} udah nyala cuy!')

bot.run(TOKEN)