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

        previous, current = self.bot.store.change_honor(interaction.guild.id, member.id, amount)
        previous_rank_index, previous_rank, _, _, _ = rank_details(previous)
        current_rank_index, current_rank, _, _, _ = rank_details(current)

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
        current = self.bot.store.set_honor(interaction.guild.id, member.id, amount)
        _, previous_rank, _, _, _ = rank_details(previous)
        _, current_rank, _, _, _ = rank_details(current)

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
