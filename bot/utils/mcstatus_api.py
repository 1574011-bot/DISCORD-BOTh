# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   UND — All In One                                               ║
# ║                                                                  ║
# ║   © 2026 KURAPIKA — All Rights Reserved                          ║
# ║   Built & owned by Kurapika                                      ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

"""Minecraft server status helper.

Servers behind a proxy + SRV record (e.g. play.example.com -> :28417) cannot be
reached by a plain `host:25565` ping, so we ask the public mcstatus.io API first
(it resolves SRV records) and fall back to a local ping in minecraft.py.

The API is cached for a few seconds so a busy panel does not hammer it.
"""

import asyncio
import time

import aiohttp

API_URL = "https://api.mcstatus.io/v2/status/{edition}/{host}"
CACHE_TTL = 45  # seconds
DEFAULT_PORTS = {"java": 25565, "bedrock": 19132}

_cache: dict[tuple, tuple[float, dict]] = {}


def _clean(text: str) -> str:
    return (text or "").replace("\n", " ").strip()


async def fetch_status(host: str, port: int | None = None, edition: str = "java") -> dict | None:
    """Return a normalised status dict, or None when the API could not answer."""
    host = (host or "").strip().lower()
    if not host:
        return None

    key = (host, port, edition)
    now = time.time()
    cached = _cache.get(key)
    if cached and now - cached[0] < CACHE_TTL:
        return cached[1]

    params = {"timeout": "5"}
    if port and int(port) != DEFAULT_PORTS.get(edition, 25565):
        params["port"] = str(int(port))

    data = None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                API_URL.format(edition=edition, host=host),
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        data = None

    if data is None:
        return None

    if not data.get("online"):
        result = {"online": False}
    else:
        players = data.get("players") or {}
        motd = data.get("motd") or {}
        version = data.get("version") or {}

        # Proxies often inject a fake "Players online: x/y" line into the sample
        # list; keep it out of the player names we show.
        names = []
        for entry in players.get("list") or []:
            name = _clean(entry.get("name_clean") or entry.get("name_raw") or "")
            if not name or name.lower().startswith("players online"):
                continue
            names.append(name)

        result = {
            "online": True,
            "motd": _clean((motd.get("clean") or "").split("\n")[0]) or "A Minecraft Server",
            "players_online": players.get("online", 0),
            "players_max": players.get("max", 0),
            "players_sample": names,
            "version": _clean(version.get("name_clean") or version.get("name_raw") or "Unknown"),
            "type": detect_type(version.get("name_clean") or version.get("name_raw")),
            "favicon": data.get("icon"),
        }

    _cache[key] = (now, result)
    return result


def detect_type(version: str | None) -> str:
    version = (version or "").lower()
    if "velocity" in version or "veloflame" in version:
        return "velocity"
    if "bungee" in version:
        return "bungeecord"
    return "java"
