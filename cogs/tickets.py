import discord
from discord import app_commands
from discord.ext import commands


class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Close Ticket', style=discord.ButtonStyle.danger, custom_id='close_ticket_button')
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message('This can only be used inside a server text channel.', ephemeral=True)
            return

        if not channel.name.startswith('ticket-'):
            await interaction.response.send_message('This is not a ticket channel.', ephemeral=True)
            return

        await interaction.response.send_message('Closing this ticket in 3 seconds...')
        await channel.delete(reason=f'Ticket closed by {interaction.user}')


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Create Ticket', style=discord.ButtonStyle.primary, custom_id='create_ticket_button')
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        if guild is None:
            await interaction.response.send_message('Tickets only work inside a server.', ephemeral=True)
            return

        existing_ticket = discord.utils.get(guild.text_channels, name=f'ticket-{user.id}')
        if existing_ticket:
            await interaction.response.send_message(f'You already have a ticket open: {existing_ticket.mention}', ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        staff_role = discord.utils.get(guild.roles, name='Staff') or discord.utils.get(guild.roles, name='Moderator')
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        category = discord.utils.get(guild.categories, name='Tickets')
        if category is None:
            category = await guild.create_category('Tickets')

        ticket_channel = await guild.create_text_channel(
            name=f'ticket-{user.id}',
            category=category,
            overwrites=overwrites,
            reason=f'Ticket created by {user}'
        )

        embed = discord.Embed(
            title='Support Ticket',
            description=f'Hi {user.mention}, explain what you need help with. A staff member will reply soon.',
            color=discord.Color.blurple()
        )
        embed.set_footer(text='Press Close Ticket when this is solved.')

        await ticket_channel.send(content=user.mention, embed=embed, view=TicketCloseView())
        await interaction.response.send_message(f'Created your ticket: {ticket_channel.mention}', ephemeral=True)


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='ticketpanel', description='Send a ticket panel in this channel')
    @app_commands.checks.has_permissions(manage_channels=True)
    async def ticketpanel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title='Need Help?',
            description='Click the button below to create a private support ticket.',
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, view=TicketPanelView())

    @app_commands.command(name='close', description='Close the current ticket channel')
    @app_commands.checks.has_permissions(manage_channels=True)
    async def close(self, interaction: discord.Interaction):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or not channel.name.startswith('ticket-'):
            await interaction.response.send_message('This command can only be used in a ticket channel.', ephemeral=True)
            return

        await interaction.response.send_message('Closing this ticket...')
        await channel.delete(reason=f'Ticket closed by {interaction.user}')


async def setup(bot):
    bot.add_view(TicketPanelView())
    bot.add_view(TicketCloseView())
    await bot.add_cog(Tickets(bot))
