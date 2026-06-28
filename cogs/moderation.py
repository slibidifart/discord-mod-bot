import discord
from discord import app_commands
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='kick')
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str=None):
        await member.kick(reason=reason)
        await interaction.response.send_message(f'Kicked {member.mention}')

    @app_commands.command(name='ban')
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str=None):
        await member.ban(reason=reason)
        await interaction.response.send_message(f'Banned {member.mention}')

async def setup(bot):
    await bot.add_cog(Moderation(bot))