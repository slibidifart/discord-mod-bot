import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

async def load_extensions():
    await bot.load_extension('cogs.moderation')
    await bot.load_extension('cogs.tickets')
    await bot.load_extension('cogs.automod')

@bot.event
async def setup_hook():
    await load_extensions()
    await bot.tree.sync()

@bot.tree.command(name='ping', description='Check bot latency')
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message('Pong 🏓')

bot.run(TOKEN)
