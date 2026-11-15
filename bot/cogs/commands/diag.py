# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   UND — All In One                                               ║
# ║                                                                  ║
# ║                                                                  ║
# ║   © 2026 KURAPIKA — All Rights Reserved                          ║
# ║   Built & owned by Kurapika                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

"""Owner diagnostics: which build is running, where data is stored, last errors."""

from __future__ import annotations

import os
import pathlib

import discord
from discord.ext import commands

from utils import storage

ERROR_LOG = pathlib.Path("logs/commands.log")


def _short_commit() -> str:
    for name in ("RAILWAY_GIT_COMMIT_SHA", "GIT_COMMIT", "SOURCE_VERSION", "COMMIT_SHA"):
        value = (os.getenv(name) or "").strip()
        if value:
            return value[:7]
    return "local"


def _dir_state(name: str) -> str:
    path = pathlib.Path(name)
    if path.is_symlink():
        try:
            target = os.readlink(path)
        except OSError:
            target = "?"
        return f"`{name}` → `{target}`"
    if path.is_dir() and os.path.ismount(path):
        return f"`{name}` (own mount — persistent)"
    return f"`{name}` (local, not persisted)"


def _log_tail(limit: int = 1200) -> str:
    if not ERROR_LOG.is_file():
        return "no error log yet"
    try:
        with ERROR_LOG.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - limit))
            return handle.read().decode("utf-8", "replace")
    except OSError as exc:
        return f"could not read log: {exc}"


class Diagnostics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="diag",
        description="Owner only — show build, data folder and the latest errors.",
    )
    async def diag(self, ctx: commands.Context):
        if not await self.bot.is_owner(ctx.author):
            return await ctx.reply(
                "This command is owner only.", mention_author=False, delete_after=10
            )

        db_files = sorted(pathlib.Path("db").glob("*.db")) if pathlib.Path("db").is_dir() else []
        total_bytes = sum(path.stat().st_size for path in db_files if path.is_file())
        storage_line = (
            f"`{storage.PERSIST_ROOT}` ✅"
            if storage.PERSIST_ROOT
            else "**not linked** ❌ (data resets on redeploy)"
        )
        build = (
            f"commit `{_short_commit()}`\n"
            f"branch `{os.getenv('RAILWAY_GIT_BRANCH', '-')}`\n"
            f"deployment `{(os.getenv('RAILWAY_DEPLOYMENT_ID') or '-')[:12]}`"
        )
        folders = "\n".join(_dir_state(name) for name in storage.RUNTIME_DIRS)

        embed = discord.Embed(title="🩺 UND diagnostics", color=0xFF0000)
        embed.add_field(name="Build", value=build, inline=False)
        embed.add_field(name="Persistent storage", value=storage_line, inline=False)
        embed.add_field(name="Folders", value=folders[:1024], inline=False)
        embed.add_field(
            name="Database",
            value=f"`{len(db_files)}` file(s) • `{total_bytes / 1024:.0f} KB`",
            inline=False,
        )
        embed.add_field(name="Last errors", value=f"```{_log_tail()[-1000:]}```", inline=False)
        embed.set_footer(text="compare this commit with the one you pushed")
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot):
    await bot.add_cog(Diagnostics(bot))
