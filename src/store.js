import fs from "node:fs";
import path from "node:path";

const dataDirectory = path.join(process.cwd(), "data");
const dataFile = path.join(dataDirectory, "bot-data.json");

let data = { guilds: {} };

export function initializeStore() {
  fs.mkdirSync(dataDirectory, { recursive: true });

  if (!fs.existsSync(dataFile)) {
    fs.writeFileSync(dataFile, JSON.stringify(data, null, 2));
    return;
  }

  try {
    const parsed = JSON.parse(fs.readFileSync(dataFile, "utf8"));
    data = parsed && typeof parsed === "object" ? parsed : { guilds: {} };
    data.guilds ??= {};
  } catch {
    const backup = `${dataFile}.broken-${Date.now()}`;
    fs.renameSync(dataFile, backup);
    fs.writeFileSync(dataFile, JSON.stringify(data, null, 2));
    console.warn(`Saved unreadable bot data as ${path.basename(backup)} and started fresh.`);
  }
}

function save() {
  const temporaryFile = `${dataFile}.tmp`;
  fs.writeFileSync(temporaryFile, JSON.stringify(data, null, 2));
  fs.renameSync(temporaryFile, dataFile);
}

function guildData(guildId) {
  data.guilds[guildId] ??= {
    config: {
      verifiedRoleId: null,
      logChannelId: null,
    },
    pending: {},
    verifications: {},
    warnings: {},
  };

  const guild = data.guilds[guildId];
  guild.config ??= { verifiedRoleId: null, logChannelId: null };
  guild.pending ??= {};
  guild.verifications ??= {};
  guild.warnings ??= {};
  return guild;
}

export function getConfig(guildId) {
  return guildData(guildId).config;
}

export function setConfig(guildId, key, value) {
  const guild = guildData(guildId);
  guild.config[key] = value;
  save();
  return guild.config;
}

export function createPendingVerification(guildId, discordId, record) {
  const guild = guildData(guildId);
  guild.pending[discordId] = record;
  save();
}

export function getPendingVerification(guildId, discordId) {
  return guildData(guildId).pending[discordId] ?? null;
}

export function deletePendingVerification(guildId, discordId) {
  const guild = guildData(guildId);
  delete guild.pending[discordId];
  save();
}

export function saveVerification(guildId, discordId, verification) {
  const guild = guildData(guildId);
  guild.verifications[discordId] = verification;
  delete guild.pending[discordId];
  save();
}

export function getVerification(guildId, discordId) {
  return guildData(guildId).verifications[discordId] ?? null;
}

export function removeVerification(guildId, discordId) {
  const guild = guildData(guildId);
  const previous = guild.verifications[discordId] ?? null;
  delete guild.verifications[discordId];
  delete guild.pending[discordId];
  save();
  return previous;
}

export function addWarning(guildId, discordId, warning) {
  const guild = guildData(guildId);
  guild.warnings[discordId] ??= [];
  guild.warnings[discordId].push(warning);
  save();
  return guild.warnings[discordId];
}

export function getWarnings(guildId, discordId) {
  return guildData(guildId).warnings[discordId] ?? [];
}

export function clearWarnings(guildId, discordId) {
  const guild = guildData(guildId);
  const count = guild.warnings[discordId]?.length ?? 0;
  delete guild.warnings[discordId];
  save();
  return count;
}
