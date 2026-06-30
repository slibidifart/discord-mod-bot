import asyncio
import os

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from storage import Store

load_dotenv()
TOKEN = os.getenv("TOKEN") or os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

if not TOKEN:
    raise RuntimeError("TOKEN is missing. Add your Discord bot token in Railway Variables, then redeploy.")

intents = discord.Intents.default()
intents.members = True


class ManagementBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.store = Store()

    async def setup_hook(self):
        for extension in ("cogs.moderation", "cogs.roblox", "cogs.honor", "cogs.settings"):
            await self.load_extension(extension)

        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Synced slash commands to server {GUILD_ID}.")
        else:
            await self.tree.sync()
            print("Synced global slash commands. Discord may take a little while to show them everywhere.")


bot = ManagementBot()


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}.")


@bot.tree.command(name="ping", description="Check whether the bot is online")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! {round(bot.latency * 1000)}ms", ephemeral=True)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        message = "You do not have permission to use that command."
    elif isinstance(error, app_commands.CommandOnCooldown):
        message = f"Slow down — try again in {error.retry_after:.1f}s."
    elif isinstance(error, app_commands.CheckFailure):
        message = "You cannot use that command here."
    elif isinstance(error, (ValueError, RuntimeError)):
        message = str(error)
    else:
        print(f"Command error: {error!r}")
        message = "Something went wrong. Check the bot's permissions and try again."

    if interaction.response.is_done():
        await interaction.followup.send(f"❌ {message}", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ {message}", ephemeral=True)


async def main():
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
