const ROBLOX_API = "https://users.roblox.com/v1";

async function robloxFetch(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "User-Agent": "discord-roblox-management-bot",
      ...(options.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new Error(`Roblox API returned ${response.status}.`);
  }

  return response.json();
}

export async function findRobloxUser(username) {
  const cleanUsername = username.trim();
  if (!/^[A-Za-z0-9_]{3,20}$/.test(cleanUsername)) {
    throw new Error("That does not look like a valid Roblox username.");
  }

  const result = await robloxFetch(`${ROBLOX_API}/usernames/users`, {
    method: "POST",
    body: JSON.stringify({ usernames: [cleanUsername], excludeBannedUsers: false }),
  });

  const user = result.data?.[0];
  if (!user?.id) {
    throw new Error("I could not find that Roblox username.");
  }

  return {
    id: String(user.id),
    username: user.name,
    displayName: user.displayName || user.name,
  };
}

export async function getRobloxProfile(userId) {
  const profile = await robloxFetch(`${ROBLOX_API}/users/${encodeURIComponent(userId)}`);
  return {
    id: String(profile.id),
    username: profile.name,
    displayName: profile.displayName || profile.name,
    description: profile.description || "",
    created: profile.created || null,
    isBanned: Boolean(profile.isBanned),
  };
}

export function robloxProfileUrl(userId) {
  return `https://www.roblox.com/users/${encodeURIComponent(userId)}/profile`;
}
