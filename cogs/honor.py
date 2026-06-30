import discord
from discord import app_commands
from discord.ext import commands

from .common import send_log

# Change these thresholds later if your military simulator uses a different rank ladder.
RANKS: tuple[tuple[str, int], ...] = (
    ("Recruit", 0),
    ("Senior Recruit", 10),
    ("Private", 25),
    ("Private First Class", 50),
    ("Lance Corporal", 85),
    ("Corporal", 125),
    ("Sergeant", 175),
    ("Staff Sergeant", 240),
    ("Sergeant First Class", 320),
    ("Master Sergeant", 420),
    ("Second Lieutenant", 550),
    ("First Lieutenant", 700),
    ("Captain", 900),
    ("Major", 1150),
    ("Lieutenant Colonel", 1450),
    ("Colonel", 1800),
    ("General", 2200),
)

RANK_CHOICES = [
    app_commands.Choice(name=f"{rank_name} ({threshold} honor)", value=rank_name)
    for rank_name, threshold in RANKS
]


def rank_details(honor: int) -> tuple[int, str, str | None, int, int | None]:
    index = 0
    for possible_index, (_, threshold) in enumerate(RANKS):
        if honor >= threshold:
            index = possible_index
        else:
            break

    rank_name, current_threshold = RANKS[index]
    if index == len(RANKS) - 1:
        return index, rank_name, None, current_threshold, None

    next_name, next_threshold = RANKS[index + 1]
    return index, rank_name, next_name, current_threshold, next_threshold


def progress_bar(honor: int, current_threshold: int, next_threshold: int | None) -> tuple[str, str]:
    if next_threshold is None:
        return "🟩" * 10, "Maximum rank reached"

    needed = next_threshold - current_threshold
    earned = max(0, honor - current_threshold)
    filled = min(10, int((earned / needed) * 10)) if needed else 10
    bar = "🟩" * filled + "⬛" * (10 - filled)
    return bar, f"{earned}/{needed} honor to next rank"


def honor_embed(member: discord.Member, honor: int) -> discord.Embed:
    _, current_rank, next_rank, current_threshold, next_threshold = rank_details(honor)
    bar, progress_text = progress_bar(honor, current_threshold, next_threshold)

    embed = discord.Embed(
        title=f"{member.display_name}'s Honor",
        color=discord.Color.dark_green(),
    )
    embed.add_field(name="Player", value=member.display_name, inline=False)
    embed.add_field(name="Honor", value=str(honor), inline=True)
    embed.add_field(name="Current Rank", value=current_rank, inline=True)
    embed.add_field(name="Next Rank", value=next_rank or "Maximum Rank", inline=True)
    embed.add_field(name="Progress", value=f"{bar}\n{progress_text}", inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="Military Simulator Honor System")
    return embed


class Honor(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def verification_is_required(self, guild_id: int) -> bool:
        return bool(self.bot.store.get_config(guild_id).get("require_verified_for_honor", True))

    def is_verified(self, guild_id: int, member_id: int) -> bool:
        return self.bot.store.get_verification(guild_id, member_id) is not None

    def can_earn_honor(self, guild_id: int, member_id: int) -> bool:
        return not self.verification_is_required(guild_id) or self.is_verified(guild_id, member_id)

    def verification_message(self, member: discord.Member) -> str:
        return (
            f"{member.mention} must complete **/verify start** and **/verify check** before they can earn honor "
            "or receive a military rank role."
        )

    async def sync_rank_role(self, member: discord.Member) -> bool:
        """Sync configured military rank roles for one member. Returns True when a role changed."""
        guild = member.guild
        config = self.bot.store.get_config(guild.id)
        role_mapping = config.get("rank_role_ids", {})
        if not isinstance(role_mapping, dict):
            return False

        bot_member = guild.me
        if bot_member is None:
            return False

        configured_roles: dict[str, discord.Role] = {}
        for rank_name, raw_role_id in role_mapping.items():
            try:
                role = guild.get_role(int(raw_role_id))
            except (TypeError, ValueError):
                role = None
            if role is not None:
                configured_roles[rank_name] = role

        managed_roles = {role.id: role for role in configured_roles.values()}
        honor = self.bot.store.get_honor(guild.id, member.id)
        _, current_rank, _, _, _ = rank_details(honor)
        should_have_rank_role = self.can_earn_honor(guild.id, member.id)
        desired_role = configured_roles.get(current_rank) if should_have_rank_role else None

        removable = [
            role for role in managed_roles.values()
            if role in member.roles
            and role != desired_role
            and not role.managed
            and role < bot_member.top_role
        ]
        addable = (
            desired_role
            if desired_role is not None
            and desired_role not in member.roles
            and not desired_role.managed
            and desired_role < bot_member.top_role
            else None
        )

        changed = False
        try:
            if removable:
                await member.remove_roles(*removable, reason="Automatic military rank role sync")
                changed = True
            if addable:
                await member.add_roles(addable, reason="Automatic military rank role sync")
                changed = True
        except discord.Forbidden:
            return changed
        return changed

    async def sync_guild_rank_roles(self, guild: discord.Guild) -> int:
        """Sync cached non-bot members after rank-role configuration changes."""
        changed = 0
        for member in guild.members:
            if member.bot:
                continue
            if await self.sync_rank_role(member):
                changed += 1
        return changed

    @app_commands.command(name="honor", description="View a player's military honor and rank")
    @app_commands.describe(member="Leave empty to view your own honor")
    async def honor(self, interaction: discord.Interaction, member: discord.Member | None = None):
        if not interaction.guild:
            return await interaction.response.send_message("Use this command inside a server.", ephemeral=True)

        target = member or interaction.user
        if not isinstance(target, discord.Member):
            return await interaction.response.send_message("I could not find that server member.", ephemeral=True)

        total = self.bot.store.get_honor(interaction.guild.id, target.id)
        await interaction.response.send_message(embed=honor_embed(target, total))

    @app_commands.command(name="leaderboard", description="See the top military honor players")
    @app_commands.describe(limit="How many players to show")
    async def leaderboard(self, interaction: discord.Interaction, limit: app_commands.Range[int, 3, 20] = 10):
        if not interaction.guild:
            return await interaction.response.send_message("Use this command inside a server.", ephemeral=True)

        entries = self.bot.store.get_honor_leaderboard(interaction.guild.id, limit)
        entries = [(user_id, honor) for user_id, honor in entries if honor > 0]
        if not entries:
            return await interaction.response.send_message("No honor has been earned yet. The leaderboard is waiting for its first recruit. 🫡")

        medals = ("🥇", "🥈", "🥉")
        lines: list[str] = []
        for position, (user_id, honor) in enumerate(entries, start=1):
            member = interaction.guild.get_member(user_id)
            player = member.display_name if member else f"<@{user_id}>"
            _, rank, _, _, _ = rank_details(honor)
            marker = medals[position - 1] if position <= 3 else f"`#{position}`"
            lines.append(f"{marker} **{player}** — **{honor}** honor · {rank}")

        embed = discord.Embed(
            title="Military Honor Leaderboard",
            description="\n".join(lines),
            color=discord.Color.dark_green(),
        )
        embed.set_footer(text="Keep training, keep climbing.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="add_honor", description="Give a player military honor")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(member="Player receiving honor", amount="How much honor to add", reason="Why they earned it")
    async def add_honor(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: app_commands.Range[int, 1, 100000],
        reason: str = "No reason provided",
    ):
        if not interaction.guild:
            return await interaction.response.send_message("Use this command inside a server.", ephemeral=True)
        if member.bot:
            return await interaction.response.send_message("Bots cannot receive honor.", ephemeral=True)
        if not self.can_earn_honor(interaction.guild.id, member.id):
            return await interaction.response.send_message(self.verification_message(member), ephemeral=True)

        previous, current = self.bot.store.change_honor(interaction.guild.id, member.id, amount)
        previous_rank_index, previous_rank, _, _, _ = rank_details(previous)
        current_rank_index, current_rank, _, _, _ = rank_details(current)
        await self.sync_rank_role(member)

        message = f"Added **{amount} honor** to {member.mention}. Total: **{current}**."
        if current_rank_index > previous_rank_index:
            message += f" 🫡 **Promotion:** {previous_rank} → **{current_rank}**"

        await send_log(
            self.bot,
            interaction.guild,
            "Honor added",
            f"{interaction.user.mention} added **{amount} honor** to {member.mention}.\n"
            f"**Total:** {current}\n**Reason:** {reason}",
        )
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="remove_honor", description="Remove military honor from a player")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(member="Player losing honor", amount="How much honor to remove", reason="Why it is being removed")
    async def remove_honor(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: app_commands.Range[int, 1, 100000],
        reason: str = "No reason provided",
    ):
        if not interaction.guild:
            return await interaction.response.send_message("Use this command inside a server.", ephemeral=True)
        if member.bot:
            return await interaction.response.send_message("Bots cannot have honor changed.", ephemeral=True)

        previous, current = self.bot.store.change_honor(interaction.guild.id, member.id, -amount)
        previous_rank_index, previous_rank, _, _, _ = rank_details(previous)
        current_rank_index, current_rank, _, _, _ = rank_details(current)
        await self.sync_rank_role(member)

        message = f"Removed **{previous - current} honor** from {member.mention}. Total: **{current}**."
        if current_rank_index < previous_rank_index:
            message += f" **Rank changed:** {previous_rank} → **{current_rank}**"

        await send_log(
            self.bot,
            interaction.guild,
            "Honor removed",
            f"{interaction.user.mention} removed **{previous - current} honor** from {member.mention}.\n"
            f"**Total:** {current}\n**Reason:** {reason}",
        )
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="set_honor", description="Set a player's military honor to an exact amount")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(member="Player whose honor you are setting", amount="New honor total", reason="Why it is being changed")
    async def set_honor(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: app_commands.Range[int, 0, 1000000],
        reason: str = "No reason provided",
    ):
        if not interaction.guild:
            return await interaction.response.send_message("Use this command inside a server.", ephemeral=True)
        if member.bot:
            return await interaction.response.send_message("Bots cannot have honor changed.", ephemeral=True)

        previous = self.bot.store.get_honor(interaction.guild.id, member.id)
        if amount > previous and not self.can_earn_honor(interaction.guild.id, member.id):
            return await interaction.response.send_message(self.verification_message(member), ephemeral=True)

        current = self.bot.store.set_honor(interaction.guild.id, member.id, amount)
        _, previous_rank, _, _, _ = rank_details(previous)
        _, current_rank, _, _, _ = rank_details(current)
        await self.sync_rank_role(member)

        await send_log(
            self.bot,
            interaction.guild,
            "Honor set",
            f"{interaction.user.mention} set {member.mention}'s honor from **{previous}** to **{current}**.\n"
            f"**Rank:** {previous_rank} → {current_rank}\n**Reason:** {reason}",
        )
        await interaction.response.send_message(
            f"Set {member.mention}'s honor to **{current}**. Rank: **{current_rank}**.",
            ephemeral=True,
        )

    @app_commands.command(name="honor_ranks", description="View the honor requirements for every military rank")
    async def honor_ranks(self, interaction: discord.Interaction):
        lines = [f"**{threshold}** — {name}" for name, threshold in RANKS]
        embed = discord.Embed(
            title="Military Honor Ranks",
            description="\n".join(lines),
            color=discord.Color.dark_green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Honor(bot))
