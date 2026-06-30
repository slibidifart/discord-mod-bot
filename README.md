# Discord Roblox Management Bot

A Discord bot with Roblox profile-code verification, a military honor/rank system, and server-management tools.

## What it does

- `/verify start`, `/verify check`, `/verify unlink` — links a Discord user to a Roblox profile without asking for their password, cookie, or Roblox login.
- `/roblox` and `/whois` — looks up Roblox profiles and saved server links.
- `/honor` — posts a military-style honor card with the player's total, current rank, next rank, and progress bar.
- `/leaderboard` — shows the server's top military honor players.
- `/add_honor`, `/remove_honor`, and `/set_honor` — staff commands for changing a player's honor. Promotion changes are detected automatically.
- `/honor_ranks` — shows the default military rank ladder and the honor needed for each rank.
- `/config rank-role` and `/config rank-roles` — connects Discord roles to military ranks and keeps them updated automatically.
- `/config honor-verification` — controls whether Roblox verification is required before players can earn honor and receive rank roles. It is **on by default**.
- `/config verified-role`, `/config log-channel`, `/config view` — sets the role for verified members and a moderation log channel.
- `/warn`, `/warnings`, `/clearwarnings`, `/timeout`, `/untimeout`, `/kick`, `/ban`, `/purge`, `/lock`, `/unlock`, `/slowmode`, and `/ping`.

## Honor system

The honor system starts with this military-style ladder:

| Rank | Honor needed |
| --- | ---: |
| Recruit | 0 |
| Senior Recruit | 10 |
| Private | 25 |
| Private First Class | 50 |
| Lance Corporal | 85 |
| Corporal | 125 |
| Sergeant | 175 |
| Staff Sergeant | 240 |
| Sergeant First Class | 320 |
| Master Sergeant | 420 |
| Second Lieutenant | 550 |
| First Lieutenant | 700 |
| Captain | 900 |
| Major | 1,150 |
| Lieutenant Colonel | 1,450 |
| Colonel | 1,800 |
| General | 2,200 |

Staff needs **Moderate Members** to use `/add_honor` and `/remove_honor`; `/set_honor` requires **Manage Server**. The exact rank list is in `cogs/honor.py`, so you can change the names or honor requirements later.

### Verified-only ranks

Roblox verification is required before a player can gain honor or receive an automatic military role. They must run `/verify start` and `/verify check` first. Staff can still remove honor when needed for discipline.

### Automatic rank roles

Create your Discord rank roles first, then put the bot's role **above every rank role**. Link them one by one:

```text
/config rank-role rank:Recruit role:@Recruit
/config rank-role rank:Senior Recruit role:@Senior Recruit
/config rank-role rank:Private role:@Private
```

The bot removes only roles that you linked as rank roles, then gives the one matching the player's current honor rank. Use `/config rank-roles` to review your setup. Existing eligible members are synced whenever you add or change one of these mappings.

## Roblox verification flow

1. A member runs `/verify start username:TheirRobloxUsername`.
2. The bot gives them a one-time code that expires in 15 minutes.
3. They paste the code into their Roblox profile **About** section and save it.
4. They run `/verify check`.
5. The bot checks the public profile description, gives the configured Verified role, and syncs their military rank role if they already have honor.

The bot only saves the public Roblox user ID, username, display name, and verification time for that server. It never asks for Roblox passwords, cookies, or account access.

## Railway setup

1. Push this project to GitHub and create a Railway project from the repository.
2. In Railway **Variables**, add `TOKEN` with your Discord bot token. You can also add `GUILD_ID` with your server ID so new slash commands show up immediately.
3. Railway uses the included `Procfile` and starts the bot with `python main.py`.
4. In the Discord Developer Portal, enable **Server Members Intent** under **Bot → Privileged Gateway Intents**.
5. Invite the bot with the `bot` and `applications.commands` scopes. Give it the permissions it needs: Manage Roles, Moderate Members, Kick Members, Ban Members, Manage Messages, Manage Channels, and View/Audit Log as wanted.
6. Put the bot's role above the Verified role and every military rank role it needs to manage.
7. In your server, run `/config verified-role`, `/config log-channel`, then set your rank roles with `/config rank-role`.

## Keeping data after redeploys

Warnings, honor totals, rank-role settings, and verification links are stored in `data/bot_data.json`. Railway's normal filesystem can reset on a redeploy, so attach a Railway Volume and set `DATA_FILE` to a path inside that volume if you want to preserve them long-term.
