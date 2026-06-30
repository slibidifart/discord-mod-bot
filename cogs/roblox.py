import asyncio
import re
import secrets
import time
from datetime import datetime, timezone

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from .common import check_assignable_role, send_log

ROBLOX_API = "https://users.roblox.com/v1"
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")


async def roblox_request(method: str, url: str, **kwargs):
    timeout = aiohttp.ClientTimeout(total=12)
    headers = {"User-Agent": "DiscordRobloxManagementBot/1.0"}
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        async with session.request(method, url, **kwargs) as response:
            if response.status == 429:
                raise RuntimeError("Roblox is rate-limiting requests right now. Try again in a minute.")
            if response.status >= 400:
                raise RuntimeError("Roblox could not complete that request right now.")
            return await response.json()


async def find_user(username: str) -> dict:
    username = username.strip()
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError("That does not look like a valid Roblox username.")

    payload = {"usernames": [username], "excludeBannedUsers": False}
    data = await roblox_request("POST", f"{ROBLOX_API}/usernames/users", json=payload)
    user = (data.get("data") or [None])[0]
    if not user or not user.get("id"):
        raise ValueError("I could not find that Roblox username.")

    return {
        "id": int(user["id"]),
        "username": user["name"],
        "display_name": user.get("displayName") or user["name"],
    }


async def get_profile(user_id: int) -> dict:
    data = await roblox_request("GET", f"{ROBLOX_API}/users/{user_id}")
    return {
        "id": int(data["id"]),
        "username": data["name"],
        "display_name": data.get("displayName") or data["name"],
        "description": data.get("description") or "",
    }


def profile_url(user_id: int) -> str:
    return f"https://www.roblox.com/users/{user_id}/profile"


def discord_time(unix_time: int) -> str:
    return f"<t:{unix_time}:R>"


class RobloxVerification(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    verify = app_commands.Group(name="verify", description="Link your Discord account to a Roblox profile")

    @verify.command(name="start", description="Start Roblox verification")
    @app_commands.describe(username="Your exact Roblox username")
    async def verify_start(self, interaction: discord.Interaction, username: str):
        if not interaction.guild:
            return await interaction.response.send_message("Use this command inside a server.", ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)
        user = await find_user(username)
        code = f"DISCORD-{secrets.token_hex(4).upper()}"
        expires_at = int(time.time()) + 15 * 60

        self.bot.store.set_pending(interaction.guild.id, interaction.user.id, {
            **user,
            "code": code,
            "expires_at": expires_at,
        })

        await interaction.followup.send(
            f"Found **{user['display_name']}** (@{user['username']}). Open <{profile_url(user['id'])}> and paste this exact code anywhere in the profile **About** section:\n\n"
            f"`{code}`\n\nSave your profile, then use **/verify check** within {discord_time(expires_at)}. You can remove the code after you are verified.",
            ephemeral=True,
        )

    @verify.command(name="check", description="Finish Roblox verification")
    async def verify_check(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("Use this command inside a server.", ephemeral=True)

        pending = self.bot.store.get_pending(interaction.guild.id, interaction.user.id)
        if not pending:
            return await interaction.response.send_message("You do not have a verification waiting. Start with **/verify start**.", ephemeral=True)
        if int(time.time()) > pending["expires_at"]:
            self.bot.store.remove_pending(interaction.guild.id, interaction.user.id)
            return await interaction.response.send_message("That verification code expired. Use **/verify start** again for a fresh one.", ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)
        profile = await get_profile(int(pending["id"]))
        if pending["code"] not in profile["description"]:
            return await interaction.followup.send("I could not see the code in that Roblox profile yet. Make sure it is saved in the **About** section, then try again.", ephemeral=True)

        config = self.bot.store.get_config(interaction.guild.id)
        role_notice = ""
        role_id = config.get("verified_role_id")
        if role_id:
            role = interaction.guild.get_role(int(role_id))
            if role is None:
                return await interaction.followup.send("The configured Verified role no longer exists. Ask staff to set it again with **/config verified-role**.", ephemeral=True)
            problem = check_assignable_role(interaction.guild, role)
            if problem:
                return await interaction.followup.send(problem, ephemeral=True)
            if not isinstance(interaction.user, discord.Member):
                return await interaction.followup.send("I could not find your server member record.", ephemeral=True)
            await interaction.user.add_roles(role, reason="Roblox profile verification completed")
            role_notice = f" and gave you {role.mention}"

        self.bot.store.set_verification(interaction.guild.id, interaction.user.id, {
            "id": profile["id"],
            "username": profile["username"],
            "display_name": profile["display_name"],
            "verified_at": datetime.now(timezone.utc).isoformat(),
        })

        # A player who already earned honor can receive their configured rank role now.
        if isinstance(interaction.user, discord.Member):
            honor_cog = self.bot.get_cog("Honor")
            if honor_cog is not None:
                await honor_cog.sync_rank_role(interaction.user)

        await send_log(self.bot, interaction.guild, "Roblox verified", f"{interaction.user.mention} linked [{profile['display_name']} (@{profile['username']})]({profile_url(profile['id'])}).")
        await interaction.followup.send(f"✅ Verified as **{profile['display_name']}** (@{profile['username']}){role_notice}.", ephemeral=True)

    @verify.command(name="unlink", description="Remove your saved Roblox link")
    async def verify_unlink(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("Use this command inside a server.", ephemeral=True)

        verification = self.bot.store.remove_verification(interaction.guild.id, interaction.user.id)
        if not verification:
            return await interaction.response.send_message("You do not currently have a Roblox account linked here.", ephemeral=True)

        role_id = self.bot.store.get_config(interaction.guild.id).get("verified_role_id")
        role = interaction.guild.get_role(int(role_id)) if role_id else None
        if role and isinstance(interaction.user, discord.Member) and role in interaction.user.roles:
            try:
                await interaction.user.remove_roles(role, reason="Roblox account unlinked by member")
            except discord.Forbidden:
                pass

        # Verification is required for rank roles by default, so remove any configured rank role too.
        if isinstance(interaction.user, discord.Member):
            honor_cog = self.bot.get_cog("Honor")
            if honor_cog is not None:
                await honor_cog.sync_rank_role(interaction.user)

        await send_log(self.bot, interaction.guild, "Roblox unlinked", f"{interaction.user.mention} removed their Roblox link for **{verification['username']}**.")
        await interaction.response.send_message(f"Your Roblox link for **{verification['username']}** was removed.", ephemeral=True)

    @app_commands.command(name="roblox", description="Look up a Roblox profile")
    @app_commands.describe(username="Roblox username")
    async def roblox(self, interaction: discord.Interaction, username: str):
        await interaction.response.defer(ephemeral=True, thinking=True)
        user = await find_user(username)
        await interaction.followup.send(
            f"**{user['display_name']}** (@{user['username']})\nRoblox ID: `{user['id']}`\n<{profile_url(user['id'])}>",
            ephemeral=True,
        )

    @app_commands.command(name="whois", description="Show a member's linked Roblox profile")
    @app_commands.describe(member="Discord member")
    async def whois(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.guild:
            return await interaction.response.send_message("Use this command inside a server.", ephemeral=True)
        verification = self.bot.store.get_verification(interaction.guild.id, member.id)
        if not verification:
            return await interaction.response.send_message(f"{member.mention} has not linked a Roblox account in this server.", ephemeral=True)
        await interaction.response.send_message(
            f"{member.mention} is linked to **{verification['display_name']}** (@{verification['username']})\n<{profile_url(verification['id'])}>",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(RobloxVerification(bot))
