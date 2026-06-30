# Discord Roblox Management Bot

A Discord bot with Roblox profile-code verification and normal server-management tools.

## What it does

- `/verify start`, `/verify check`, `/verify unlink` — links a Discord user to a Roblox profile without asking for their password, cookie, or Roblox login.
- `/roblox` and `/whois` — looks up Roblox profiles and saved server links.
- `/config verified-role`, `/config log-channel`, `/config view` — sets the role for verified members and a moderation log channel.
- `/warn`, `/warnings`, `/clearwarnings`, `/timeout`, `/untimeout`, `/kick`, `/ban`, `/purge`, `/lock`, `/unlock`, `/slowmode`, and `/ping`.

## Roblox verification flow

1. A member runs `/verify start username:TheirRobloxUsername`.
2. The bot gives them a one-time code that expires in 15 minutes.
3. They paste the code into their Roblox profile **About** section and save it.
4. They run `/verify check`.
5. The bot checks the public profile description and gives the configured Verified role.

The bot only saves the public Roblox user ID, username, display name, and verification time for that server. It never asks for Roblox passwords, cookies, or account access.

## Railway setup

1. Push this project to GitHub and create a Railway project from the repository.
2. In Railway **Variables**, add `TOKEN` with your Discord bot token. You can also add `GUILD_ID` with your server ID so new slash commands show up immediately.
3. Railway uses the included `Procfile` and starts the bot with `python main.py`.
4. In the Discord Developer Portal, enable **Server Members Intent** under **Bot → Privileged Gateway Intents**.
5. Invite the bot with the `bot` and `applications.commands` scopes. Give it the permissions it needs: Manage Roles, Moderate Members, Kick Members, Ban Members, Manage Messages, Manage Channels, and View/Audit Log as wanted.
6. Put the bot's role above the Verified role and above roles it should moderate.
7. In your server, run `/config verified-role` and `/config log-channel`.

## Keeping data after redeploys

Warnings and verification links are stored in `data/bot_data.json`. Railway's normal filesystem can reset on a redeploy, so attach a Railway Volume and set `DATA_FILE` to a path inside that volume if you want to preserve them long-term.
