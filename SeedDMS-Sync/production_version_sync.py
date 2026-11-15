#!/usr/bin/env python3
"""Read-only production document version-change detector."""

import hashlib
import sqlite3
from collections import Counter
from pathlib import Path

import auto_sync

PROJECT = Path.home() / "SeedDMS-Sync"


def checksum(path):
    digest = hashlib.sha256()
    size = 0

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1048576), b""):
            digest.update(chunk)
            size += len(chunk)

    return digest.hexdigest(), size


def remote_checksum(session, url):
    digest = hashlib.sha256()
    size = 0

    with session.get(
        url,
        stream=True,
        timeout=(10, 120),
        allow_redirects=False
    ) as response:
        if response.status_code != 200:
            raise RuntimeError(
                f"Remote GET returned HTTP {response.status_code}"
            )

        for chunk in response.iter_content(1048576):
            if chunk:
                digest.update(chunk)
                size += len(chunk)

    return digest.hexdigest(), size


def main():
    sync = auto_sync.load_sync_module()
    config = sync.load_config(PROJECT / "config.json")

    if (
        config["dry_run"] is not True
        or config["allow_overwrite"] is not False
        or config["delete_remote_files"] is not False
    ):
        raise RuntimeError("SAFETY STOP: Unsafe configuration")

    root = Path(config["source_directory"]).resolve(strict=True)
    database = Path(config["database"]).resolve(strict=True)

    conn = sqlite3.connect(
        database.as_uri() + "?mode=ro",
        uri=True
    )
    conn.execute("PRAGMA query_only=ON")

    session = sync.make_session(config)
    counts = Counter()

    try:
        records = conn.execute("""
            SELECT path, sha256, size, status
            FROM processed_files
            ORDER BY path
        """).fetchall()

        print("===== PRODUCTION VERSION DETECTION =====")

        for relative, old_hash, old_size, status in records:
            path = root / relative

            if not path.is_file() or path.is_symlink():
                counts["MISSING_LOCAL"] += 1
                print("[MISSING_LOCAL]", relative)
                continue

            if sync.excluded(path, Path(relative), config):
                counts["EXCLUDED"] += 1
                continue

            if status != "done":
                counts["CONFLICT"] += 1
                print("[CONFLICT: TRACKING]", relative)
                continue

            local = checksum(path)
            baseline = (old_hash, old_size)

            if local == baseline:
                counts["UNCHANGED"] += 1
                continue

            url = sync.remote_url(config, Path(relative))

            if not sync.remote_exists(session, url):
                counts["MISSING_REMOTE"] += 1
                print("[MISSING_REMOTE]", relative)
                continue

            remote = remote_checksum(session, url)

            if remote == baseline:
                counts["MODIFIED"] += 1
                print("[MODIFIED]", relative)

            elif remote == local:
                counts["RECOVERY"] += 1
                print("[RECOVERY]", relative)

            else:
                counts["CONFLICT"] += 1
                print("[CONFLICT: REMOTE CHANGED]", relative)

        print()
        print("===== VERSION DETECTION SUMMARY =====")

        for category in (
            "UNCHANGED",
            "MODIFIED",
            "RECOVERY",
            "CONFLICT",
            "MISSING_LOCAL",
            "MISSING_REMOTE",
            "EXCLUDED"
        ):
            print(f"{category}: {counts[category]}")

        print()
        print("Production uploads: NONE")
        print("Remote deletions: NONE")
        print("SQLite modifications: NONE")

    finally:
        session.close()
        conn.close()


if __name__ == "__main__":
    main()
