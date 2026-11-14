# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   UND — All In One                                               ║
# ║                                                                  ║
# ║                                                                  ║
# ║   © 2026 KURAPIKA — All Rights Reserved                          ║
# ║   Built & owned by Kurapika                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

"""`/help` — the very same view as `!help` (ZyroX CV2 layout).

Kept in one place (`utils.help.build_help_view`) so both entry points always
show the same custom emojis, categories and buttons.
"""

import discord
from discord import app_commands
from discord.ext import commands

from utils.Tools import getConfig
from utils.help import build_help_view


class SlashHelp(commands.Cog, name="slashhelp"):
    """`/help` — the complete command directory."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show every UND command, grouped by category")
    @app_commands.describe(category="Optional category name to jump straight to it")
    async def help_cmd(self, interaction: discord.Interaction, category: str | None = None):
        prefix = ">"
        if interaction.guild:
            try:
                prefix = (await getConfig(interaction.guild.id))["prefix"]
            except Exception:
                prefix = ">"

        view = await build_help_view(self.bot, interaction.user, prefix, category)
        await interaction.response.send_message(view=view)


async def setup(bot):
    await bot.add_cog(SlashHelp(bot))
