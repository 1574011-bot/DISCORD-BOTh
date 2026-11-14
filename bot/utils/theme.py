# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   UND — All In One                                               ║
# ║                                                                  ║
# ║   © 2026 KURAPIKA — All Rights Reserved                          ║
# ║   Built & owned by Kurapika                                      ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

"""UND theme — one red colour for every embed in the bot."""

import discord

THEME_COLOR = 0xFF0000

_applied = False


def apply_theme() -> None:
    """Make every embed red, including the ones created without a colour."""
    global _applied
    if _applied:
        return

    original_init = discord.Embed.__init__

    def red_init(self, *args, **kwargs):
        if kwargs.get("color") is None and kwargs.get("colour") is None:
            kwargs["color"] = THEME_COLOR
        original_init(self, *args, **kwargs)

    discord.Embed.__init__ = red_init
    _applied = True
