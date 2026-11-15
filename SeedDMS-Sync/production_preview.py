#!/usr/bin/env python3

import sqlite3
from collections import Counter
from pathlib import Path

import auto_sync


PROJECT = Path.home() / "SeedDMS-Sync"
CONFIG = PROJECT / "config.json"


def main():
    sync = auto_sync.load_sync_module()
    config = sync.load_config(CONFIG)

    if config["dry_run"] is not True:
        raise RuntimeError("SAFETY STOP: Dry-run required")

    if config["allow_overwrite"] is not False:
        raise RuntimeError("SAFETY STOP: Overwrite prohibited")

    if config["delete_remote_files"] is not False:
        raise RuntimeError("SAFETY STOP: Deletion prohibited")

    source_root = Path(config["source_directory"]).resolve(
        strict=True
    )

    database = Path(config["database"]).resolve(strict=True)

    conn = sqlite3.connect(
        database.as_uri() + "?mode=ro",
        uri=True
    )

    conn.execute("PRAGMA query_only = ON")

    session = sync.make_session(config)
    counts = Counter()

    try:
        files = sorted(
            p for p in source_root.rglob("*")
            if p.is_file()
        )

        print("===== PRODUCTION VERSIONING PREVIEW =====")
        print("Source:", source_root)
        print("Mode: READ ONLY")
        print("Files found:", len(files))
        print()

        for index, path in enumerate(files, 1):
            relative = path.relative_to(source_root)

            try:
                if relative.as_posix() == "99_To_Review/.xml":
                    status = "EXCLUDED"

                elif path.is_symlink():
                    status = "EXCLUDED"

                elif path.name.startswith("~$") or (
                    path.name.lower().endswith(
                        (".bak", ".backup", ".tmp", ".part", ".swp")
                    )
                ):
                    status = "EXCLUDED"

                elif sync.excluded(path, relative, config):
                    status = "EXCLUDED"

                else:
                    status = auto_sync.classify_file(
                        sync,
                        config,
                        session,
                        conn,
                        path,
                        relative
                    )

                counts[status] += 1
                print(f"[{status}] {relative}")

            except Exception as exc:
                counts["ERROR"] += 1
                print(f"[ERROR] {relative}: {exc}")

            if index % 50 == 0:
                print(f"Progress: {index}/{len(files)}")

        print()
        print("===== CLASSIFICATION SUMMARY =====")

        for status in (
            "NEW",
            "MODIFIED",
            "UNCHANGED",
            "RECOVERY",
            "CONFLICT",
            "UNTRACKED",
            "MISSING_REMOTE",
            "EXCLUDED",
            "ERROR"
        ):
            print(f"{status}: {counts[status]}")

        print()
        print("WebDAV uploads: NONE")
        print("Remote deletions: NONE")
        print("SQLite modifications: NONE")
        print("Production synchronisation: DISABLED")

    finally:
        session.close()
        conn.close()


if __name__ == "__main__":
    main()
