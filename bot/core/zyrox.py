# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   UND — All In One                                               ║
# ║                                                                  ║
# ║                                                                  ║
# ║   © 2026 KURAPIKA — All Rights Reserved                          ║
# ║   Built & owned by Kurapika                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

from __future__ import annotations
from discord.ext import commands, tasks
import discord
import aiohttp
import json
import jishaku
import asyncio
import typing
from typing import List
import aiosqlite
from utils.config import OWNER_IDS, BotName
# NOTE: getConfig is imported lazily inside the methods below. Importing it here
# created a circular import (utils -> utils.Tools -> core -> core.zyrox -> utils).
from .Context import Context
from colorama import Fore, Style, init
import importlib
import inspect
import traceback

init(autoreset=True)

# Corrected the extensions list
extensions: List[str] = [
    "cogs"
]

class zyrox(commands.AutoShardedBot):
    def __init__(self, *arg, **kwargs):
        intents = discord.Intents.all()
        intents.presences = True
        intents.members = True
        super().__init__(command_prefix=self.get_prefix,
                         case_insensitive=True,
                         intents=intents,
                         # The status is already set to Do Not Disturb here
                         status=discord.Status.do_not_disturb,
                         strip_after_prefix=True,
                         owner_ids=OWNER_IDS,
                         allowed_mentions=discord.AllowedMentions(
                             everyone=False, replied_user=False, roles=False),
                         sync_commands_debug=True,
                         sync_commands=True,
                         shard_count=1)
        self.status_index = 0
        self.status_list = []

    async def setup_hook(self):
        # Without this every slash-command error is silent and Discord only
        # shows "The application did not respond".
        self.tree.on_error = self.on_app_command_error
        await self.load_extensions()
        self.status_task.start()

    # ── error handling ────────────────────────────────────────────────────────

    async def on_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """Answer /app commands instead of failing silently."""
        original = getattr(error, "original", error)
        traceback.print_exception(type(original), original, original.__traceback__)

        ac = discord.app_commands
        if isinstance(original, ac.CommandOnCooldown):
            message = f"⏳ Slow down — try again in **{original.retry_after:.1f}s**."
        elif isinstance(original, ac.MissingPermissions):
            perms = ", ".join(f"`{p}`" for p in original.missing_permissions)
            message = f"🔒 You need: {perms}"
        elif isinstance(original, ac.BotMissingPermissions):
            perms = ", ".join(f"`{p}`" for p in original.missing_permissions)
            message = f"🤖 I need these permissions: {perms}"
        elif isinstance(original, ac.CheckFailure):
            message = f"🔒 {original}" if str(original) else "🔒 You can't use this command here."
        elif isinstance(original, ac.TransformerError):
            message = f"❌ Bad argument for `{original.param}`: {original}"
        else:
            message = f"❌ Something went wrong (`{type(original).__name__}`). It was logged — try again in a moment."

        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except discord.HTTPException:
            pass

    async def on_command_error(self, ctx: Context, error: Exception) -> None:
        """Answer prefixed commands instead of dying silently."""
        if isinstance(error, (commands.CommandNotFound, commands.DisabledCommand)):
            return

        original = getattr(error, "original", error)
        traceback.print_exception(type(original), original, original.__traceback__)

        if isinstance(original, commands.CommandOnCooldown):
            text = f"⏳ Slow down — try again in **{original.retry_after:.1f}s**."
        elif isinstance(original, commands.MissingPermissions):
            text = "🔒 You need: " + ", ".join(f"`{p}`" for p in original.missing_permissions)
        elif isinstance(original, commands.BotMissingPermissions):
            text = "🤖 I need: " + ", ".join(f"`{p}`" for p in original.missing_permissions)
        elif isinstance(original, commands.MissingRequiredArgument):
            text = f"❌ Missing `{original.param.name}`. Usage: `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`"
        elif isinstance(original, (commands.BadArgument, commands.BadUnionArgument)):
            text = f"❌ {original}"
        elif isinstance(original, commands.CheckFailure):
            text = f"🔒 {original}" if str(original) else "🔒 You can't use this command here."
        else:
            text = f"❌ Something went wrong (`{type(original).__name__}`). It was logged — try again in a moment."

        try:
            await ctx.send(embed=discord.Embed(description=text, color=0xFF0000))
        except discord.HTTPException:
            pass

    async def load_extensions(self):
        for extension in extensions:
            try:
                await self.load_extension(extension)
                print(Fore.GREEN + Style.BRIGHT + f"Loaded extension: {extension}")
            except Exception as e:
                print(f"{Fore.RED}{Style.BRIGHT}Failed to load extension {extension}. {e}")
        print(Fore.GREEN + Style.BRIGHT + "*" * 20)

    @tasks.loop(seconds=30)
    async def status_task(self):
        await self.wait_until_ready()
        if not self.guilds:
            return

        guild = self.guilds[0]  # Use first available guild for prefix
        try:
            from utils import getConfig
            config = await getConfig(guild.id)
            prefix = config.get("prefix", ">")
        except:
            prefix = ">"

        user_count = sum(g.member_count or 0 for g in self.guilds)
        guild_count = len(self.guilds)

        self.status_list = [
            (discord.ActivityType.playing, f"{prefix}help | Security in your Server"),
            (discord.ActivityType.watching, f"{user_count} users"),
            (discord.ActivityType.watching, f"{guild_count} servers"),
            (discord.ActivityType.listening, "Killing Nukers"),
            (discord.ActivityType.playing, f"Protector {BotName}"),
        ]

        current = self.status_list[self.status_index % len(self.status_list)]
        # This task only changes the activity, not the online status (dnd, idle, etc.)
        await self.change_presence(activity=discord.Activity(type=current[0], name=current[1]))
        self.status_index += 1

    async def send_raw(self, channel_id: int, content: str, **kwargs) -> typing.Optional[discord.Message]:
        await self.http.send_message(channel_id, content, **kwargs)

    async def invoke_help_command(self, ctx: Context) -> None:
        return await ctx.send_help(ctx.command)

    async def fetch_message_by_channel(self, channel: discord.TextChannel, messageID: int) -> typing.Optional[discord.Message]:
        async for msg in channel.history(limit=1, before=discord.Object(messageID + 1), after=discord.Object(messageID - 1)):
            return msg

    async def get_prefix(self, message: discord.Message):
        if message.guild:
            guild_id = message.guild.id
            async with aiosqlite.connect('db/np.db') as db:
                async with db.execute("SELECT id FROM np WHERE id = ?", (message.author.id,)) as cursor:
                    row = await cursor.fetchone()
            from utils import getConfig
            data = await getConfig(guild_id)
            prefix = data["prefix"]
            # Always accept "!" next to the guild prefix so both styles work.
            extra = ["!"] if prefix != "!" else []
            if row:
                return commands.when_mentioned_or(prefix, *extra, '')(self, message)
            else:
                return commands.when_mentioned_or(prefix, *extra)(self, message)
        else:
            async with aiosqlite.connect('db/np.db') as db:
                async with db.execute("SELECT id FROM np WHERE id = ?", (message.author.id,)) as cursor:
                    row = await cursor.fetchone()
            if row:
                return commands.when_mentioned_or('?', '!', '')(self, message)
            else:
                return commands.when_mentioned_or('?', '!')(self, message)

    async def on_message_edit(self, before, after):
        ctx: Context = await self.get_context(after, cls=Context)
        if before.content != after.content:
            if after.guild is None or after.author.bot:
                return
            if ctx.command is None:
                return
            if type(ctx.channel) == "public_thread":
                return
            await self.invoke(ctx)

def setup_bot():
    intents = discord.Intents.all()
    bot = zyrox(intents=intents)
    return bot
