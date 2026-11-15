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
import sqlite3
import time

RUNTIME_DIRS = ("db", "jsondb", "clients", "logs")
# Where the data actually lives once linking ran (None = local, wiped on redeploy).
PERSIST_ROOT: str | None = None


def _volume_root() -> str | None:
    for name in ("DATA_DIR", "RAILWAY_VOLUME_MOUNT_PATH", "VOLUME_MOUNT_PATH"):
        value = (os.getenv(name) or "").strip()
        if value:
            return os.path.abspath(value)
    return None



def _merge_tree(source: str, destination: str) -> None:
    """Move everything from `source` into `destination` without overwriting."""
    os.makedirs(destination, exist_ok=True)
    for entry in os.listdir(source):
        src = os.path.join(source, entry)
        dst = os.path.join(destination, entry)
        if os.path.isdir(src) and not os.path.islink(src):
            if os.path.exists(dst) and not os.path.isdir(dst):
                continue
            _merge_tree(src, dst)
            try:
                os.rmdir(src)
            except OSError:
                pass
        elif os.path.exists(dst):
            # The volume already holds this file — the local copy is ephemeral.
            try:
                if os.path.isdir(src) and not os.path.islink(src):
                    shutil.rmtree(src)
                else:
                    os.remove(src)
            except OSError:
                pass
        else:
            shutil.move(src, dst)


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
                if os.path.ismount(link):
                    print(f"[storage] {name}/ is its own mount — already persistent")
                    continue
                # First run after the switch: keep whatever is still on disk.
                _merge_tree(link, target)
                try:
                    os.rmdir(link)
                except OSError as exc:
                    # Duplicates the merge could not drop (open files, race, …).
                    leftover = os.listdir(link)
                    print(f"[storage] {name}/ not empty after merge ({exc}); clearing {leftover[:5]}")
                    for entry in leftover:
                        path = os.path.join(link, entry)
                        try:
                            if os.path.isdir(path) and not os.path.islink(path):
                                shutil.rmtree(path)
                            else:
                                os.remove(path)
                        except OSError:
                            pass
                    try:
                        os.rmdir(link)
                    except OSError as final_exc:
                        print(f"[storage] could not replace {name}/ ({final_exc}) — keeping local copy")
                        continue
            elif os.path.exists(link):
                continue

            os.symlink(target, link, target_is_directory=True)
        except OSError as exc:
            print(f"[storage] could not persist {name}/ ({exc})")

    global PERSIST_ROOT
    PERSIST_ROOT = root
    print(f"[storage] persistent data: {root} ({", ".join(RUNTIME_DIRS)})")
    return root


BACKUP_DIRNAME = "db-backup"


def backup_dir() -> str | None:
    return os.path.join(PERSIST_ROOT, BACKUP_DIRNAME) if PERSIST_ROOT else None


def snapshot_databases() -> int:
    """Copy every db/*.db onto the volume (SQLite backup API, safe while open)."""
    destination = backup_dir()
    if not destination:
        return 0
    if not os.path.isdir("db"):
        return 0
    os.makedirs(destination, exist_ok=True)
    copied = 0
    for name in sorted(os.listdir("db")):
        if not name.endswith(".db"):
            continue
        source = os.path.join("db", name)
        if not os.path.isfile(source):
            continue
        target = os.path.join(destination, name)
        try:
            with sqlite3.connect(source, timeout=5) as src, sqlite3.connect(target, timeout=5) as dst:
                src.backup(dst)
            copied += 1
        except sqlite3.Error:
            try:
                shutil.copy2(source, target)
                copied += 1
            except OSError:
                pass
    return copied


def restore_databases() -> int:
    """Fill db/ from the volume snapshot — used when a folder could not be linked."""
    source = backup_dir()
    if not source or not os.path.isdir(source):
        return 0
    os.makedirs("db", exist_ok=True)
    restored = 0
    for name in sorted(os.listdir(source)):
        if not name.endswith(".db"):
            continue
        target = os.path.join("db", name)
        if os.path.exists(target):
            continue
        try:
            shutil.copy2(os.path.join(source, name), target)
            restored += 1
        except OSError:
            pass
    if restored:
        print(f"[storage] restored {restored} database file(s) from {source}")
    return restored
