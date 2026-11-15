# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   UND — All In One                                               ║
# ║                                                                  ║
# ║                                                                  ║
# ║   © 2026 KURAPIKA — All Rights Reserved                          ║
# ║   Built & owned by Kurapika                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

"""Keep runtime data on the host's persistent volume.

Every cog opens SQLite files with relative paths (`db/clients.db`, …), so the
data lives wherever the process happens to run. In a container that directory
is thrown away on every redeploy unless a volume is mounted there.

`persist_runtime_dirs()` looks for a volume (DATA_DIR, RAILWAY_VOLUME_MOUNT_PATH
or a `data/` folder on the volume) and points `db/`, `jsondb/` and `clients/`
at it with symlinks, so no cog has to know about paths.
"""

from __future__ import annotations

import os
import shutil

RUNTIME_DIRS = ("db", "jsondb", "clients", "logs")
# Where the data actually lives once linking ran (None = local, wiped on redeploy).
PERSIST_ROOT: str | None = None


def _volume_root() -> str | None:
    for name in ("DATA_DIR", "RAILWAY_VOLUME_MOUNT_PATH", "VOLUME_MOUNT_PATH"):
        value = (os.getenv(name) or "").strip()
        if value:
            return os.path.abspath(value)
    return None


def persist_runtime_dirs(root: str | None = None) -> str | None:
    """Link the runtime folders to `root` and return it (None when not possible)."""
    root = (root or _volume_root() or "").strip()
    if not root:
        print("[storage] no volume configured — data resets on every redeploy")
        return None
    root = os.path.abspath(root)

    try:
        os.makedirs(root, exist_ok=True)
    except OSError as exc:
        print(f"[storage] volume {root} is not usable ({exc}) — keeping local data")
        return None

    here = os.path.abspath(os.getcwd())
    root_real = os.path.realpath(root)
    here_real = os.path.realpath(here)
    if root_real == here_real:
        print(f"[storage] whole app directory is persistent: {root}")
        return root

    for name in RUNTIME_DIRS:
        target = os.path.join(root, name)
        link = os.path.join(here, name)
        try:
            os.makedirs(target, exist_ok=True)

            if os.path.realpath(link) == root_real:
                continue  # the volume is mounted straight on this folder

            if os.path.islink(link):
                if os.path.realpath(link) == os.path.realpath(target):
                    continue
                os.unlink(link)
            elif os.path.isdir(link):
                # First run after the switch: keep whatever is still on disk.
                for entry in os.listdir(link):
                    source = os.path.join(link, entry)
                    destination = os.path.join(target, entry)
                    if not os.path.exists(destination):
                        shutil.move(source, destination)
                os.rmdir(link)
            elif os.path.exists(link):
                continue

            os.symlink(target, link, target_is_directory=True)
        except OSError as exc:
            print(f"[storage] could not persist {name}/ ({exc})")

    global PERSIST_ROOT
    PERSIST_ROOT = root
    print(f"[storage] persistent data: {root} ({", ".join(RUNTIME_DIRS)})")
    return root
