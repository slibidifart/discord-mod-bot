import discord
from discord import app_commands
from discord.ext import commands

from .common import check_assignable_role
from .honor import RANK_CHOICES


class Settings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    config = app_commands.Group(name="config", description="Configure the bot for this server")

    async def sync_rank_roles(self, guild: discord.Guild) -> int:
        honor_cog = self.bot.get_cog("Honor")
        if honor_cog is None:
            return 0
        return await honor_cog.sync_guild_rank_roles(guild)

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

    @config.command(name="rank-role", description="Link a Discord role to an automatic military rank")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.choices(rank=RANK_CHOICES)
    @app_commands.describe(rank="Military rank", role="Role to assign; leave blank to remove this rank role")
    async def rank_role(
        self,
        interaction: discord.Interaction,
        rank: app_commands.Choice[str],
        role: discord.Role | None = None,
    ):
        if not interaction.guild:
            return await interaction.response.send_message("Use this command inside a server.", ephemeral=True)

        config = self.bot.store.get_config(interaction.guild.id)
        raw_mapping = config.get("rank_role_ids", {})
        mapping = dict(raw_mapping) if isinstance(raw_mapping, dict) else {}

        if role is None:
            if rank.value not in mapping:
                return await interaction.response.send_message(f"No role is currently linked to **{rank.value}**.", ephemeral=True)
            mapping.pop(rank.value, None)
            self.bot.store.set_config(interaction.guild.id, "rank_role_ids", mapping)
            await interaction.response.defer(ephemeral=True, thinking=True)
            changed = await self.sync_rank_roles(interaction.guild)
            return await interaction.followup.send(
                f"Removed the automatic role for **{rank.value}**. Synced **{changed}** member(s).",
                ephemeral=True,
            )

        problem = check_assignable_role(interaction.guild, role)
        if problem:
            return await interaction.response.send_message(problem, ephemeral=True)

        for mapped_rank, mapped_role_id in mapping.items():
            if mapped_rank != rank.value and str(mapped_role_id) == str(role.id):
                return await interaction.response.send_message(
                    f"{role.mention} is already linked to **{mapped_rank}**. Use a different role for each rank.",
                    ephemeral=True,
                )

        mapping[rank.value] = role.id
        self.bot.store.set_config(interaction.guild.id, "rank_role_ids", mapping)
        await interaction.response.defer(ephemeral=True, thinking=True)
        changed = await self.sync_rank_roles(interaction.guild)
        await interaction.followup.send(
            f"Linked {role.mention} to **{rank.value}**. Synced **{changed}** member(s). Keep my bot role above this role.",
            ephemeral=True,
        )

    @config.command(name="rank-roles", description="View every automatic military rank role")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def rank_roles(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("Use this command inside a server.", ephemeral=True)

        mapping = self.bot.store.get_config(interaction.guild.id).get("rank_role_ids", {})
        if not isinstance(mapping, dict) or not mapping:
            return await interaction.response.send_message(
                "No automatic rank roles are set. Use **/config rank-role** to link one.",
                ephemeral=True,
            )

        lines: list[str] = []
        for rank, role_id in mapping.items():
            try:
                role = interaction.guild.get_role(int(role_id))
            except (TypeError, ValueError):
                role = None
            lines.append(f"**{rank}:** {role.mention if role else '`Deleted role - set this again`'}")

        embed = discord.Embed(title="Automatic Military Rank Roles", description="\n".join(lines), color=discord.Color.dark_green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @config.command(name="honor-verification", description="Require Roblox verification before players can earn honor")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(enabled="True keeps verified-only honor and rank roles on")
    async def honor_verification(self, interaction: discord.Interaction, enabled: bool):
        if not interaction.guild:
            return await interaction.response.send_message("Use this command inside a server.", ephemeral=True)

        self.bot.store.set_config(interaction.guild.id, "require_verified_for_honor", enabled)
        await interaction.response.defer(ephemeral=True, thinking=True)
        changed = await self.sync_rank_roles(interaction.guild)
        status = "required" if enabled else "not required"
        await interaction.followup.send(
            f"Roblox verification is now **{status}** before a player can earn honor or get automatic rank roles. Synced **{changed}** member(s).",
            ephemeral=True,
        )

    @config.command(name="view", description="View this server's bot settings")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def view(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("Use this command inside a server.", ephemeral=True)
        config = self.bot.store.get_config(interaction.guild.id)
        role = interaction.guild.get_role(int(config["verified_role_id"])) if config.get("verified_role_id") else None
        channel = interaction.guild.get_channel(int(config["log_channel_id"])) if config.get("log_channel_id") else None
        mapping = config.get("rank_role_ids", {})
        rank_role_count = len(mapping) if isinstance(mapping, dict) else 0
        verification_status = "Required" if config.get("require_verified_for_honor", True) else "Off"
        await interaction.response.send_message(
            f"**Bot settings**\n"
            f"Verified role: {role.mention if role else 'Not set'}\n"
            f"Mod-log channel: {channel.mention if channel else 'Not set'}\n"
            f"Honor verification: **{verification_status}**\n"
            f"Automatic rank roles: **{rank_role_count}** configured",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Settings(bot))
