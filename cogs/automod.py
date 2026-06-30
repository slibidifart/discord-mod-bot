import re
from collections import defaultdict, deque
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands


INVITE_REGEX = re.compile(r'(discord\.gg/|discord\.com/invite/)', re.IGNORECASE)
LINK_REGEX = re.compile(r'https?://|www\.', re.IGNORECASE)

# Add words you do not want in your server here.
BLOCKED_WORDS = {
    'badword1',
    'badword2',
    'badword3'
}


class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_cache = defaultdict(lambda: deque(maxlen=6))

    async def punish(self, message: discord.Message, reason: str):
        try:
            await message.delete()
        except discord.Forbidden:
            return

        warning = f'{message.author.mention}, your message was removed. Reason: **{reason}**'
        try:
            await message.channel.send(warning, delete_after=6)
        except discord.Forbidden:
            pass

        if isinstance(message.author, discord.Member):
            try:
                await message.author.timeout(timedelta(minutes=5), reason=reason)
            except (discord.Forbidden, discord.HTTPException):
                pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        if isinstance(message.author, discord.Member) and message.author.guild_permissions.manage_messages:
            return

        content = message.content.lower()

        if any(word in content for word in BLOCKED_WORDS):
            await self.punish(message, 'Blocked word')
            return

        if INVITE_REGEX.search(content):
            await self.punish(message, 'Discord invite link')
            return

        if LINK_REGEX.search(content):
            await self.punish(message, 'Links are not allowed')
            return

        cache_key = (message.guild.id, message.author.id)
        self.message_cache[cache_key].append(message.created_at.timestamp())

        if len(self.message_cache[cache_key]) >= 5:
            oldest = self.message_cache[cache_key][0]
            newest = self.message_cache[cache_key][-1]
            if newest - oldest <= 6:
                await self.punish(message, 'Spam')
                self.message_cache[cache_key].clear()

    @app_commands.command(name='automod_status', description='Check what AutoMod is filtering')
    @app_commands.checks.has_permissions(manage_messages=True)
    async def automod_status(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title='AutoMod Status',
            description='AutoMod is enabled and watching for spam, Discord invites, links, and blocked words.',
            color=discord.Color.green()
        )
        embed.add_field(name='Spam filter', value='5 messages in 6 seconds = timeout', inline=False)
        embed.add_field(name='Timeout length', value='5 minutes', inline=False)
        embed.add_field(name='Blocked words', value=f'{len(BLOCKED_WORDS)} words in the list', inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AutoMod(bot))
