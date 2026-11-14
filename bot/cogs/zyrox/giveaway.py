# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   UND — All In One                                               ║
# ║                                                                  ║
# ║                                                                  ║
# ║   © 2026 KURAPIKA — All Rights Reserved                          ║
# ║   Built & owned by Kurapika                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import discord
from utils.emoji import ZTADA
from discord.ext import commands


class _giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    """Giveaway commands"""
  
    def help_custom(self):
		      emoji = f'{ZTADA} '
		      label = "Giveaway Commands"
		      description = "Show you Commands of Giveaway"
		      return emoji, label, description

    @commands.group()
    async def __Giveaway__(self, ctx: commands.Context):
        """`gstart`, `gend`, `greroll` , `glist`"""