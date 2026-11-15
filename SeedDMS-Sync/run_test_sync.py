#!/usr/bin/env python3

import argparse
import sqlite3
from pathlib import Path

import auto_sync
import versioning


PROJECT = Path("/home/wynand/SeedDMS-Sync")
TEST_CONFIG = PROJECT / "upload-test/test-config.json"
ALLOWED_FILE = Path("Level_A/Level_B/nested-test.txt")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execute-isolated-test",
        action="store_true"
    )
    args = parser.parse_args()

    if not args.execute_isolated_test:
        raise RuntimeError(
            "SAFETY STOP: Explicit isolated-test flag required"
        )

    sync = auto_sync.load_sync_module()
    config = sync.load_config(TEST_CONFIG)

    sync.validate_upload_environment(config)

    source_root = Path(
        config["source_directory"]
    ).resolve(strict=True)

    source = source_root / ALLOWED_FILE

    if source.is_symlink():
        raise RuntimeError("SAFETY STOP: Symlink prohibited")

    database = Path(config["database"]).resolve()

    conn = sqlite3.connect(database)
    session = sync.make_session(config)

    try:
        status = auto_sync.classify_file(
            sync,
            config,
            session,
            conn,
            source,
            ALLOWED_FILE
        )

        print("===== ISOLATED AUTOMATIC SYNC =====")
        print("File:", ALLOWED_FILE)
        print("Classification:", status)

        if status == "UNCHANGED":
            print("[SKIP] File already synchronised")

        elif status == "RECOVERY":
            print("[RECOVERY] Local and remote content match")
            print("[RECOVERY] Reconciling verified SQLite baseline")

            result = versioning.upload_changed_version_safely(
                sync,
                config,
                session,
                source,
                ALLOWED_FILE,
                conn
            )

            if result != "recovered_or_unchanged":
                raise RuntimeError(
                    "SAFETY STOP: Unexpected recovery result"
                )

            print("[PASS] Recovery completed without upload")

        elif status == "MODIFIED":
            result = versioning.upload_changed_version_safely(
                sync,
                config,
                session,
                source,
                ALLOWED_FILE,
                conn
            )
            print("Result:", result)

        else:
            print("[SAFETY STOP] No upload for classification:", status)

        print()
        print("Production synchronisation: DISABLED")
        print("Remote deletion: DISABLED")

    finally:
        session.close()
        conn.close()


if __name__ == "__main__":
    main()
