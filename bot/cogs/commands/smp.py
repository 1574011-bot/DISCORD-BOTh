# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   UND — All In One                                               ║
# ║                                                                  ║
# ║   © 2026 KURAPIKA — All Rights Reserved                          ║
# ║   Built & owned by Kurapika                                      ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

"""SMP module — applications, IGN linking and live status.

Works without RCON or any server permission:
  * /apply   -> modal, posts a staff review card with Approve / Deny buttons
  * /link    -> links a Discord account to a Minecraft IGN (staff approved)
  * /smp ... -> setup, live status, pending lists

Cracked (offline-mode) friendly: the Minecraft UUID is computed locally with the
same algorithm the server uses, and nothing depends on Mojang's API.
"""

import hashlib
import os
import re
import uuid as uuid_lib
from datetime import datetime, timedelta, timezone

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

from utils.mcstatus_api import fetch_status

DB_PATH = "db/smp.db"
IGN_PATTERN = re.compile(r"^\.?[A-Za-z0-9_]{3,16}$")
RELINK_COOLDOWN = timedelta(days=14)
REAPPLY_COOLDOWN = timedelta(hours=24)
COLOR_RED = 0xFF0000
COLOR_GREEN = 0x2ECC71

SCHEMA = """
CREATE TABLE IF NOT EXISTS smp_config (
    guild_id         INTEGER PRIMARY KEY,
    host             TEXT,
    port             INTEGER DEFAULT 0,
    apply_channel_id INTEGER,
    review_channel_id INTEGER,
    audit_channel_id INTEGER,
    member_role_id   INTEGER,
    staff_role_id    INTEGER
);
CREATE TABLE IF NOT EXISTS smp_applications (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id     INTEGER NOT NULL,
    user_id      INTEGER NOT NULL,
    ign          TEXT NOT NULL,
    platform     TEXT,
    age          TEXT,
    experience   TEXT,
    reason       TEXT,
    status       TEXT NOT NULL DEFAULT 'pending',
    message_id   INTEGER,
    created_at   TEXT,
    decided_at   TEXT,
    decided_by   INTEGER
);
CREATE TABLE IF NOT EXISTS smp_links (
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    ign        TEXT NOT NULL,
    uuid       TEXT,
    platform   TEXT,
    status     TEXT NOT NULL DEFAULT 'pending',
    message_id INTEGER,
    created_at TEXT,
    decided_at TEXT,
    decided_by INTEGER,
    PRIMARY KEY (guild_id, user_id)
);
CREATE TABLE IF NOT EXISTS smp_audit (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER,
    action     TEXT,
    detail     TEXT,
    actor_id   INTEGER,
    created_at TEXT
);
"""


def offline_uuid(ign: str) -> str:
    """The UUID an offline-mode (cracked) server gives to a username."""
    raw = hashlib.md5(f"OfflinePlayer:{ign}".encode("utf-8")).digest()
    return str(uuid_lib.UUID(bytes=raw, version=3))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def avatar_url(ign: str) -> str:
    return f"https://mc-heads.net/avatar/{ign.replace('.', '')}/128"


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


async def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def get_config(guild_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM smp_config WHERE guild_id = ?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
    return dict(row) if row else None


async def save_config(guild_id: int, **fields) -> None:
    await init_db()
    columns = ", ".join(f"{name} = ?" for name in fields)
    values = [*fields.values(), guild_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO smp_config (guild_id) VALUES (?) ON CONFLICT(guild_id) DO NOTHING",
            (guild_id,),
        )
        if fields:
            await db.execute(f"UPDATE smp_config SET {columns} WHERE guild_id = ?", values)
        await db.commit()


async def audit(guild: discord.Guild | None, action: str, detail: str, actor_id: int | None) -> None:
    if guild is None:
        return
    config = await get_config(guild.id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO smp_audit (guild_id, action, detail, actor_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (guild.id, action, detail[:900], actor_id, now_iso()),
        )
        await db.commit()
    channel_id = (config or {}).get("audit_channel_id")
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if channel is None:
        return
    embed = discord.Embed(title="🛡️ SMP Audit", description=f"**{action}**\n{detail}"[:3900], color=COLOR_RED)
    embed.timestamp = datetime.now(timezone.utc)
    if actor_id:
        embed.set_footer(text=f"Actor ID: {actor_id}")
    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Application modal
# ─────────────────────────────────────────────────────────────────────────────
class ApplyModal(discord.ui.Modal):
    ign = discord.ui.TextInput(label="Minecraft username (IGN)", placeholder="Kurapika2010", max_length=16)
    platform = discord.ui.TextInput(label="Platform", placeholder="java / bedrock", max_length=8, default="java")
    age = discord.ui.TextInput(label="Your age", placeholder="18", max_length=3, required=False)
    experience = discord.ui.TextInput(
        label="How long have you played Minecraft?", placeholder="e.g. 3 years, mostly survival", max_length=100, required=False
    )
    reason = discord.ui.TextInput(
        label="Why do you want to join the SMP?", style=discord.TextStyle.paragraph, max_length=500
    )

    def __init__(self, cog: "SMP", interaction: discord.Interaction):
        super().__init__(title="SMP Application", timeout=600)
        self.cog = cog
        self.origin = interaction

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.create_application(
            interaction,
            {
                "ign": str(self.ign.value).strip(),
                "platform": str(self.platform.value).strip(),
                "age": str(self.age.value or "").strip(),
                "experience": str(self.experience.value or "").strip(),
                "reason": str(self.reason.value).strip(),
            },
        )


# ─────────────────────────────────────────────────────────────────────────────
# Persistent review views (survive restarts, routed by message id)
# ─────────────────────────────────────────────────────────────────────────────
class ReviewView(discord.ui.View):
    def __init__(self, cog: "SMP"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Approve", emoji="✅", style=discord.ButtonStyle.danger, custom_id="smp_app_approve")
    async def approve(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self.cog.decide_application(interaction, interaction.message.id, "approved")

    @discord.ui.button(label="Deny", emoji="❌", style=discord.ButtonStyle.danger, custom_id="smp_app_deny")
    async def deny(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self.cog.decide_application(interaction, interaction.message.id, "denied")

    @discord.ui.button(label="Mark whitelisted", emoji="✅", style=discord.ButtonStyle.danger, custom_id="smp_app_added")
    async def added(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self.cog.decide_application(interaction, interaction.message.id, "added")


class LinkReviewView(discord.ui.View):
    def __init__(self, cog: "SMP"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Approve link", emoji="✅", style=discord.ButtonStyle.danger, custom_id="smp_link_approve")
    async def approve(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self.cog.decide_link(interaction, interaction.message.id, "approved")

    @discord.ui.button(label="Reject", emoji="❌", style=discord.ButtonStyle.danger, custom_id="smp_link_deny")
    async def deny(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self.cog.decide_link(interaction, interaction.message.id, "rejected")


# ─────────────────────────────────────────────────────────────────────────────
# Cog
# ─────────────────────────────────────────────────────────────────────────────
class SMP(commands.Cog):
    """Applications + IGN linking + live status for the SMP."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ready = False

    async def cog_load(self):
        await init_db()
        self.bot.add_view(ReviewView(self))
        self.bot.add_view(LinkReviewView(self))
        self.ready = True

    # ── helpers ────────────────────────────────────────────────────────────
    async def is_staff(self, member: discord.Member) -> bool:
        if await self.bot.is_owner(member):
            return True
        if member.guild_permissions.manage_guild:
            return True
        config = await get_config(member.guild.id)
        role_id = (config or {}).get("staff_role_id")
        return bool(role_id) and any(role.id == role_id for role in member.roles)

    async def staff_member(self, interaction: discord.Interaction):
        """Return the invoking Member even when interaction.member is missing."""
        guild = interaction.guild
        if guild is None:
            return None
        member = guild.get_member(interaction.user.id)
        if member is None:
            try:
                member = await guild.fetch_member(interaction.user.id)
            except discord.HTTPException:
                return None
        return member

    async def apply_member_role(self, guild: discord.Guild, user_id: int) -> str:
        config = await get_config(guild.id)
        role_id = (config or {}).get("member_role_id")
        if not role_id:
            return ""
        role = guild.get_role(role_id)
        if role is None:
            return "⚠️ member role not found"
        try:
            member = guild.get_member(user_id) or await guild.fetch_member(user_id)
            await member.add_roles(role, reason="SMP access granted")
            return ""
        except (discord.Forbidden, discord.HTTPException):
            return "⚠️ could not add the member role"

    async def notify_user(self, guild: discord.Guild, user_id: int, text: str) -> None:
        try:
            user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
            await user.send(embed=discord.Embed(title="SMP", description=text, color=COLOR_RED))
        except (discord.Forbidden, discord.HTTPException):
            pass

    # ── application flow ───────────────────────────────────────────────────
    async def create_application(self, interaction: discord.Interaction, data: dict):
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild
        config = await get_config(guild.id)
        review_id = (config or {}).get("review_channel_id")
        if not config or not review_id:
            return await interaction.followup.send(
                "❌ SMP applications are not configured yet. Ask a staff member to run `/smp setup`.",
                ephemeral=True,
            )

        ign = data["ign"]
        if not IGN_PATTERN.match(ign):
            return await interaction.followup.send(
                "❌ That is not a valid Minecraft username (3–16 characters: letters, numbers, `_`).", ephemeral=True
            )

        platform = "bedrock" if data["platform"].lower().startswith("b") else "java"

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT status, created_at FROM smp_applications WHERE guild_id = ? AND user_id = ? "
                "ORDER BY id DESC LIMIT 1",
                (guild.id, interaction.user.id),
            ) as cursor:
                previous = await cursor.fetchone()
            async with db.execute(
                "SELECT 1 FROM smp_applications WHERE guild_id = ? AND lower(ign) = lower(?) "
                "AND status IN ('pending', 'approved', 'added') LIMIT 1",
                (guild.id, ign),
            ) as cursor:
                taken = await cursor.fetchone()

        if previous and previous["status"] == "pending":
            return await interaction.followup.send("⏳ You already have an application waiting for review.", ephemeral=True)
        if previous and previous["status"] == "denied":
            decided = parse_iso(previous["created_at"])
            if decided and datetime.now(timezone.utc) - decided < REAPPLY_COOLDOWN:
                return await interaction.followup.send(
                    "⏳ Your last application was denied recently. You can try again in a few hours.", ephemeral=True
                )
        if taken:
            return await interaction.followup.send(
                f"❌ The username **{ign}** is already used by another application on this server.", ephemeral=True
            )

        embed = discord.Embed(title="📝 SMP Application", color=COLOR_RED)
        embed.add_field(name="Applicant", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
        embed.add_field(name="IGN", value=f"`{ign}`", inline=True)
        embed.add_field(name="Platform", value=platform, inline=True)
        embed.add_field(name="Age", value=data["age"] or "—", inline=True)
        embed.add_field(name="Experience", value=data["experience"] or "—", inline=False)
        embed.add_field(name="Why join?", value=data["reason"][:1000] or "—", inline=False)
        embed.add_field(name="Offline UUID", value=f"`{offline_uuid(ign)}`", inline=False)
        embed.set_thumbnail(url=avatar_url(ign))
        embed.set_footer(text="Approve → whitelist the IGN in-game → Mark whitelisted")
        embed.timestamp = datetime.now(timezone.utc)

        try:
            review_channel = guild.get_channel(review_id) or await guild.fetch_channel(review_id)
            message = await review_channel.send(embed=embed, view=ReviewView(self))
        except (discord.Forbidden, discord.HTTPException, AttributeError):
            return await interaction.followup.send("❌ I cannot post in the review channel.", ephemeral=True)

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO smp_applications (guild_id, user_id, ign, platform, age, experience, reason, "
                "message_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (guild.id, interaction.user.id, ign, platform, data["age"], data["experience"],
                 data["reason"], message.id, now_iso()),
            )
            await db.commit()

        await audit(guild, "Application submitted", f"{interaction.user.mention} → `{ign}`", interaction.user.id)
        await interaction.followup.send(
            f"📨 Your application for **{ign}** was sent to the staff. You will get a DM once it is reviewed.",
            ephemeral=True,
        )

    async def decide_application(self, interaction: discord.Interaction, message_id: int, action: str):
        if interaction.guild is None:
            return
        member = await self.staff_member(interaction)
        if member is None or not await self.is_staff(member):
            return await interaction.response.send_message("❌ Staff only.", ephemeral=True)

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM smp_applications WHERE guild_id = ? AND message_id = ?",
                (interaction.guild.id, message_id),
            ) as cursor:
                row = await cursor.fetchone()

        if row is None:
            return await interaction.response.send_message("❌ Application not found in the database.", ephemeral=True)

        status = row["status"]
        if action != "added" and status != "pending":
            return await interaction.response.send_message(f"ℹ️ This application is already **{status}**.", ephemeral=True)
        if action == "added" and status != "approved":
            return await interaction.response.send_message("⚠️ Approve the application first.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE smp_applications SET status = ?, decided_at = ?, decided_by = ? WHERE id = ?",
                (action, now_iso(), interaction.user.id, row["id"]),
            )
            await db.commit()

        ign = row["ign"]
        if action == "approved":
            note = await self.apply_member_role(interaction.guild, row["user_id"])
            await self.notify_user(
                interaction.guild,
                row["user_id"],
                f"✅ Your application for **{ign}** was **approved**!\n"
                f"A staff member will whitelist you in-game shortly.\n"
                f"{note}".strip(),
            )
            await audit(interaction.guild, "Application approved", f"`{ign}` — {interaction.user.mention}", interaction.user.id)
        elif action == "denied":
            await self.notify_user(
                interaction.guild,
                row["user_id"],
                f"❌ Your application for **{ign}** was **denied**.\nYou can apply again later.",
            )
            await audit(interaction.guild, "Application denied", f"`{ign}` — {interaction.user.mention}", interaction.user.id)
        else:
            await self.notify_user(
                interaction.guild,
                row["user_id"],
                f"🔴 You are now whitelisted on the SMP as **{ign}**. See you in-game!",
            )
            await audit(interaction.guild, "Whitelisted", f"`{ign}` — {interaction.user.mention}", interaction.user.id)

        # refresh the review card
        try:
            base = interaction.message.embeds[0].copy() if interaction.message.embeds else discord.Embed()
            base.color = COLOR_GREEN if action in ("approved", "added") else COLOR_RED
            base.add_field(name="Status", value=f"**{action.upper()}** by {interaction.user.mention}", inline=False)
            if action == "approved":
                base.add_field(name="Server command", value=f"```\nwhitelist add {ign}\n```", inline=False)
            await interaction.message.edit(embed=base)
        except (discord.Forbidden, discord.HTTPException):
            pass

        await interaction.followup.send(f"✅ Application for `{ign}` → **{action}**.", ephemeral=True)

    # ── link flow ──────────────────────────────────────────────────────────
    async def create_link_request(self, interaction: discord.Interaction, ign: str, platform: str):
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild
        config = await get_config(guild.id)
        if not config or not config.get("host"):
            return await interaction.followup.send(
                "❌ SMP is not configured yet. Ask staff to run `/smp setup`.", ephemeral=True
            )
        review_id = config.get("review_channel_id") or config.get("apply_channel_id")
        if not IGN_PATTERN.match(ign):
            return await interaction.followup.send("❌ That is not a valid Minecraft username.", ephemeral=True)

        platform = "bedrock" if platform.lower().startswith("b") else "java"
        ign_uuid = offline_uuid(ign)

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM smp_links WHERE guild_id = ? AND user_id = ?", (guild.id, interaction.user.id)
            ) as cursor:
                current = await cursor.fetchone()
            async with db.execute(
                "SELECT user_id FROM smp_links WHERE guild_id = ? AND lower(ign) = lower(?) "
                "AND status = 'approved' AND user_id <> ?",
                (guild.id, ign, interaction.user.id),
            ) as cursor:
                taken = await cursor.fetchone()

        if taken:
            return await interaction.followup.send(
                f"❌ `{ign}` is already linked to another Discord account.", ephemeral=True
            )
        if current and current["status"] == "pending":
            return await interaction.followup.send("⏳ Your link request is already waiting for staff.", ephemeral=True)
        if current and current["status"] == "approved" and current["ign"].lower() == ign.lower():
            return await interaction.followup.send(f"ℹ️ Your account is already linked to `{ign}`.", ephemeral=True)
        if current and current["status"] == "approved":
            decided = parse_iso(current["decided_at"])
            if decided and datetime.now(timezone.utc) - decided < RELINK_COOLDOWN:
                days = (RELINK_COOLDOWN - (datetime.now(timezone.utc) - decided)).days + 1
                return await interaction.followup.send(
                    f"⏳ You can only change your linked IGN once every 14 days ({days} day(s) left).", ephemeral=True
                )

        embed = discord.Embed(title="🔗 SMP Account Link", color=COLOR_RED)
        embed.add_field(name="Discord", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
        embed.add_field(name="IGN", value=f"`{ign}`", inline=True)
        embed.add_field(name="Platform", value=platform, inline=True)
        embed.add_field(name="Offline UUID", value=f"`{ign_uuid}`", inline=False)
        embed.set_thumbnail(url=avatar_url(ign))
        embed.set_footer(text="Check the player is really this person in-game before approving")
        embed.timestamp = datetime.now(timezone.utc)

        try:
            if review_id:
                review_channel = guild.get_channel(review_id) or await guild.fetch_channel(review_id)
            else:
                # No review channel configured: keep the request in the channel
                # the member used so staff can still approve it.
                review_channel = interaction.channel
            message = await review_channel.send(embed=embed, view=LinkReviewView(self))
        except (discord.Forbidden, discord.HTTPException, AttributeError):
            return await interaction.followup.send(
                "❌ I cannot post the link request here. Staff: add **review_channel** to `/smp setup`.",
                ephemeral=True,
            )

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO smp_links (guild_id, user_id, ign, uuid, platform, status, message_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, 'pending', ?, ?) "
                "ON CONFLICT(guild_id, user_id) DO UPDATE SET ign=excluded.ign, uuid=excluded.uuid, "
                "platform=excluded.platform, status='pending', message_id=excluded.message_id, "
                "created_at=excluded.created_at, decided_at=NULL, decided_by=NULL",
                (guild.id, interaction.user.id, ign, ign_uuid, platform, message.id, now_iso()),
            )
            await db.commit()

        await audit(guild, "Link requested", f"{interaction.user.mention} → `{ign}`", interaction.user.id)
        await interaction.followup.send(
            f"🔗 Link request for **{ign}** sent to the staff for approval.", ephemeral=True
        )

    async def decide_link(self, interaction: discord.Interaction, message_id: int, decision: str):
        if interaction.guild is None:
            return
        member = await self.staff_member(interaction)
        if member is None or not await self.is_staff(member):
            return await interaction.response.send_message("❌ Staff only.", ephemeral=True)

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM smp_links WHERE guild_id = ? AND message_id = ?",
                (interaction.guild.id, message_id),
            ) as cursor:
                row = await cursor.fetchone()

        if row is None:
            return await interaction.response.send_message("❌ Link request not found.", ephemeral=True)
        if row["status"] != "pending":
            return await interaction.response.send_message(f"ℹ️ This request is already **{row['status']}**.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        ign = row["ign"]

        if decision == "approved":
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT user_id FROM smp_links WHERE guild_id = ? AND lower(ign) = lower(?) "
                    "AND status = 'approved' AND user_id <> ?",
                    (interaction.guild.id, ign, row["user_id"]),
                ) as cursor:
                    taken = await cursor.fetchone()
            if taken:
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        "UPDATE smp_links SET status = 'rejected', decided_at = ?, decided_by = ? WHERE guild_id = ? AND user_id = ?",
                        (now_iso(), interaction.user.id, interaction.guild.id, row["user_id"]),
                    )
                    await db.commit()
                await interaction.followup.send(f"❌ `{ign}` is already linked to another member.", ephemeral=True)
                return

            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE smp_links SET status = 'approved', decided_at = ?, decided_by = ? WHERE guild_id = ? AND user_id = ?",
                    (now_iso(), interaction.user.id, interaction.guild.id, row["user_id"]),
                )
                await db.commit()

            note = await self.apply_member_role(interaction.guild, row["user_id"])
            member = interaction.guild.get_member(row["user_id"])
            if member is not None:
                try:
                    await member.edit(nick=ign[:32])
                except (discord.Forbidden, discord.HTTPException):
                    pass
            await self.notify_user(
                interaction.guild,
                row["user_id"],
                f"✅ Your Discord account is now linked to **{ign}**.{chr(10) + note if note else ''}",
            )
            await audit(interaction.guild, "Link approved", f"`{ign}` — <@{row['user_id']}> by {interaction.user.mention}", interaction.user.id)
        else:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE smp_links SET status = 'rejected', decided_at = ?, decided_by = ? WHERE guild_id = ? AND user_id = ?",
                    (now_iso(), interaction.user.id, interaction.guild.id, row["user_id"]),
                )
                await db.commit()
            await self.notify_user(
                interaction.guild, row["user_id"], f"❌ Your link request for **{ign}** was rejected."
            )
            await audit(interaction.guild, "Link rejected", f"`{ign}` — <@{row['user_id']}> by {interaction.user.mention}", interaction.user.id)

        try:
            base = interaction.message.embeds[0].copy() if interaction.message.embeds else discord.Embed()
            base.color = COLOR_GREEN if decision == "approved" else COLOR_RED
            base.add_field(name="Status", value=f"**{decision.upper()}** by {interaction.user.mention}", inline=False)
            await interaction.message.edit(embed=base)
        except (discord.Forbidden, discord.HTTPException):
            pass

        await interaction.followup.send(f"✅ Link for `{ign}` → **{decision}**.", ephemeral=True)

    # ── user commands ──────────────────────────────────────────────────────
    @commands.hybrid_command(name="apply", description="Apply to join the SMP.")
    @commands.guild_only()
    async def apply_cmd(self, ctx: commands.Context):
        if ctx.interaction is None:
            return await ctx.send("❌ Applications must be sent with the slash command `/apply`.")
        await ctx.interaction.response.send_modal(ApplyModal(self, ctx.interaction))

    @commands.hybrid_command(name="link", description="Link your Discord account to your Minecraft username.")
    @app_commands.describe(ign="Your Minecraft username", platform="java or bedrock")
    @commands.guild_only()
    async def link_cmd(self, ctx: commands.Context, ign: str, platform: str = "java"):
        if ctx.interaction is None:
            return await ctx.send("❌ Please use the slash command `/link <ign>`.")
        await self.create_link_request(ctx.interaction, ign.strip(), platform)

    @commands.hybrid_group(name="smp", invoke_without_command=True, description="SMP panel and settings.")
    @commands.guild_only()
    async def smp(self, ctx: commands.Context):
        config = await get_config(ctx.guild.id)
        if not config:
            return await ctx.send("❌ Not configured. Staff: `/smp setup host:<ip>`")
        await ctx.send(
            embed=discord.Embed(
                title="🎮 SMP",
                description=(
                    f"**Server:** `{config['host']}`\n"
                    "**Apply:** `/apply`\n**Link:** `/link <ign>`\n\n"
                    "Staff: `/smp status`, `/smp pending`, `/smp setup`"
                ),
                color=COLOR_RED,
            )
        )

    @smp.command(name="setup", description="Configure the SMP module (staff).")
    @app_commands.describe(
        host="Server address, e.g. play.bonbonsmp.xyz",
        port="Port (leave empty when the server uses an SRV record)",
        apply_channel="Channel where members should apply",
        review_channel="Channel where staff review applications",
        audit_channel="Channel for the audit log",
        member_role="Role given after approval",
        staff_role="Role allowed to review applications",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def smp_setup(
        self,
        ctx: commands.Context,
        host: str,
        port: int = 0,
        apply_channel: discord.TextChannel = None,
        review_channel: discord.TextChannel = None,
        audit_channel: discord.TextChannel = None,
        member_role: discord.Role = None,
        staff_role: discord.Role = None,
    ):
        fields = {"host": host.strip().lower(), "port": int(port or 0)}
        if apply_channel:
            fields["apply_channel_id"] = apply_channel.id
        if review_channel:
            fields["review_channel_id"] = review_channel.id
        if audit_channel:
            fields["audit_channel_id"] = audit_channel.id
        if member_role:
            fields["member_role_id"] = member_role.id
        if staff_role:
            fields["staff_role_id"] = staff_role.id

        await save_config(ctx.guild.id, **fields)
        await audit(ctx.guild, "Setup updated", ", ".join(f"{k}={v}" for k, v in fields.items()), ctx.author.id)

        status = await fetch_status(fields["host"], fields.get("port") or None)
        reachable = "🟢 reachable" if status and status.get("online") else "🔴 not reachable"
        await ctx.send(
            embed=discord.Embed(
                title="✅ SMP configured",
                description=f"**Host:** `{fields['host']}`\n**Status:** {reachable}",
                color=COLOR_RED,
            )
        )

    @smp.command(name="status", description="Show the live server status.")
    async def smp_status(self, ctx: commands.Context):
        config = await get_config(ctx.guild.id)
        if not config:
            return await ctx.send("❌ Not configured. Staff: `/smp setup host:<ip>`")
        await ctx.defer()
        status = await fetch_status(config["host"], config.get("port") or None)
        if not status or not status.get("online"):
            return await ctx.send(
                embed=discord.Embed(title="🔴 Offline", description=f"`{config['host']}` did not answer.", color=COLOR_RED)
            )
        embed = discord.Embed(title=f"🟢 {config['host']}", color=COLOR_RED)
        embed.add_field(name="Players", value=f"`{status['players_online']}/{status['players_max']}`", inline=True)
        embed.add_field(name="Version", value=f"`{status['version']}`", inline=True)
        embed.add_field(name="MOTD", value=status["motd"][:200] or "—", inline=False)
        if status.get("favicon"):
            embed.set_thumbnail(url=status["favicon"])
        embed.timestamp = datetime.now(timezone.utc)
        await ctx.send(embed=embed)

    @smp.command(name="mylink", description="Show the Minecraft account linked to you.")
    async def smp_mylink(self, ctx: commands.Context):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT ign, uuid, platform, status FROM smp_links WHERE guild_id = ? AND user_id = ?",
                (ctx.guild.id, ctx.author.id),
            ) as cursor:
                row = await cursor.fetchone()
            async with db.execute(
                "SELECT ign, status FROM smp_applications WHERE guild_id = ? AND user_id = ? ORDER BY id DESC LIMIT 1",
                (ctx.guild.id, ctx.author.id),
            ) as cursor:
                app_row = await cursor.fetchone()

        if row is None and app_row is None:
            return await ctx.send("ℹ️ You have no linked account. Use `/link <ign>`.")
        embed = discord.Embed(title="🔗 Your SMP profile", color=COLOR_RED)
        if row:
            embed.add_field(name="IGN", value=f"`{row['ign']}` ({row['platform']})", inline=True)
            embed.add_field(name="Link status", value=row["status"], inline=True)
            embed.set_thumbnail(url=avatar_url(row["ign"]))
        if app_row:
            embed.add_field(name="Last application", value=f"`{app_row['ign']}` → {app_row['status']}", inline=False)
        await ctx.send(embed=embed)

    @smp.command(name="pending", description="List pending applications and links (staff).")
    async def smp_pending(self, ctx: commands.Context):
        if not await self.is_staff(ctx.author):
            return await ctx.send("❌ Staff only.")
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT user_id, ign, platform, created_at FROM smp_applications "
                "WHERE guild_id = ? AND status = 'pending' ORDER BY id ASC",
                (ctx.guild.id,),
            ) as cursor:
                apps = await cursor.fetchall()
            async with db.execute(
                "SELECT user_id, ign, platform, created_at FROM smp_links "
                "WHERE guild_id = ? AND status = 'pending' ORDER BY created_at ASC",
                (ctx.guild.id,),
            ) as cursor:
                links = await cursor.fetchall()

        embed = discord.Embed(title="⏳ Pending SMP requests", color=COLOR_RED)
        embed.add_field(
            name=f"Applications ({len(apps)})",
            value="\n".join(f"• <@{r['user_id']}> → `{r['ign']}`" for r in apps[:10]) or "—",
            inline=False,
        )
        embed.add_field(
            name=f"Links ({len(links)})",
            value="\n".join(f"• <@{r['user_id']}> → `{r['ign']}`" for r in links[:10]) or "—",
            inline=False,
        )
        await ctx.send(embed=embed)

    @smp.command(name="whois", description="Show the SMP data of a member (staff).")
    @app_commands.describe(member="Member to look up")
    async def smp_whois(self, ctx: commands.Context, member: discord.Member):
        if not await self.is_staff(ctx.author):
            return await ctx.send("❌ Staff only.")
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT ign, uuid, platform, status, decided_at FROM smp_links WHERE guild_id = ? AND user_id = ?",
                (ctx.guild.id, member.id),
            ) as cursor:
                link = await cursor.fetchone()
            async with db.execute(
                "SELECT ign, status, created_at FROM smp_applications WHERE guild_id = ? AND user_id = ? ORDER BY id DESC LIMIT 3",
                (ctx.guild.id, member.id),
            ) as cursor:
                apps = await cursor.fetchall()

        embed = discord.Embed(title=f"🔎 {member}", color=COLOR_RED)
        if link:
            embed.add_field(name="IGN", value=f"`{link['ign']}` ({link['platform']})", inline=True)
            embed.add_field(name="Status", value=link["status"], inline=True)
            embed.add_field(name="UUID", value=f"`{link['uuid']}`", inline=False)
        else:
            embed.add_field(name="Link", value="not linked", inline=False)
        if apps:
            embed.add_field(
                name="Applications",
                value="\n".join(f"• `{a['ign']}` → {a['status']}" for a in apps),
                inline=False,
            )
        await ctx.send(embed=embed)

    @smp.command(name="whitelistcmd", description="Print the whitelist command for an IGN (staff).")
    @app_commands.describe(ign="Minecraft username")
    async def smp_whitelistcmd(self, ctx: commands.Context, ign: str):
        if not await self.is_staff(ctx.author):
            return await ctx.send("❌ Staff only.")
        if not IGN_PATTERN.match(ign):
            return await ctx.send("❌ Invalid username.")
        await ctx.send(
            embed=discord.Embed(
                title="Server console command",
                description=f"```\nwhitelist add {ign}\n```\nOffline UUID: `{offline_uuid(ign)}`",
                color=COLOR_RED,
            )
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(SMP(bot))
