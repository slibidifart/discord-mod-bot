from datetime import timedelta
from uuid import uuid4

import discord
from discord import app_commands
from discord.ext import commands

from .common import check_target, send_log


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="warn", description="Warn a member and save the warning")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(member="Member to warn", reason="Why they are being warned")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        problem = check_target(interaction, member)
        if problem:
            return await interaction.response.send_message(problem, ephemeral=True)
        count = self.bot.store.add_warning(interaction.guild.id, member.id, {
            "id": str(uuid4()),
            "reason": reason,
            "moderator_id": interaction.user.id,
            "created_at": discord.utils.utcnow().isoformat(),
        })
        await send_log(self.bot, interaction.guild, "Member warned", f"{member.mention} was warned by {interaction.user.mention}.\n**Reason:** {reason}")
        await interaction.response.send_message(f"⚠️ Warned {member.mention}. They now have **{count}** saved warning(s).", ephemeral=True)

    @app_commands.command(name="warnings", description="View a member's saved warnings")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        warnings = self.bot.store.get_warnings(interaction.guild.id, member.id)
        if not warnings:
            return await interaction.response.send_message(f"{member.mention} has no saved warnings.", ephemeral=True)
        lines = []
        for index, warning in enumerate(reversed(warnings[-10:]), start=1):
            lines.append(f"**{len(warnings) - index + 1}.** {warning['reason']} — <@{warning['moderator_id']}>")
        await interaction.response.send_message(f"**Warnings for {member} ({len(warnings)})**\n" + "\n".join(lines), ephemeral=True)

    @app_commands.command(name="clearwarnings", description="Delete all saved warnings for a member")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def clearwarnings(self, interaction: discord.Interaction, member: discord.Member):
        count = self.bot.store.clear_warnings(interaction.guild.id, member.id)
        await send_log(self.bot, interaction.guild, "Warnings cleared", f"{interaction.user.mention} cleared **{count}** warning(s) for {member.mention}.")
        await interaction.response.send_message(f"Cleared **{count}** warning(s) for {member.mention}.", ephemeral=True)

    @app_commands.command(name="timeout", description="Temporarily timeout a member")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(member="Member to timeout", minutes="1 to 40320 minutes", reason="Reason for timeout")
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: app_commands.Range[int, 1, 40320], reason: str):
        problem = check_target(interaction, member)
        if problem:
            return await interaction.response.send_message(problem, ephemeral=True)
        try:
            await member.timeout(timedelta(minutes=minutes), reason=reason)
        except discord.Forbidden:
            return await interaction.response.send_message("I need the Moderate Members permission to timeout that member.", ephemeral=True)
        await send_log(self.bot, interaction.guild, "Member timed out", f"{member.mention} was timed out by {interaction.user.mention} for **{minutes} minute(s)**.\n**Reason:** {reason}")
        await interaction.response.send_message(f"Timed out {member.mention} for **{minutes} minute(s)**.", ephemeral=True)

    @app_commands.command(name="untimeout", description="Remove a member's timeout")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(member="Member to untimeout", reason="Reason")
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        problem = check_target(interaction, member)
        if problem:
            return await interaction.response.send_message(problem, ephemeral=True)
        try:
            await member.timeout(None, reason=reason)
        except discord.Forbidden:
            return await interaction.response.send_message("I need the Moderate Members permission to remove that timeout.", ephemeral=True)
        await send_log(self.bot, interaction.guild, "Timeout removed", f"{interaction.user.mention} removed {member.mention}'s timeout.\n**Reason:** {reason}")
        await interaction.response.send_message(f"Removed {member.mention}'s timeout.", ephemeral=True)

    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        problem = check_target(interaction, member)
        if problem:
            return await interaction.response.send_message(problem, ephemeral=True)
        try:
            await member.kick(reason=reason)
        except discord.Forbidden:
            return await interaction.response.send_message("I need the Kick Members permission to do that.", ephemeral=True)
        await send_log(self.bot, interaction.guild, "Member kicked", f"{member.mention} was kicked by {interaction.user.mention}.\n**Reason:** {reason}")
        await interaction.response.send_message(f"Kicked {member.mention}.", ephemeral=True)

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        problem = check_target(interaction, member)
        if problem:
            return await interaction.response.send_message(problem, ephemeral=True)
        try:
            await member.ban(reason=reason)
        except discord.Forbidden:
            return await interaction.response.send_message("I need the Ban Members permission to do that.", ephemeral=True)
        await send_log(self.bot, interaction.guild, "Member banned", f"{member.mention} was banned by {interaction.user.mention}.\n**Reason:** {reason}")
        await interaction.response.send_message(f"Banned {member.mention}.", ephemeral=True)

    @app_commands.command(name="purge", description="Delete recent messages in this channel")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
        if not isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
            return await interaction.response.send_message("Use this command in a text channel.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        deleted = await interaction.channel.purge(limit=amount, bulk=True)
        await send_log(self.bot, interaction.guild, "Messages purged", f"{interaction.user.mention} deleted **{len(deleted)}** message(s) in {interaction.channel.mention}.")
        await interaction.followup.send(f"Deleted **{len(deleted)}** message(s). Discord will not bulk-delete messages older than 14 days.", ephemeral=True)

    @app_commands.command(name="lock", description="Stop @everyone from sending messages in this channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction, reason: str = "No reason provided"):
        if not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message("Use this command in a server text channel.", ephemeral=True)
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=reason)
        await send_log(self.bot, interaction.guild, "Channel locked", f"{interaction.user.mention} locked {interaction.channel.mention}.\n**Reason:** {reason}")
        await interaction.response.send_message(f"🔒 Locked {interaction.channel.mention}.", ephemeral=True)

    @app_commands.command(name="unlock", description="Let @everyone send messages in this channel again")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction, reason: str = "No reason provided"):
        if not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message("Use this command in a server text channel.", ephemeral=True)
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=reason)
        await send_log(self.bot, interaction.guild, "Channel unlocked", f"{interaction.user.mention} unlocked {interaction.channel.mention}.\n**Reason:** {reason}")
        await interaction.response.send_message(f"🔓 Unlocked {interaction.channel.mention}.", ephemeral=True)

    @app_commands.command(name="slowmode", description="Set this channel's slowmode")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 21600]):
        if not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message("Use this command in a server text channel.", ephemeral=True)
        await interaction.channel.edit(slowmode_delay=seconds, reason=f"Changed by {interaction.user}")
        await send_log(self.bot, interaction.guild, "Slowmode changed", f"{interaction.user.mention} set {interaction.channel.mention} slowmode to **{seconds} second(s)**.")
        await interaction.response.send_message("Slowmode is now off." if seconds == 0 else f"Slowmode is now **{seconds} second(s)**.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
