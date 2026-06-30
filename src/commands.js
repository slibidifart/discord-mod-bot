import { ChannelType, PermissionFlagsBits, SlashCommandBuilder } from "discord.js";

const staff = PermissionFlagsBits.ModerateMembers;
const admin = PermissionFlagsBits.ManageGuild;

export const commands = [
  new SlashCommandBuilder()
    .setName("verify")
    .setDescription("Link your Discord account to a Roblox profile")
    .addSubcommand((sub) =>
      sub
        .setName("start")
        .setDescription("Start Roblox verification")
        .addStringOption((option) =>
          option.setName("username").setDescription("Your exact Roblox username").setRequired(true),
        ),
    )
    .addSubcommand((sub) => sub.setName("check").setDescription("Finish Roblox verification"))
    .addSubcommand((sub) => sub.setName("unlink").setDescription("Remove your saved Roblox link")),

  new SlashCommandBuilder()
    .setName("roblox")
    .setDescription("Look up a Roblox profile")
    .addStringOption((option) =>
      option.setName("username").setDescription("Roblox username").setRequired(true),
    ),

  new SlashCommandBuilder()
    .setName("whois")
    .setDescription("Show a member's linked Roblox account")
    .addUserOption((option) =>
      option.setName("member").setDescription("Discord member").setRequired(true),
    ),

  new SlashCommandBuilder()
    .setName("config")
    .setDescription("Configure the bot for this server")
    .setDefaultMemberPermissions(admin)
    .addSubcommand((sub) =>
      sub
        .setName("verified-role")
        .setDescription("Choose the role granted after Roblox verification")
        .addRoleOption((option) =>
          option.setName("role").setDescription("Role to grant").setRequired(true),
        ),
    )
    .addSubcommand((sub) =>
      sub
        .setName("log-channel")
        .setDescription("Choose where moderation actions are logged")
        .addChannelOption((option) =>
          option
            .setName("channel")
            .setDescription("Text channel for logs")
            .addChannelTypes(ChannelType.GuildText)
            .setRequired(true),
        ),
    )
    .addSubcommand((sub) => sub.setName("view").setDescription("View this server's bot settings")),

  new SlashCommandBuilder()
    .setName("warn")
    .setDescription("Warn a member and save the warning")
    .setDefaultMemberPermissions(staff)
    .addUserOption((option) => option.setName("member").setDescription("Member to warn").setRequired(true))
    .addStringOption((option) => option.setName("reason").setDescription("Why they are being warned").setRequired(true)),

  new SlashCommandBuilder()
    .setName("warnings")
    .setDescription("View a member's saved warnings")
    .setDefaultMemberPermissions(staff)
    .addUserOption((option) => option.setName("member").setDescription("Member to check").setRequired(true)),

  new SlashCommandBuilder()
    .setName("clearwarnings")
    .setDescription("Delete all saved warnings for a member")
    .setDefaultMemberPermissions(staff)
    .addUserOption((option) => option.setName("member").setDescription("Member to clear").setRequired(true)),

  new SlashCommandBuilder()
    .setName("timeout")
    .setDescription("Temporarily timeout a member")
    .setDefaultMemberPermissions(staff)
    .addUserOption((option) => option.setName("member").setDescription("Member to timeout").setRequired(true))
    .addIntegerOption((option) =>
      option.setName("minutes").setDescription("Length in minutes, up to 28 days").setMinValue(1).setMaxValue(40320).setRequired(true),
    )
    .addStringOption((option) => option.setName("reason").setDescription("Reason for the timeout").setRequired(true)),

  new SlashCommandBuilder()
    .setName("untimeout")
    .setDescription("Remove a member's timeout")
    .setDefaultMemberPermissions(staff)
    .addUserOption((option) => option.setName("member").setDescription("Member to untimeout").setRequired(true))
    .addStringOption((option) => option.setName("reason").setDescription("Reason").setRequired(false)),

  new SlashCommandBuilder()
    .setName("kick")
    .setDescription("Kick a member")
    .setDefaultMemberPermissions(PermissionFlagsBits.KickMembers)
    .addUserOption((option) => option.setName("member").setDescription("Member to kick").setRequired(true))
    .addStringOption((option) => option.setName("reason").setDescription("Reason").setRequired(true)),

  new SlashCommandBuilder()
    .setName("ban")
    .setDescription("Ban a member")
    .setDefaultMemberPermissions(PermissionFlagsBits.BanMembers)
    .addUserOption((option) => option.setName("member").setDescription("Member to ban").setRequired(true))
    .addStringOption((option) => option.setName("reason").setDescription("Reason").setRequired(true)),

  new SlashCommandBuilder()
    .setName("purge")
    .setDescription("Delete recent messages from this channel")
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages)
    .addIntegerOption((option) =>
      option.setName("amount").setDescription("Messages to delete, 1–100").setMinValue(1).setMaxValue(100).setRequired(true),
    ),

  new SlashCommandBuilder()
    .setName("lock")
    .setDescription("Stop @everyone from sending messages in this channel")
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageChannels)
    .addStringOption((option) => option.setName("reason").setDescription("Reason").setRequired(false)),

  new SlashCommandBuilder()
    .setName("unlock")
    .setDescription("Let @everyone send messages in this channel again")
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageChannels)
    .addStringOption((option) => option.setName("reason").setDescription("Reason").setRequired(false)),

  new SlashCommandBuilder()
    .setName("slowmode")
    .setDescription("Set this channel's slowmode")
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageChannels)
    .addIntegerOption((option) =>
      option.setName("seconds").setDescription("0 to disable, maximum 6 hours").setMinValue(0).setMaxValue(21600).setRequired(true),
    ),

  new SlashCommandBuilder().setName("ping").setDescription("Check whether the bot is online"),
].map((command) => command.toJSON());
