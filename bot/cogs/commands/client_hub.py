# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   UND — All In One                                               ║
# ║                                                                  ║
# ║                                                                  ║
# ║   © 2026 KURAPIKA — All Rights Reserved                          ║
# ║   Built & owned by Kurapika                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

"""Client delivery panel.

A red embed lists every client as its own button. Clicking a button sends
the `.jar` to that member only (ephemeral), together with the disclaimer,
the file size and its SHA-256.

Files live in `clients/<guild_id>/<slug>/` (see `utils/client_store.py`),
so they are never committed to git and can be dropped in from a panel or
SFTP and registered with `/client scan`.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import aiosqlite
import discord
from discord.ext import commands

from utils import client_store as store

DB_PATH = "db/clients.db"
MAX_PER_PAGE = 20          # 4 rows x 5 buttons, pagination lives in row 5
DEFAULT_COLOR = 0xFF0000
DEFAULT_TITLE = "🔴 UND Client Delivery"
DEFAULT_DESCRIPTION = "Choose your client below — the file is sent privately to **you only**."
DEFAULT_DISCLAIMER = (
    "UND doesn't host, endorse or distribute any client. Files are provided by the server "
    "staff **for educational purposes only** and are not affiliated with Mojang or Microsoft. "
    "Using cheat clients on other servers may break their rules — use on **BONBON SMP** at your own risk."
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS client_config (
    guild_id INTEGER PRIMARY KEY,
    channel_id INTEGER,
    message_id INTEGER,
    role_id INTEGER,
    title TEXT,
    description TEXT,
    banner_url TEXT,
    thumbnail_url TEXT,
    color INTEGER,
    disclaimer TEXT,
    total_downloads INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    version TEXT,
    emoji TEXT,
    notes TEXT,
    file_name TEXT,
    file_path TEXT,
    size INTEGER DEFAULT 0,
    sha256 TEXT,
    enabled INTEGER DEFAULT 1,
    downloads INTEGER DEFAULT 0,
    created_at TEXT,
    UNIQUE(guild_id, slug)
);
CREATE TABLE IF NOT EXISTS client_deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    client_id INTEGER,
    user_id INTEGER,
    created_at TEXT
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_color(raw: str | None) -> int | None:
    if not raw:
        return None
    value = raw.strip().lstrip("#")
    try:
        return int(value, 16) & 0xFFFFFF
    except ValueError:
        return None


def _safe_emoji(raw) -> discord.PartialEmoji | None:
    """Return a usable button emoji, or None when the stored value is invalid."""
    if not raw:
        return None
    try:
        emoji = discord.PartialEmoji.from_str(str(raw).strip())
    except (ValueError, TypeError, AttributeError):
        return None
    if emoji.id is None and not emoji.is_unicode_emoji():
        return None
    return emoji


class ClientButton(discord.ui.Button):
    def __init__(self, cog: "ClientHub", guild_id: int, row: dict):
        label = f"{row['name']} {row.get('version') or ''}".strip()[:80] or "Client"
        super().__init__(
            label=label,
            emoji=_safe_emoji(row.get("emoji")),
            style=discord.ButtonStyle.secondary,
            custom_id=f"und:cl:{guild_id}:{row['id']}",
        )
        self.cog = cog
        self.guild_id = guild_id
        self.client_id = row["id"]

    async def callback(self, interaction: discord.Interaction):
        await self.cog.deliver(interaction, self.guild_id, self.client_id)


class PageButton(discord.ui.Button):
    def __init__(self, cog: "ClientHub", guild_id: int, page: int, emoji: str, disabled: bool = False):
        super().__init__(
            emoji=emoji,
            style=discord.ButtonStyle.primary,
            custom_id=f"und:clp:{guild_id}:{page}",
            disabled=disabled,
        )
        self.cog = cog
        self.guild_id = guild_id
        self.page = page

    async def callback(self, interaction: discord.Interaction):
        await self.cog.show_page(interaction, self.guild_id, self.page)


class PanelView(discord.ui.View):
    def __init__(self, cog: "ClientHub", guild_id: int, page: int, rows: list[dict]):
        super().__init__(timeout=None)
        pages = max(1, -(-len(rows) // MAX_PER_PAGE))
        self.page = max(0, min(page, pages - 1))

        for row in rows[self.page * MAX_PER_PAGE:(self.page + 1) * MAX_PER_PAGE]:
            self.add_item(ClientButton(cog, guild_id, row))

        if pages > 1:
            self.add_item(
                PageButton(cog, guild_id, self.page - 1, "◀️", disabled=self.page == 0)
            )
            self.add_item(
                PageButton(cog, guild_id, self.page + 1, "▶️", disabled=self.page >= pages - 1)
            )


class ClientHub(commands.Cog, name="clients"):
    """Client delivery panel with private `.jar` downloads."""

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def say(ctx: commands.Context, content: str | None = None, **kwargs):
        """Reply safely: `ephemeral` only exists on interaction contexts."""
        if ctx.interaction is None:
            kwargs.pop("ephemeral", None)
        try:
            await ctx.send(content, **kwargs)
        except discord.NotFound:
            pass  # interaction expired before we could answer (10062)

    @staticmethod
    async def defer(ctx: commands.Context):
        """Acknowledge at once: DB work + panel refresh can pass 3 seconds."""
        try:
            if ctx.interaction is not None:
                if not ctx.interaction.response.is_done():
                    await ctx.interaction.response.defer(ephemeral=True, thinking=True)
            else:
                await ctx.trigger_typing()
        except discord.HTTPException:
            pass

    # ── database ─────────────────────────────────────────────────────────────
    _schema_ready = False

    async def _connect(self):
        os.makedirs("db", exist_ok=True)
        db = await aiosqlite.connect(DB_PATH, timeout=15)
        db.row_factory = aiosqlite.Row
        if not type(self)._schema_ready:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.executescript(SCHEMA)
            await db.commit()
            type(self)._schema_ready = True
        return db

    async def cog_load(self):
        store.BASE_DIR.mkdir(parents=True, exist_ok=True)
        db = await self._connect()
        try:
            async with db.execute(
                "SELECT guild_id FROM client_config WHERE message_id IS NOT NULL"
            ) as cursor:
                guilds = [row[0] for row in await cursor.fetchall()]
        finally:
            await db.close()

        for guild_id in guilds:
            try:
                rows = await self.list_clients(guild_id)
                self.bot.add_view(PanelView(self, guild_id, 0, rows))
            except Exception:
                continue

    async def get_config(self, guild_id: int) -> dict:
        db = await self._connect()
        try:
            async with db.execute(
                "SELECT * FROM client_config WHERE guild_id = ?", (guild_id,)
            ) as cursor:
                row = await cursor.fetchone()
        finally:
            await db.close()
        if row is None:
            return {
                "guild_id": guild_id,
                "channel_id": None,
                "message_id": None,
                "role_id": None,
                "title": DEFAULT_TITLE,
                "description": DEFAULT_DESCRIPTION,
                "banner_url": None,
                "thumbnail_url": None,
                "color": DEFAULT_COLOR,
                "disclaimer": DEFAULT_DISCLAIMER,
                "total_downloads": 0,
            }
        return dict(row)

    async def patch_config(self, guild_id: int, **fields) -> None:
        db = await self._connect()
        try:
            await db.execute(
                "INSERT INTO client_config (guild_id) VALUES (?) ON CONFLICT(guild_id) DO NOTHING",
                (guild_id,),
            )
            if fields:
                assignments = ", ".join(f"{column} = ?" for column in fields)
                await db.execute(
                    f"UPDATE client_config SET {assignments} WHERE guild_id = ?",
                    (*fields.values(), guild_id),
                )
            await db.commit()
        finally:
            await db.close()

    async def list_clients(self, guild_id: int) -> list[dict]:
        db = await self._connect()
        try:
            async with db.execute(
                "SELECT * FROM clients WHERE guild_id = ? AND enabled = 1 ORDER BY name COLLATE NOCASE",
                (guild_id,),
            ) as cursor:
                rows = await cursor.fetchall()
        finally:
            await db.close()
        return [dict(row) for row in rows]

    async def get_client(self, client_id: int) -> dict | None:
        db = await self._connect()
        try:
            async with db.execute("SELECT * FROM clients WHERE id = ?", (client_id,)) as cursor:
                row = await cursor.fetchone()
        finally:
            await db.close()
        return dict(row) if row else None

    async def upsert_client(self, guild_id: int, meta: dict) -> None:
        db = await self._connect()
        try:
            await db.execute(
                """
                INSERT INTO clients
                    (guild_id, slug, name, version, emoji, notes, file_name, file_path, size, sha256, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(guild_id, slug) DO UPDATE SET
                    name = excluded.name,
                    version = excluded.version,
                    emoji = excluded.emoji,
                    notes = excluded.notes,
                    file_name = excluded.file_name,
                    file_path = excluded.file_path,
                    size = excluded.size,
                    sha256 = excluded.sha256
                """,
                (
                    guild_id,
                    meta["slug"],
                    meta["name"],
                    meta.get("version", ""),
                    meta.get("emoji", ""),
                    meta.get("notes", ""),
                    meta.get("file_name"),
                    meta["file_path"],
                    int(meta.get("size") or 0),
                    meta.get("sha256"),
                    _now(),
                ),
            )
            await db.commit()
        finally:
            await db.close()

    async def bump_downloads(self, guild_id: int, client_id: int, user_id: int) -> None:
        db = await self._connect()
        try:
            await db.execute("UPDATE clients SET downloads = downloads + 1 WHERE id = ?", (client_id,))
            await db.execute(
                "UPDATE client_config SET total_downloads = total_downloads + 1 WHERE guild_id = ?",
                (guild_id,),
            )
            await db.execute(
                "INSERT INTO client_deliveries (guild_id, client_id, user_id, created_at) VALUES (?, ?, ?, ?)",
                (guild_id, client_id, user_id, _now()),
            )
            await db.commit()
        finally:
            await db.close()

    # ── panel ────────────────────────────────────────────────────────────────
    async def panel_embed(self, guild_id: int) -> discord.Embed:
        config = await self.get_config(guild_id)
        rows = await self.list_clients(guild_id)

        embed = discord.Embed(
            title=config["title"] or DEFAULT_TITLE,
            description=config["description"] or DEFAULT_DESCRIPTION,
            color=int(config["color"] or DEFAULT_COLOR),
        )
        embed.add_field(
            name="✅ Total Downloads",
            value=f"**{int(config['total_downloads'] or 0):,}**",
            inline=True,
        )
        embed.add_field(name="📦 Clients", value=f"**{len(rows)}**", inline=True)
        if config["banner_url"]:
            embed.set_image(url=config["banner_url"])
        if config["thumbnail_url"]:
            embed.set_thumbnail(url=config["thumbnail_url"])
        embed.set_footer(text="⚠️ Educational purposes only — UND doesn't endorse any client.")
        return embed

    async def panel_view(self, guild_id: int, page: int = 0) -> PanelView:
        rows = await self.list_clients(guild_id)
        return PanelView(self, guild_id, page, rows)

    async def refresh_panel(self, guild) -> discord.Message | None:
        config = await self.get_config(guild.id)
        if not config["channel_id"]:
            return None
        channel = guild.get_channel(int(config["channel_id"]))
        if channel is None:
            return None

        embed = await self.panel_embed(guild.id)
        view = await self.panel_view(guild.id)

        if config["message_id"]:
            try:
                message = await channel.fetch_message(int(config["message_id"]))
                await message.edit(embed=embed, view=view)
                return message
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

        try:
            message = await channel.send(embed=embed, view=view)
        except discord.HTTPException:
            return None
        await self.patch_config(guild.id, message_id=message.id)
        return message

    async def show_page(self, interaction: discord.Interaction, guild_id: int, page: int):
        embed = await self.panel_embed(guild_id)
        view = await self.panel_view(guild_id, page)
        try:
            await interaction.response.edit_message(embed=embed, view=view)
        except discord.HTTPException:
            try:
                await interaction.followup.send(
                    "❌ This panel is out of date — ask a staff member to run `/client setup`.",
                    ephemeral=True,
                )
            except discord.HTTPException:
                pass

    # ── delivery ─────────────────────────────────────────────────────────────
    async def deliver(self, interaction: discord.Interaction, guild_id: int, client_id: int):
        # Acknowledge first — DB lookups and uploads can exceed Discord's 3s window.
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True, thinking=True)
        except discord.HTTPException:
            return  # the interaction is already gone

        async def reply(message: str) -> None:
            try:
                await interaction.followup.send(message, ephemeral=True)
            except discord.HTTPException:
                pass

        config = await self.get_config(guild_id)
        row = await self.get_client(client_id)

        if row is None or row["guild_id"] != guild_id:
            return await reply("❌ This client is no longer available.")

        if not row.get("enabled", 1):
            return await reply("❌ This client is currently disabled.")

        role_id = config["role_id"]
        if role_id:
            roles = getattr(interaction.user, "roles", [])
            if not any(role.id == int(role_id) for role in roles):
                return await reply(
                    f"❌ You need the <@&{role_id}> role to download clients. Ask a staff member."
                )

        # Never trust the stored path: it must stay inside clients/.
        base = store.BASE_DIR.resolve()
        path = (store.BASE_DIR / str(row["file_path"] or "")).resolve()
        if base not in path.parents or not path.is_file():
            return await interaction.followup.send(
                "❌ The file is missing on the host. Contact a staff member.", ephemeral=True
            )

        size = path.stat().st_size

        # discord.py's guild.filesize_limit is stale (10 MiB on tiers 0/1).
        # Prefer the value Discord reports on the interaction itself.
        limit = store.delivery_limit(interaction, interaction.guild)
        parts_count = 1 if size <= limit else -(-size // limit)
        if parts_count > store.MAX_PARTS:
            return await interaction.followup.send(
                f"❌ This client is **{store.human_size(size)}** — too big even when split "
                f"({parts_count} parts). Ask a staff member for a direct link.",
                ephemeral=True,
            )

        emoji = _safe_emoji(row.get("emoji"))
        title = f"{emoji or '🔴'} {row['name']} {row.get('version') or ''}".strip()
        file_name = row.get("file_name") or path.name
        sha = row.get("sha256") or store.sha256_file(path)

        description = "**Your file is attached below.**\n🔒 Only you can see this message.\n"
        if parts_count > 1:
            description = (
                f"**Split into {parts_count} parts** ({store.human_size(limit)} max each).\n"
                "🧩 Run **merge.bat** (Windows) or `cat *.part* > file` (Linux/macOS) "
                "to rebuild the file — see `MERGE-INSTRUCTIONS.txt`.\n"
                "🔒 Only you can see this message.\n"
            )
        description += f"\n⚠️ **Disclaimer**\n{(config['disclaimer'] or DEFAULT_DISCLAIMER)[:3500]}"

        embed = discord.Embed(title=title[:256], description=description, color=DEFAULT_COLOR)
        if row.get("notes"):
            embed.add_field(name="📝 Notes", value=row["notes"][:1024], inline=False)
        embed.add_field(name="📦 Size", value=store.human_size(size), inline=True)
        if parts_count > 1:
            embed.add_field(name="🧩 Parts", value=f"`{parts_count}`", inline=True)
        embed.add_field(name="🔒 SHA-256", value=f"`{sha[:32]}…`", inline=True)
        embed.set_footer(text=f"UND • sent privately to {interaction.user}"[:2048])

        temp_dir = None
        try:
            if parts_count == 1:
                await interaction.followup.send(
                    embed=embed,
                    file=discord.File(path, filename=file_name),
                    ephemeral=True,
                )
            else:
                temp_dir, parts = store.make_parts(path, limit)
                helpers = store.write_merge_helpers(temp_dir, parts, file_name, sha)
                first = parts[:8]
                await interaction.followup.send(
                    embed=embed,
                    files=[discord.File(p, filename=p.name) for p in first]
                    + [discord.File(h, filename=h.name) for h in helpers],
                    ephemeral=True,
                )
                rest = parts[8:]
                for offset in range(0, len(rest), 10):
                    chunk = rest[offset:offset + 10]
                    await interaction.followup.send(
                        content=f"🧩 Parts {offset + 9}–{offset + 9 + len(chunk) - 1} of {parts_count}",
                        files=[discord.File(p, filename=p.name) for p in chunk],
                        ephemeral=True,
                    )
        except (discord.HTTPException, OSError) as error:
            try:
                await interaction.followup.send(
                    f"❌ I couldn't upload the file ({type(error).__name__}). "
                    "Try again in a moment or ask a staff member.",
                    ephemeral=True,
                )
            except discord.HTTPException:
                pass  # the interaction is already gone
            return
        finally:
            store.cleanup_temp(temp_dir)

        try:
            await self.bump_downloads(guild_id, client_id, interaction.user.id)
        except aiosqlite.Error:
            pass  # the file was delivered; counters are best effort

    # ── commands ─────────────────────────────────────────────────────────────
    @commands.hybrid_group(
        name="client",
        description="Client delivery panel — upload, list and hand out clients.",
        invoke_without_command=True,
    )
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def client(self, ctx: commands.Context):
        await self.defer(ctx)
        config = await self.get_config(ctx.guild.id)
        rows = await self.list_clients(ctx.guild.id)
        role_text = f"<@&{config['role_id']}>" if config["role_id"] else "`not set`"
        embed = discord.Embed(
            title="🔴 Client Delivery",
            description=(
                f"**Clients:** `{len(rows)}` • **Downloads:** `{int(config['total_downloads'] or 0):,}`\n"
                f"**Role:** {role_text}\n\n"
                "`/client setup` • `/client add` • `/client scan` • `/client list` • `/client panel`"
            ),
            color=DEFAULT_COLOR,
        )
        await self.say(ctx, embed=embed)

    @client.command(name="setup", description="Create or refresh the delivery panel.")
    @commands.has_guild_permissions(manage_guild=True)
    async def setup(self, ctx: commands.Context, channel: discord.TextChannel = None, role: discord.Role = None):
        await self.defer(ctx)
        channel = channel or ctx.channel
        fields = {"channel_id": channel.id}
        if role is not None:
            fields["role_id"] = role.id
        await self.patch_config(ctx.guild.id, **fields)

        message = await self.refresh_panel(ctx.guild)
        if message is None:
            return await self.say(ctx, "❌ I cannot post in that channel.", ephemeral=True)
        await self.say(ctx, 
            f"✅ Panel ready in {channel.mention}"
            + (f" — only {role.mention} can download." if role else ""),
            ephemeral=True,
        )

    @client.command(name="add", description="Upload a client file to the panel.")
    @commands.has_guild_permissions(manage_guild=True)
    async def add(
        self,
        ctx: commands.Context,
        name: str,
        file: discord.Attachment,
        version: str = "",
        emoji: str = "",
    ):
        name = (name or "").strip()
        if not name:
            return await self.say(ctx, "❌ Give the client a name.", ephemeral=True)
        emoji = (emoji or "").strip()
        if emoji and _safe_emoji(emoji) is None:
            return await self.say(
                ctx,
                "❌ Invalid emoji. Use a unicode emoji like ⭐ or a custom one like `<:name:id>`.",
                ephemeral=True,
            )
        if file.size > store.MAX_BYTES:
            return await self.say(ctx, 
                f"❌ Max upload is **{store.human_size(store.MAX_BYTES)}**. Put the file in "
                f"`clients/{ctx.guild.id}/<name>/` on the host and run `/client scan`.",
                ephemeral=True,
            )
        await ctx.defer(ephemeral=True)
        try:
            data = await file.read()
            meta = store.save_upload(ctx.guild.id, name, file.filename, data, version=version, emoji=emoji)
        except ValueError as error:
            return await self.say(ctx, f"❌ {error}", ephemeral=True)

        await self.upsert_client(ctx.guild.id, meta)
        await self.refresh_panel(ctx.guild)
        await self.say(ctx, 
            f"✅ **{name}** added ({store.human_size(meta['size'])}) and the panel was refreshed.",
            ephemeral=True,
        )

    @client.command(name="scan", description="Import clients from the clients/ folder on the host.")
    @commands.has_guild_permissions(manage_guild=True)
    async def scan(self, ctx: commands.Context):
        await ctx.defer(ephemeral=True)
        found = store.scan(ctx.guild.id)
        for meta in found:
            await self.upsert_client(ctx.guild.id, meta)
        oversized = [meta["name"] for meta in found if meta.get("oversized")]
        await self.refresh_panel(ctx.guild)
        if oversized:
            await self.say(
                ctx,
                "⚠️ Big files (auto-split when downloading): "
                + ", ".join(oversized[:5]),
                ephemeral=True,
            )
        await self.say(ctx, 
            f"✅ Scanned `clients/{ctx.guild.id}/` — **{len(found)}** client(s) registered.",
            ephemeral=True,
        )

    @client.command(name="list", description="List every client on the panel.")
    @commands.has_guild_permissions(manage_guild=True)
    async def list_clients_cmd(self, ctx: commands.Context):
        rows = await self.list_clients(ctx.guild.id)
        if not rows:
            return await self.say(ctx, "ℹ️ No clients yet. `/client add` or `/client scan`.", ephemeral=True)

        lines = [
            f"`{index + 1:02d}` **{row['name']}** {row.get('version') or ''} — "
            f"{store.human_size(row['size'])} • {row['downloads']} downloads"
            for index, row in enumerate(rows[:40])
        ]
        embed = discord.Embed(
            title=f"🔴 Clients ({len(rows)})",
            description=(
                "\n".join(lines)
                + (f"\n…and {len(rows) - 40} more." if len(rows) > 40 else "")
            )[:4000],
            color=DEFAULT_COLOR,
        )
        await self.say(ctx, embed=embed)

    @client.command(name="remove", description="Delete a client and its file.")
    @commands.has_guild_permissions(manage_guild=True)
    async def remove(self, ctx: commands.Context, name: str):
        await self.defer(ctx)
        rows = await self.list_clients(ctx.guild.id)
        slug = store.slugify(name)
        match = next((row for row in rows if row["slug"] == slug or row["name"].lower() == name.lower()), None)
        if match is None:
            return await self.say(ctx, f"❌ No client named `{name}`.", ephemeral=True)

        store.delete_client(ctx.guild.id, match["slug"])
        db = await self._connect()
        try:
            await db.execute("DELETE FROM clients WHERE id = ?", (match["id"],))
            await db.commit()
        finally:
            await db.close()

        await self.refresh_panel(ctx.guild)
        await self.say(ctx, f"🗑️ **{match['name']}** removed.", ephemeral=True)

    @client.command(name="edit", description="Edit a client's version, emoji, notes or file.")
    @commands.has_guild_permissions(manage_guild=True)
    async def edit(
        self,
        ctx: commands.Context,
        name: str,
        version: str = None,
        emoji: str = None,
        notes: str = None,
        file: discord.Attachment = None,
    ):
        await self.defer(ctx)
        rows = await self.list_clients(ctx.guild.id)
        slug = store.slugify(name)
        match = next((row for row in rows if row["slug"] == slug or row["name"].lower() == name.lower()), None)
        if match is None:
            return await self.say(ctx, f"❌ No client named `{name}`.", ephemeral=True)

        meta = {
            "slug": match["slug"],
            "name": match["name"],
            "version": version if version is not None else match.get("version"),
            "emoji": emoji if emoji is not None else match.get("emoji"),
            "notes": notes if notes is not None else match.get("notes"),
            "file_name": match.get("file_name"),
            "file_path": match["file_path"],
            "size": match["size"],
            "sha256": match.get("sha256"),
        }

        if file is not None:
            if file.size > store.MAX_BYTES:
                return await self.say(ctx, 
                    f"❌ Max upload is **{store.human_size(store.MAX_BYTES)}**.", ephemeral=True
                )
            data = await file.read()
            saved = store.save_upload(
                ctx.guild.id, match["name"], file.filename, data,
                version=meta["version"] or "", emoji=meta["emoji"] or "", notes=meta["notes"] or "",
            )
            meta.update(saved)

        store.write_meta(store.client_dir(ctx.guild.id, meta["slug"]), meta)
        await self.upsert_client(ctx.guild.id, meta)
        await self.refresh_panel(ctx.guild)
        await self.say(ctx, f"✅ **{meta['name']}** updated.", ephemeral=True)

    @client.command(name="panel", description="Edit the panel embed (title, description, banner, color).")
    @commands.has_guild_permissions(manage_guild=True)
    async def panel(
        self,
        ctx: commands.Context,
        title: str = None,
        description: str = None,
        banner: str = None,
        thumbnail: str = None,
        color: str = None,
        disclaimer: str = None,
    ):
        fields = {}
        if title is not None:
            fields["title"] = title
        if description is not None:
            fields["description"] = description
        if banner is not None:
            fields["banner_url"] = banner
        if thumbnail is not None:
            fields["thumbnail_url"] = thumbnail
        if color is not None:
            parsed = _parse_color(color)
            if parsed is None:
                return await self.say(ctx, "❌ Color must be hex, e.g. `FF0000` or `#ff0000`.", ephemeral=True)
            fields["color"] = parsed
        if disclaimer is not None:
            fields["disclaimer"] = disclaimer

        if "title" in fields:
            fields["title"] = fields["title"][:256] or DEFAULT_TITLE
        if "description" in fields:
            fields["description"] = fields["description"][:4000] or DEFAULT_DESCRIPTION
        if "disclaimer" in fields:
            fields["disclaimer"] = fields["disclaimer"][:3500] or DEFAULT_DISCLAIMER
        for key in ("banner_url", "thumbnail_url"):
            value = fields.get(key)
            if value and not value.startswith(("http://", "https://")):
                return await self.say(
                    ctx, "❌ Banner/thumbnail must be a http(s) image URL.", ephemeral=True
                )

        if not fields:
            return await self.say(ctx,
                "ℹ️ Use `/client panel title:… description:… banner:… thumbnail:… color:FF0000 disclaimer:…`",
                ephemeral=True,
            )

        await self.defer(ctx)
        await self.patch_config(ctx.guild.id, **fields)
        await self.refresh_panel(ctx.guild)
        await self.say(ctx, f"✅ Panel updated ({', '.join(fields)}).", ephemeral=True)

    @client.command(name="role", description="Choose the role allowed to download clients.")
    @commands.has_guild_permissions(manage_guild=True)
    async def role(self, ctx: commands.Context, role: discord.Role = None):
        await self.defer(ctx)
        if role is None:
            await self.patch_config(ctx.guild.id, role_id=None)
            return await self.say(ctx, "✅ Everyone in the server can download now.", ephemeral=True)
        await self.patch_config(ctx.guild.id, role_id=role.id)
        await self.say(ctx, f"✅ Only {role.mention} can download clients.", ephemeral=True)

    @client.command(name="stats", description="Download statistics.")
    @commands.has_guild_permissions(manage_guild=True)
    async def stats(self, ctx: commands.Context):
        await self.defer(ctx)
        config = await self.get_config(ctx.guild.id)
        rows = await self.list_clients(ctx.guild.id)
        top = sorted(rows, key=lambda row: row["downloads"], reverse=True)[:10]
        lines = [f"**{row['name']}** — {row['downloads']} downloads" for row in top] or ["No downloads yet."]
        embed = discord.Embed(
            title="📊 Client downloads",
            description=(
                f"**Total:** `{int(config['total_downloads'] or 0):,}`\n"
                f"**Clients:** `{len(rows)}`\n\n" + "\n".join(lines)
            ),
            color=DEFAULT_COLOR,
        )
        await self.say(ctx, embed=embed)

    @client.error
    async def client_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await self.say(ctx, "❌ You need **Manage Server** to use this.", ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            await self.say(ctx, f"❌ Missing argument: `{error.param.name}`.", ephemeral=True)
        elif isinstance(error, commands.BadArgument):
            await self.say(ctx, f"❌ {error}", ephemeral=True)
        else:
            await self.say(ctx, "❌ Something went wrong. Check the bot logs.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ClientHub(bot))
