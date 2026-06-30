import discord
from discord import app_commands
from discord.ext import commands

from .common import check_assignable_role


class Settings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    config = app_commands.Group(name="config", description="Configure the bot for this server")

    @config.command(name="verified-role", description="Choose the role given after Roblox verification")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(role="Role to give members after verification")
    async def verified_role(self, interaction: discord.Interaction, role: discord.Role):
        if not interaction.guild:
            return await interaction.response.send_message("Use this command inside a server.", ephemeral=True)
        problem = check_assignable_role(interaction.guild, role)
        if problem:
            return await interaction.response.send_message(problem, ephemeral=True)
        self.bot.store.set_config(interaction.guild.id, "verified_role_id", role.id)
        await interaction.response.send_message(f"Roblox-verified members will now receive {role.mention}.", ephemeral=True)

    @config.command(name="log-channel", description="Choose where moderation actions are logged")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channel="Text channel for moderation logs")
    async def log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.guild:
            return await interaction.response.send_message("Use this command inside a server.", ephemeral=True)
        self.bot.store.set_config(interaction.guild.id, "log_channel_id", channel.id)
        await interaction.response.send_message(f"Moderation logs will now be sent to {channel.mention}.", ephemeral=True)

    @config.command(name="view", description="View this server's bot settings")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def view(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("Use this command inside a server.", ephemeral=True)
        config = self.bot.store.get_config(interaction.guild.id)
        role = interaction.guild.get_role(int(config["verified_role_id"])) if config.get("verified_role_id") else None
        channel = interaction.guild.get_channel(int(config["log_channel_id"])) if config.get("log_channel_id") else None
        await interaction.response.send_message(
            f"**Bot settings**\nVerified role: {role.mention if role else 'Not set'}\nMod-log channel: {channel.mention if channel else 'Not set'}",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Settings(bot))
