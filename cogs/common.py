import discord


async def send_log(bot: discord.Client, guild: discord.Guild, title: str, description: str) -> None:
    config = bot.store.get_config(guild.id)
    channel_id = config.get("log_channel_id")
    if not channel_id:
        return

    channel = guild.get_channel(int(channel_id))
    if channel is None:
        try:
            channel = await guild.fetch_channel(int(channel_id))
        except discord.DiscordException:
            return

    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        return

    embed = discord.Embed(title=title, description=description)
    await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())


def check_target(interaction: discord.Interaction, target: discord.Member) -> str | None:
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        return "Use this command inside a server."
    if target.id == interaction.user.id:
        return "Choose another server member."
    if target.id == interaction.guild.owner_id:
        return "I cannot moderate the server owner."

    actor = interaction.user
    if actor.id != interaction.guild.owner_id and target.top_role >= actor.top_role:
        return "You cannot moderate someone with the same or a higher role than you."

    me = interaction.guild.me
    if me is None or target.top_role >= me.top_role:
        return "Move my bot role above that member's highest role first."
    return None


def check_assignable_role(guild: discord.Guild, role: discord.Role) -> str | None:
    if role.is_default() or role.managed:
        return "Choose a normal server role, not @everyone or an integration-managed role."
    me = guild.me
    if me is None or role >= me.top_role:
        return "Move my bot role above that role first, then try again."
    return None
