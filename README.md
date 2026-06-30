# Discord Bot

A simple Discord moderation bot with slash commands, tickets, and basic AutoMod.

## Setup

1. Install packages:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file:
   ```env
   DISCORD_TOKEN=your_bot_token_here
   ```

3. Run the bot:
   ```bash
   python main.py
   ```

## Commands

### General
- `/ping` - Check if the bot is online.

### Moderation
- `/kick` - Kick a member.
- `/ban` - Ban a member.

### Tickets
- `/ticketpanel` - Sends a ticket panel with a button.
- `/close` - Closes the current ticket channel.

Ticket channels are created inside a `Tickets` category. Staff can see tickets if your server has a role named `Staff` or `Moderator`.

### AutoMod
- `/automod_status` - Shows what AutoMod is filtering.

AutoMod currently removes:
- Spam
- Discord invite links
- Links
- Words listed in `BLOCKED_WORDS` inside `cogs/automod.py`

## Required Discord Developer Portal Settings

Turn on these bot gateway intents:
- Server Members Intent
- Message Content Intent

## Recommended Bot Permissions

When inviting the bot, give it:
- Manage Channels
- Manage Messages
- Moderate Members
- Kick Members
- Ban Members
- Read Messages/View Channels
- Send Messages
- Use Slash Commands
