# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   UND — All In One                                               ║
# ║                                                                  ║
# ║                                                                  ║
# ║   © 2026 KURAPIKA — All Rights Reserved                          ║
# ║   Built & owned by Kurapika                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import discord
from utils.Tools import *
from utils.cv2 import build_container
from utils.emoji import REWIND, PREVIOUS, NEXT, FORWARD, DELETE, HOME, safe_emoji
from discord.ui import LayoutView, TextDisplay, Separator, ActionRow


class Dropdown(discord.ui.Select):

    def __init__(self, ctx, options, placeholder="Choose a Category for Help"):
        super().__init__(placeholder=placeholder,
                         min_values=1,
                         max_values=1,
                         options=options)
        self.invoker = ctx.author

    async def callback(self, interaction: discord.Interaction):
        if self.invoker == interaction.user:
            index = self.view.find_index_from_select(self.values[0])
            if not index:
                index = 0
            await self.view.set_page(index, interaction)
        else:
            await interaction.response.send_message(
                "You must run this command to interact with it.", ephemeral=True)


class View(LayoutView):

    def __init__(self, mapping: dict, ctx, homeembed, ui: int):
        super().__init__(timeout=None)
        self.mapping = mapping
        self.ctx = ctx
        self.index = 0
        self.current_page = 0
        self.ui = ui

        self.options, self.pages, self.total_pages = self.gen_pages(homeembed)
        self.pages[0]['footer'] = f"• Help page 1/{self.total_pages} | Requested by: {self.ctx.author.display_name}"
        self._rebuild()

    def _rebuild(self):
        self.clear_items()
        page = self.pages[self.index]
        page['footer'] = f"• Help page {self.index + 1}/{self.total_pages} | Requested by: {self.ctx.author.display_name}"

        # Build container items (text content)
        items = []
        if page.get('title'):
            items.append(TextDisplay(f"**{page['title']}**"))
        if page.get('description'):
            if items:
                items.append(Separator(visible=True))
            items.append(TextDisplay(page['description']))
        for name, value in page.get('fields', []):
            items.append(Separator(visible=True))
            items.append(TextDisplay(f"**{name}**\n{value}"))

        # Build buttons
        is_first = self.index == 0
        is_last = self.index >= len(self.pages) - 1

        homeB = discord.ui.Button(label="", emoji=REWIND, style=discord.ButtonStyle.secondary, disabled=is_first)
        backB = discord.ui.Button(label="", emoji=PREVIOUS, style=discord.ButtonStyle.secondary, disabled=is_first)
        quitB = discord.ui.Button(label="", emoji=DELETE, style=discord.ButtonStyle.danger)
        nextB = discord.ui.Button(label="", emoji=NEXT, style=discord.ButtonStyle.secondary, disabled=is_last)
        lastB = discord.ui.Button(label="", emoji=FORWARD, style=discord.ButtonStyle.secondary, disabled=is_last)

        homeB.callback = self._home_cb
        backB.callback = self._back_cb
        quitB.callback = self._quit_cb
        nextB.callback = self._next_cb
        lastB.callback = self._last_cb

        # Add buttons ActionRow inside the container
        items.append(ActionRow(homeB, backB, quitB, nextB, lastB))

        # Add dropdowns inside the container
        if self.ui == 0:
            items.append(ActionRow(Dropdown(ctx=self.ctx, options=self.options)))
        elif self.ui == 2:
            mid = len(self.options) // 2
            o1, o2 = self.options[:mid], self.options[mid:]
            if o1:
                items.append(ActionRow(Dropdown(ctx=self.ctx, options=o1, placeholder="Main Commands")))
            if o2:
                items.append(ActionRow(Dropdown(ctx=self.ctx, options=o2, placeholder="Extra Commands")))
        elif self.ui == 3:
            items.append(ActionRow(Dropdown(ctx=self.ctx, options=self.options)))

        # Add footer after controls
        if page.get('footer'):
            items.append(Separator(visible=True))
            items.append(TextDisplay(f"*{page['footer']}*"))

        # Build the single container with everything inside
        self.add_item(build_container(*items))

    async def _check(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You must run this command to interact with it.", ephemeral=True)
            return False
        return True

    async def _home_cb(self, interaction):
        if await self._check(interaction):
            await self.set_page(0, interaction)

    async def _back_cb(self, interaction):
        if await self._check(interaction):
            await self.set_page(self.index - 1 if self.index > 0 else len(self.pages) - 1, interaction)

    async def _quit_cb(self, interaction):
        if await self._check(interaction):
            await interaction.response.defer()
            await interaction.delete_original_response()

    async def _next_cb(self, interaction):
        if await self._check(interaction):
            await self.set_page(self.index + 1 if self.index < len(self.pages) - 1 else 0, interaction)

    async def _last_cb(self, interaction):
        if await self._check(interaction):
            await self.set_page(len(self.pages) - 1, interaction)

    def find_index_from_select(self, value):
        i = 0
        used_labels = set()
        for cog in self.get_cogs():
            if cog.__class__.__name__ == "Roleplay":
                continue
            if "help_custom" in dir(cog):
                _, label, _ = cog.help_custom()
                original_label = label
                counter = 1
                while label in used_labels:
                    label = f"{original_label} {counter}"
                    counter += 1
                used_labels.add(label)
                if label == value or value.startswith(original_label + " "):
                    return i + 1
                i += 1
        return 0

    def get_cogs(self):
        return list(self.mapping.keys())

    def gen_pages(self, homeembed):
        options, pages = [], []
        total_pages = 0
        used_labels = set()

        options.append(discord.SelectOption(label="Home", emoji=safe_emoji(HOME, "🏠"), description=""))

        # Convert homeembed (CV2Embed) to page data
        if hasattr(homeembed, '_title'):
            home_page = {
                'title': homeembed._title or '',
                'description': homeembed._description or '',
                'fields': list(homeembed._fields) if hasattr(homeembed, '_fields') else [],
                'footer': None
            }
        else:
            home_page = {
                'title': getattr(homeembed, 'title', '') or '',
                'description': getattr(homeembed, 'description', '') or '',
                'fields': [(f.name, f.value) for f in homeembed.fields] if hasattr(homeembed, 'fields') and homeembed.fields else [],
                'footer': homeembed.footer.text if hasattr(homeembed, 'footer') and homeembed.footer else None
            }

        pages.append(home_page)
        total_pages += 1
        used_labels.add("Home")

        for cog in self.get_cogs():
            if cog.__class__.__name__ == "Roleplay":
                continue
            if "help_custom" in dir(cog):
                emoji, label, description = cog.help_custom()
                # Discord rejects stray spaces / foreign custom emoji here with
                # "Invalid emoji" (HTTP 400), which used to break the whole help.
                emoji = safe_emoji(emoji)
                label = str(label or "Commands")[:100]
                description = str(description or "")[:100]
                original_label = label
                counter = 1
                while label in used_labels:
                    label = f"{original_label} {counter}"[:100]
                    counter += 1
                used_labels.add(label)
                options.append(discord.SelectOption(label=label, emoji=emoji, description=description))

                fields = []
                for command in cog.get_commands():
                    params = ""
                    for param in command.clean_params:
                        if param not in ["self", "ctx"]:
                            params += f" <{param}>"
                    help_text = command.help or "No description available"
                    if len(help_text) > 1020:
                        help_text = help_text[:1017] + "..."
                    fields.append((f"{command.name}{params}", f"{help_text}\n•"))

                pages.append({
                    'title': f"{emoji} {original_label}",
                    'description': '',
                    'fields': fields,
                    'footer': None
                })
                total_pages += 1

        return options, pages, total_pages

    async def set_page(self, page, interaction):
        self.index = page
        self.current_page = page
        self._rebuild()
        await interaction.response.edit_message(view=self)

# ============================================================================
# SHARED HELP VIEW (used by both `!help` and `/help`)
# ============================================================================

class _HelpCtx:
    """Minimal Context stand-in so the same View serves slash and prefix."""

    def __init__(self, author, prefix, bot):
        self.author = author
        self.prefix = prefix
        self.bot = bot


def _home_embed(author, prefix, total_commands):
    from utils.cv2 import CV2Embed
    from utils.config import BRAND_NAME
    from utils.emoji import (
        ARROWRED, BOOST, CAST, GAMES, LEVEL_UP, LOCK, MESSAGE, MINECRAFT, MUSIC,
        NEW, PIN, SEED, STAR, SWORD, SYSTEM, THUNDER, TICKET, WIFI, ZAI, ZARROW,
        ZBAN, ZBOT, ZCIRCLE, ZCIRCLE_ALT1, ZCLOUD, ZCOUNTING, ZMODULE, ZPEOPLE,
        ZROCKET, ZSAFE, ZTADA, ZUNMUTE, ZWRENCH,
    )

    embed = CV2Embed(
        description=(
            f"**{ARROWRED} __Start {BRAND_NAME} Today__**\n"
            f"**{ZARROW} Type {prefix}antinuke enable**\n"
            f"**{ZARROW} Server Prefix:** `{prefix}`\n"
            f"**{ZARROW} Total Commands:** `{total_commands}`\n"),
        color=0xFF0000)

    embed.add_field(
        name=f"{ZCLOUD} Main Features",
        value=f">>> \n {ZSAFE} `»` Security\n"
              f" {ZBOT} `»` Automoderation\n"
              f" {ZWRENCH} `»` Utility\n"
              f" {MUSIC} `»` Music\n"
              f" {WIFI} `»` Autoreact & responder\n"
              f" {SWORD} `»` Moderation\n"
              f" {ZPEOPLE} `»` Autorole & Invc\n"
              f" {ZROCKET} `»` Fun\n"
              f" {GAMES} `»` Games\n"
              f" {ZBAN} `»` Ignore Channels\n"
              f" {WIFI} `»` Server\n"
              f" {ZUNMUTE} `»` Voice\n"
              f" {SEED} `»` Welcomer\n"
              f" {ZTADA} `»` Giveaway\n"
              f" {TICKET} `»` Ticket {NEW}\n"
              f" {ZPEOPLE} `»` Invite Tracker {NEW}\n")

    embed.add_field(
        name=f" {ZMODULE} Extra Features",
        value=f">>> \n {CAST} `»` Advance Logging\n"
              f" {STAR} `»` Vanityroles\n"
              f" {ZCOUNTING} `»` Counting {NEW}\n"
              f" {SYSTEM} `»` J2C {NEW}\n"
              f" {ZAI} `»` AI {NEW}\n"
              f" {BOOST} `»` Boost {NEW}\n"
              f" {LEVEL_UP} `»` Leveling {NEW}\n"
              f" {PIN} `»` Sticky {NEW}\n"
              f" {THUNDER} `»` Verification {NEW}\n"
              f" {LOCK} `»` Encryption {NEW}\n"
              f" {MINECRAFT} `»` Minecraft {NEW}\n"
              f" {MESSAGE} `»` Joindm {NEW}\n"
              f" {ZCIRCLE} `»` Birthday {NEW}\n"
              f" {ZCIRCLE_ALT1} `»` Customrole\n")

    embed.set_footer(text=f"Requested By {author} | [Support](https://discord.gg/und)")
    return embed


async def build_help_view(bot, author, prefix, category=None):
    """The one help view used everywhere (matches ZyroX CV2 layout)."""
    mapping = {cog: cog.get_commands() for cog in bot.cogs.values()}
    total = len(set(bot.walk_commands()))
    embed = _home_embed(author, prefix, total)
    view = View(mapping=mapping, ctx=_HelpCtx(author, prefix, bot), homeembed=embed, ui=2)

    if category:
        wanted = str(category).strip().lower()
        for index, page in enumerate(view.pages):
            if wanted and wanted in str(page.get("title", "")).lower():
                view.index = index
                view._rebuild()
                break
    return view
