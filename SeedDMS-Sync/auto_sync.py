#!/usr/bin/env python3

import argparse
import importlib.util
import json
import sqlite3
from collections import Counter
from pathlib import Path


PROJECT = Path("/home/wynand/SeedDMS-Sync")

SYNC_FILE = PROJECT / "sync.py"

TEST_CONFIG = PROJECT / "upload-test/test-config.json"


def load_sync_module():
    spec = importlib.util.spec_from_file_location(
        "seeddms_sync", SYNC_FILE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def classify_file(sync, config, session, conn, source, relative):
    tracked = sync.get_tracked_file(
        conn, relative.as_posix()
    )

    local_hash = sync.calculate_sha256(source)
    local_size = source.stat().st_size

    url = sync.remote_url(config, relative)
    exists = sync.remote_exists(session, url)

    if not exists:
        if tracked is None:
            return "NEW"

        return "MISSING_REMOTE"

    remote_hash, remote_size = sync.calculate_remote_sha256(
        config, session, relative
    )

    if tracked is None:
        return "UNTRACKED"

    old_hash, old_size, status = tracked

    if status != "done":
        return "CONFLICT"

    local = (local_hash, local_size)
    remote = (remote_hash, remote_size)
    baseline = (old_hash, old_size)

    if local == baseline and remote == baseline:
        return "UNCHANGED"

    if local != baseline and remote == baseline:
        return "MODIFIED"

    if local != baseline and remote == local:
        return "RECOVERY"

    return "CONFLICT"


def main():
    parser = argparse.ArgumentParser(
        description="SeedDMS automatic synchronisation preview"
    )

    parser.add_argument(
        "--config",
        default=str(TEST_CONFIG)
    )

    args = parser.parse_args()

    config_path = Path(args.config).resolve()

    if config_path != TEST_CONFIG.resolve():
        raise RuntimeError(
            "SAFETY STOP: Only isolated test configuration permitted"
        )

    sync = load_sync_module()
    config = sync.load_config(config_path)

    sync.validate_upload_environment(config)

    source_root = Path(
        config["source_directory"]
    ).resolve(strict=True)

    database = Path(config["database"]).resolve()

    conn = sqlite3.connect(
        database.as_uri() + "?mode=ro",
        uri=True
    )

    session = sync.make_session(config)
    counts = Counter()

    try:
        files = sorted(
            p for p in source_root.rglob("*")
            if p.is_file()
        )

        print("===== SEEDDMS AUTOMATIC SYNC PREVIEW =====")
        print("Source:", source_root)
        print("Destination:", config["webdav_url"])
        print("Files found:", len(files))
        print("Mode: PREVIEW ONLY")
        print()

        for path in files:
            relative = path.relative_to(source_root)

            try:
                if path.is_symlink():
                    status = "EXCLUDED"
                    detail = "symlink"

                elif (
                    path.name.lower().endswith(
                        (".bak", ".backup", ".tmp", ".part", ".swp")
                    )
                    or path.name.startswith("~$")
                ):
                    status = "EXCLUDED"
                    detail = "backup or temporary file"

                else:
                    reason = sync.excluded(
                        path, relative, config
                    )

                    if reason:
                        status = "EXCLUDED"
                        detail = reason

                    else:
                        status = classify_file(
                            sync,
                            config,
                            session,
                            conn,
                            path,
                            relative
                        )
                        detail = ""

                counts[status] += 1

                print(
                    f"[{status}] {relative}"
                    + (f" ({detail})" if detail else "")
                )

            except Exception as exc:
                counts["ERROR"] += 1
                print(f"[ERROR] {relative}: {exc}")

        print()
        print("===== SUMMARY =====")

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
        print("Remote uploads: NONE")
        print("Remote deletions: NONE")
        print("SQLite modifications: NONE")
        print("Production synchronisation: DISABLED")

    finally:
        session.close()
        conn.close()


if __name__ == "__main__":
    main()
