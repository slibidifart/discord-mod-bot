import "dotenv/config";
import crypto from "node:crypto";
import {
  Client,
  EmbedBuilder,
  Events,
  GatewayIntentBits,
  PermissionFlagsBits,
  REST,
  Routes,
} from "discord.js";
import { commands } from "./commands.js";
import { findRobloxUser, getRobloxProfile, robloxProfileUrl } from "./roblox.js";
import {
  addWarning,
  clearWarnings,
  createPendingVerification,
  deletePendingVerification,
  getConfig,
  getPendingVerification,
  getVerification,
  getWarnings,
  initializeStore,
  removeVerification,
  saveVerification,
  setConfig,
} from "./store.js";

const token = process.env.TOKEN || process.env.DISCORD_TOKEN;
const clientId = process.env.CLIENT_ID;
const guildId = process.env.GUILD_ID;

if (!token) {
  throw new Error("TOKEN is missing. Add your Discord bot token in Railway Variables, then redeploy.");
}

initializeStore();

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMembers],
});

function reply(interaction, content) {
  return interaction.editReply({ content, allowedMentions: { parse: [] } });
}

function timestamp(date = Date.now()) {
  return `<t:${Math.floor(new Date(date).getTime() / 1000)}:f>`;
}

async function syncCommands() {
  if (process.env.SYNC_COMMANDS === "false") return;
  if (!clientId || !guildId) {
    console.warn("CLIENT_ID or GUILD_ID is missing, so slash commands were not synced.");
    return;
  }

  const rest = new REST({ version: "10" }).setToken(token);
  await rest.put(Routes.applicationGuildCommands(clientId, guildId), { body: commands });
  console.log(`Synced ${commands.length} slash commands to server ${guildId}.`);
}

async function sendLog(guild, title, description) {
  const { logChannelId } = getConfig(guild.id);
  if (!logChannelId) return;

  const channel = await guild.channels.fetch(logChannelId).catch(() => null);
  if (!channel?.isTextBased()) return;

  const embed = new EmbedBuilder()
    .setTitle(title)
    .setDescription(description)
    .setTimestamp();

  await channel.send({ embeds: [embed], allowedMentions: { parse: [] } }).catch(() => null);
}

async function getTargetMember(interaction, user) {
  if (!user || user.id === interaction.user.id) {
    throw new Error("Choose another server member.");
  }

  const target = await interaction.guild.members.fetch(user.id).catch(() => null);
  if (!target) throw new Error("That user is not currently in this server.");
  if (target.id === interaction.guild.ownerId) throw new Error("I cannot moderate the server owner.");

  const actor = interaction.member;
  const actorIsOwner = interaction.user.id === interaction.guild.ownerId;
  if (!actorIsOwner && target.roles.highest.position >= actor.roles.highest.position) {
    throw new Error("You cannot moderate someone with the same or a higher role than you.");
  }

  return target;
}

async function requireConfigurableRole(guild, role) {
  const botMember = guild.members.me ?? (await guild.members.fetchMe());
  if (role.id === guild.id || role.managed) {
    throw new Error("Pick a normal server role, not @everyone or an integration-managed role.");
  }
  if (role.position >= botMember.roles.highest.position) {
    throw new Error("Move my bot role above that role first, then try again.");
  }
}

async function handleVerification(interaction) {
  const action = interaction.options.getSubcommand();
  const guild = interaction.guild;

  if (action === "start") {
    const username = interaction.options.getString("username", true);
    const user = await findRobloxUser(username);
    const code = `DISCORD-${crypto.randomBytes(4).toString("hex").toUpperCase()}`;
    const expiresAt = Date.now() + 15 * 60 * 1000;

    createPendingVerification(guild.id, interaction.user.id, {
      ...user,
      code,
      expiresAt,
    });

    return reply(
      interaction,
      `Found **${user.displayName}** (@${user.username}). Open <${robloxProfileUrl(user.id)}> and paste this exact code anywhere in the profile **About** section:\n\n\`${code}\`\n\nSave your profile, then run **/verify check** before ${timestamp(expiresAt)}. You can remove the code after verification.`,
    );
  }

  if (action === "check") {
    const pending = getPendingVerification(guild.id, interaction.user.id);
    if (!pending) return reply(interaction, "You do not have a verification waiting. Start with **/verify start**.");
    if (Date.now() > pending.expiresAt) {
      deletePendingVerification(guild.id, interaction.user.id);
      return reply(interaction, "That verification code expired. Run **/verify start** again for a fresh code.");
    }

    const profile = await getRobloxProfile(pending.id);
    if (!profile.description.includes(pending.code)) {
      return reply(interaction, "I could not see your code in that Roblox profile yet. Make sure it is saved in the **About** section, then try again.");
    }

    const config = getConfig(guild.id);
    const member = await guild.members.fetch(interaction.user.id);
    let roleNotice = "";

    if (config.verifiedRoleId) {
      const role = guild.roles.cache.get(config.verifiedRoleId) ?? (await guild.roles.fetch(config.verifiedRoleId).catch(() => null));
      if (!role) return reply(interaction, "Your server's Verified role was deleted. Ask staff to run **/config verified-role** again.");
      await requireConfigurableRole(guild, role);
      await member.roles.add(role, "Roblox profile verification completed");
      roleNotice = ` and gave you ${role}`;
    }

    saveVerification(guild.id, interaction.user.id, {
      id: pending.id,
      username: profile.username,
      displayName: profile.displayName,
      verifiedAt: new Date().toISOString(),
    });

    await sendLog(guild, "Roblox verified", `${interaction.user} linked [${profile.displayName} (@${profile.username})](${robloxProfileUrl(profile.id)}).`);
    return reply(interaction, `✅ Verified as **${profile.displayName}** (@${profile.username})${roleNotice}.`);
  }

  const verification = removeVerification(guild.id, interaction.user.id);
  if (!verification) return reply(interaction, "You do not currently have a Roblox account linked here.");

  const { verifiedRoleId } = getConfig(guild.id);
  const role = verifiedRoleId ? guild.roles.cache.get(verifiedRoleId) : null;
  if (role) {
    const member = await guild.members.fetch(interaction.user.id).catch(() => null);
    if (member?.roles.cache.has(role.id)) await member.roles.remove(role, "Roblox account unlinked by member").catch(() => null);
  }

  await sendLog(guild, "Roblox unlinked", `${interaction.user} removed their Roblox link for **${verification.username}**.`);
  return reply(interaction, `Your Roblox link for **${verification.username}** was removed.`);
}

async function handleConfig(interaction) {
  const action = interaction.options.getSubcommand();
  const guild = interaction.guild;

  if (action === "verified-role") {
    const role = interaction.options.getRole("role", true);
    await requireConfigurableRole(guild, role);
    setConfig(guild.id, "verifiedRoleId", role.id);
    return reply(interaction, `Roblox-verified members will now receive ${role}.`);
  }

  if (action === "log-channel") {
    const channel = interaction.options.getChannel("channel", true);
    if (!channel.isTextBased()) throw new Error("Choose a text channel for logs.");
    setConfig(guild.id, "logChannelId", channel.id);
    return reply(interaction, `Moderation logs will now be sent to ${channel}.`);
  }

  const config = getConfig(guild.id);
  const verifiedRole = config.verifiedRoleId ? `<@&${config.verifiedRoleId}>` : "Not set";
  const logChannel = config.logChannelId ? `<#${config.logChannelId}>` : "Not set";
  return reply(interaction, `**Bot settings**\nVerified role: ${verifiedRole}\nMod-log channel: ${logChannel}`);
}

async function handleModeration(interaction) {
  const guild = interaction.guild;
  const command = interaction.commandName;

  if (command === "warn") {
    const user = interaction.options.getUser("member", true);
    const reason = interaction.options.getString("reason", true);
    await getTargetMember(interaction, user);
    const warnings = addWarning(guild.id, user.id, {
      id: crypto.randomUUID(),
      reason,
      moderatorId: interaction.user.id,
      createdAt: new Date().toISOString(),
    });
    await sendLog(guild, "Member warned", `${user} was warned by ${interaction.user}.\n**Reason:** ${reason}`);
    return reply(interaction, `⚠️ Warned ${user}. They now have **${warnings.length}** saved warning(s).`);
  }

  if (command === "warnings") {
    const user = interaction.options.getUser("member", true);
    const warnings = getWarnings(guild.id, user.id);
    if (!warnings.length) return reply(interaction, `${user} has no saved warnings.`);
    const list = warnings.slice(-10).reverse().map((warning, index) => {
      return `**${warnings.length - index}.** ${warning.reason} — <@${warning.moderatorId}> (${timestamp(warning.createdAt)})`;
    }).join("\n");
    return reply(interaction, `**Warnings for ${user.tag} (${warnings.length})**\n${list}`);
  }

  if (command === "clearwarnings") {
    const user = interaction.options.getUser("member", true);
    const count = clearWarnings(guild.id, user.id);
    await sendLog(guild, "Warnings cleared", `${interaction.user} cleared **${count}** warning(s) for ${user}.`);
    return reply(interaction, `Cleared **${count}** warning(s) for ${user}.`);
  }

  if (command === "timeout" || command === "untimeout" || command === "kick" || command === "ban") {
    const user = interaction.options.getUser("member", true);
    const member = await getTargetMember(interaction, user);
    const reason = interaction.options.getString("reason") || "No reason provided";

    if (command === "timeout") {
      if (!member.moderatable) throw new Error("I cannot timeout that member. Check my role and Moderation permission.");
      const minutes = interaction.options.getInteger("minutes", true);
      await member.timeout(minutes * 60_000, reason);
      await sendLog(guild, "Member timed out", `${user} was timed out by ${interaction.user} for **${minutes} minute(s)**.\n**Reason:** ${reason}`);
      return reply(interaction, `Timed out ${user} for **${minutes} minute(s)**.`);
    }

    if (command === "untimeout") {
      if (!member.moderatable) throw new Error("I cannot change that member's timeout. Check my role and Moderation permission.");
      await member.timeout(null, reason);
      await sendLog(guild, "Timeout removed", `${interaction.user} removed ${user}'s timeout.\n**Reason:** ${reason}`);
      return reply(interaction, `Removed ${user}'s timeout.`);
    }

    if (command === "kick") {
      if (!member.kickable) throw new Error("I cannot kick that member. Check my role and Kick Members permission.");
      await member.kick(reason);
      await sendLog(guild, "Member kicked", `${user} was kicked by ${interaction.user}.\n**Reason:** ${reason}`);
      return reply(interaction, `Kicked ${user}.`);
    }

    if (!member.bannable) throw new Error("I cannot ban that member. Check my role and Ban Members permission.");
    await member.ban({ reason });
    await sendLog(guild, "Member banned", `${user} was banned by ${interaction.user}.\n**Reason:** ${reason}`);
    return reply(interaction, `Banned ${user}.`);
  }

  const channel = interaction.channel;
  if (!channel?.isTextBased()) throw new Error("Use this command in a server text channel.");

  if (command === "purge") {
    if (typeof channel.bulkDelete !== "function") throw new Error("This channel does not support bulk deletion.");
    const amount = interaction.options.getInteger("amount", true);
    const deleted = await channel.bulkDelete(amount, true);
    await sendLog(guild, "Messages purged", `${interaction.user} deleted **${deleted.size}** message(s) in ${channel}.`);
    return reply(interaction, `Deleted **${deleted.size}** message(s). Messages older than 14 days cannot be bulk deleted by Discord.`);
  }

  if (command === "lock" || command === "unlock") {
    if (!channel.permissionOverwrites) throw new Error("This channel cannot be locked by the bot.");
    const locked = command === "lock";
    const reason = interaction.options.getString("reason") || "No reason provided";
    await channel.permissionOverwrites.edit(guild.roles.everyone, { SendMessages: locked }, { reason });
    await sendLog(guild, locked ? "Channel locked" : "Channel unlocked", `${interaction.user} ${locked ? "locked" : "unlocked"} ${channel}.\n**Reason:** ${reason}`);
    return reply(interaction, `${locked ? "🔒 Locked" : "🔓 Unlocked"} ${channel}.`);
  }

  if (command === "slowmode") {
    if (typeof channel.setRateLimitPerUser !== "function") throw new Error("This channel does not support slowmode.");
    const seconds = interaction.options.getInteger("seconds", true);
    await channel.setRateLimitPerUser(seconds, `Changed by ${interaction.user.tag}`);
    await sendLog(guild, "Slowmode changed", `${interaction.user} set ${channel} slowmode to **${seconds} second(s)**.`);
    return reply(interaction, seconds ? `Slowmode is now **${seconds} second(s)**.` : "Slowmode is now off.");
  }
}

client.once(Events.ClientReady, async (readyClient) => {
  console.log(`Logged in as ${readyClient.user.tag}.`);
  try {
    await syncCommands();
  } catch (error) {
    console.error("Could not sync slash commands:", error);
  }
});

client.on(Events.InteractionCreate, async (interaction) => {
  if (!interaction.isChatInputCommand()) return;
  if (!interaction.inGuild()) {
    return interaction.reply({ content: "Use this bot inside a Discord server.", ephemeral: true });
  }

  await interaction.deferReply({ ephemeral: true });

  try {
    if (interaction.commandName === "ping") return reply(interaction, `Pong! ${client.ws.ping}ms`);

    if (interaction.commandName === "verify") return handleVerification(interaction);

    if (interaction.commandName === "roblox") {
      const profile = await findRobloxUser(interaction.options.getString("username", true));
      return reply(interaction, `**${profile.displayName}** (@${profile.username})\nRoblox ID: \`${profile.id}\`\nProfile: <${robloxProfileUrl(profile.id)}>`);
    }

    if (interaction.commandName === "whois") {
      const user = interaction.options.getUser("member", true);
      const verification = getVerification(interaction.guild.id, user.id);
      if (!verification) return reply(interaction, `${user} has not linked a Roblox account in this server.`);
      return reply(interaction, `${user} is linked to **${verification.displayName}** (@${verification.username})\n<${robloxProfileUrl(verification.id)}>\nVerified ${timestamp(verification.verifiedAt)}`);
    }

    if (interaction.commandName === "config") return handleConfig(interaction);

    return handleModeration(interaction);
  } catch (error) {
    console.error(`Error handling /${interaction.commandName}:`, error);
    return reply(interaction, `❌ ${error instanceof Error ? error.message : "Something went wrong. Check my permissions and try again."}`);
  }
});

client.login(token);
