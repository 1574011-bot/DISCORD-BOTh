# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   UND — All In One                                               ║
# ║                                                                  ║
# ║                                                                  ║
# ║   © 2026 KURAPIKA — All Rights Reserved                          ║
# ║   Built & owned by Kurapika                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

"""Local storage for client files.

Layout:
    clients/<guild_id>/<slug>/orchard.jar
    clients/<guild_id>/<slug>/meta.json

Drop a file inside a folder (a `meta.json` is optional — it is created on
the first scan), run `/client scan`, and it shows up on the panel.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

BASE_DIR = Path("clients")
META_NAME = "meta.json"
ALLOWED_SUFFIXES = {".jar", ".zip", ".mrpack", ".rar", ".7z", ".exe"}
# Discord's default per-file limit for bots is 20 MiB.
MAX_BYTES = 20 * 1024 * 1024


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "-", (name or "").strip().lower()).strip("-")
    return slug[:48] or "client"


def guild_dir(guild_id: int | str) -> Path:
    return BASE_DIR / str(guild_id)


def client_dir(guild_id: int | str, slug: str) -> Path:
    base = guild_dir(guild_id).resolve()
    directory = (base / slugify(slug)).resolve()
    if directory.parent != base:
        raise ValueError("Invalid client path")
    return directory


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(BASE_DIR.resolve()))


def human_size(size: int | None) -> str:
    value = float(size or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} B" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def clean_filename(filename: str) -> str:
    """Strip directories and unsafe characters from a user supplied name."""
    name = Path(str(filename or "")).name
    name = re.sub(r"[^A-Za-z0-9._ ()-]+", "_", name).strip(" .")
    suffix = Path(name).suffix.lower()
    if not name or suffix not in ALLOWED_SUFFIXES:
        raise ValueError(f"Unsupported file type `{suffix or 'unknown'}`")
    if len(name) > 120:
        name = name[: 120 - len(suffix)] + suffix
    return name


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_meta(directory: Path) -> dict:
    meta_file = directory / META_NAME
    if not meta_file.exists():
        return {}
    try:
        data = json.loads(meta_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def write_meta(directory: Path, data: dict) -> None:
    """Persist known keys and keep any extra keys the owner added by hand."""
    directory.mkdir(parents=True, exist_ok=True)
    merged = dict(read_meta(directory))
    for key in ("name", "slug", "version", "emoji", "notes", "file_name", "size", "sha256"):
        if key in data:
            merged[key] = data[key]
    merged.pop("oversized", None)
    (directory / META_NAME).write_text(
        json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def find_file(directory: Path, preferred: str | None = None) -> Path | None:
    if preferred:
        candidate = directory / Path(str(preferred)).name
        if candidate.is_file() and not candidate.is_symlink():
            return candidate
    for path in sorted(directory.iterdir()):
        if path.is_file() and not path.is_symlink() and path.suffix.lower() in ALLOWED_SUFFIXES:
            return path
    return None


def save_upload(guild_id, name: str, filename: str, data: bytes, **extra) -> dict:
    """Write an uploaded file into the clients folder and return its metadata."""
    filename = clean_filename(filename)
    if len(data) > MAX_BYTES:
        raise ValueError(f"File is too big ({human_size(len(data))} > {human_size(MAX_BYTES)})")

    slug = slugify(name)
    directory = client_dir(guild_id, slug)
    directory.mkdir(parents=True, exist_ok=True)

    # A replaced file must not stay behind next to the new one.
    for stale in directory.iterdir():
        if (
            stale.is_file()
            and stale.name not in (filename, META_NAME)
            and stale.suffix.lower() in ALLOWED_SUFFIXES
        ):
            stale.unlink(missing_ok=True)

    target = directory / filename
    target.write_bytes(data)

    meta = {
        "name": name.strip(),
        "slug": slug,
        "version": str(extra.get("version") or "").strip(),
        "emoji": str(extra.get("emoji") or "").strip(),
        "notes": str(extra.get("notes") or "").strip(),
        "file_name": filename,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    write_meta(directory, meta)
    return {**meta, "file_path": relative(target)}


def scan(guild_id) -> list[dict]:
    """Return every client found in the guild folder, creating meta when missing."""
    base = guild_dir(guild_id)
    if not base.exists():
        return []

    found = []
    for directory in sorted(path for path in base.iterdir() if path.is_dir() and not path.is_symlink()):
        meta = read_meta(directory)
        file_path = find_file(directory, meta.get("file_name"))
        if file_path is None:
            continue

        slug = directory.name
        size = file_path.stat().st_size
        meta.update({
            "slug": slug,
            "name": meta.get("name") or slug.replace("-", " ").title(),
            "file_name": file_path.name,
            "size": size,
            "sha256": meta.get("sha256") or sha256_file(file_path),
            "file_path": relative(file_path),
            "oversized": size > MAX_BYTES,
        })
        write_meta(directory, meta)
        found.append(meta)
    return found


def delete_client(guild_id, slug: str) -> bool:
    directory = client_dir(guild_id, slug)
    if not directory.exists():
        return False
    shutil.rmtree(directory)
    return True


# ── delivery limits & splitting ──────────────────────────────────────────────
# Discord raised the default bot limit to 20 MiB (Sept 2026). discord.py's
# `guild.filesize_limit` still uses the old 10 MiB table for tiers 0/1, so it
# must never be trusted for a decision.
MIB = 1024 * 1024
TIER_LIMITS = {0: 20 * MIB, 1: 20 * MIB, 2: 50 * MIB, 3: 100 * MIB}
MAX_PARTS = 40


def delivery_limit(interaction=None, guild=None) -> int:
    """The real per-file cap Discord reports for this interaction/guild."""
    limit = getattr(interaction, "attachment_size_limit", None)
    if limit:
        return int(limit)
    target = guild if guild is not None else getattr(interaction, "guild", None)
    tier = int(getattr(target, "premium_tier", 0) or 0)
    return TIER_LIMITS.get(tier, 20 * MIB)


def make_parts(path: Path, limit: int):
    """Split a file into <=limit byte parts. Returns (temp_dir, [parts])."""
    import tempfile

    directory = Path(tempfile.mkdtemp(prefix="und-parts-"))
    parts = []
    with open(path, "rb") as source:
        index = 1
        while True:
            chunk = source.read(limit)
            if not chunk:
                break
            part = directory / f"{path.name}.part{index:03d}"
            part.write_bytes(chunk)
            parts.append(part)
            index += 1
    return directory, parts


def write_merge_helpers(directory: Path, parts, original: str, sha: str) -> list[Path]:
    """merge.bat (Windows) + MERGE-INSTRUCTIONS.txt (all platforms)."""
    joined = "+".join(f'"{part.name}"' for part in parts)
    bat = directory / "merge.bat"
    bat.write_text(
        "@echo off\r\n"
        f'copy /b {joined} "{original}"\r\n'
        "echo.\r\n"
        f'echo Merged into {original}\r\n'
        "pause\r\n",
        encoding="utf-8",
    )
    prefix = parts[0].name.rsplit(".part", 1)[0]
    txt = directory / "MERGE-INSTRUCTIONS.txt"
    txt.write_text(
        "How to merge this split client\n"
        "==============================\n\n"
        f"1. Keep all {len(parts)} parts in the same folder.\n"
        "2. Windows: double-click merge.bat\n"
        f'   Linux/macOS: cat "{prefix}".part* > "{original}"\n'
        f"3. The result is {original}\n\n"
        f"SHA-256 of the merged file: {sha}\n",
        encoding="utf-8",
    )
    return [bat, txt]


def cleanup_temp(directory: Path | None) -> None:
    if directory:
        shutil.rmtree(directory, ignore_errors=True)
