#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path

import auto_sync


PROJECT = Path.home() / "SeedDMS-Sync"
CONFIG = PROJECT / "config.json"
AUTHORIZATION = PROJECT / "production_authorization.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()

    if not args.preflight:
        raise SystemExit(
            "SAFETY STOP: Only --preflight is implemented."
        )

    sync = auto_sync.load_sync_module()
    config = sync.load_config(CONFIG)
    authorization = json.loads(AUTHORIZATION.read_text())

    if config["dry_run"] is not True:
        raise RuntimeError("SAFETY STOP: Dry-run required")

    if config["allow_overwrite"] is not False:
        raise RuntimeError("SAFETY STOP: Overwrite prohibited")

    if config["delete_remote_files"] is not False:
        raise RuntimeError("SAFETY STOP: Deletion prohibited")

    if authorization["execution_enabled"] is not False:
        raise RuntimeError("SAFETY STOP: Execution must remain disabled")

    if authorization["approved_for_upload"] is not False:
        raise RuntimeError("SAFETY STOP: Upload approval must remain disabled")

    relative = Path(authorization["relative_path"])

    if relative != Path("Document_Open_Test.txt"):
        raise RuntimeError("SAFETY STOP: Unexpected document")

    source_root = Path(config["source_directory"]).resolve(strict=True)
    source = source_root / relative

    if source.is_symlink() or not source.is_file():
        raise RuntimeError("SAFETY STOP: Invalid source")

    if sync.excluded(source, relative, config):
        raise RuntimeError("SAFETY STOP: Document excluded")

    checksum = sync.calculate_sha256(source)
    size = source.stat().st_size

    if checksum != authorization["expected_sha256"]:
        raise RuntimeError("SAFETY STOP: SHA-256 mismatch")

    if size != authorization["expected_size"]:
        raise RuntimeError("SAFETY STOP: File size mismatch")

    database = Path(config["database"]).resolve(strict=True)

    conn = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")

    session = sync.make_session(config)

    try:
        status = auto_sync.classify_file(
            sync, config, session, conn, source, relative
        )

        print("===== PRODUCTION PREFLIGHT =====")
        print("Document:", relative)
        print("Classification:", status)
        print("SHA-256:", checksum)
        print("Size:", size)
        print()
        print("Upload performed: NO")
        print("SQLite modified: NO")
        print("Production execution enabled: NO")

        if status != "NEW":
            raise RuntimeError(
                "SAFETY STOP: Expected NEW classification; got " + status
            )

        print("PASS: Document eligible for supervised NEW upload")

    finally:
        session.close()
        conn.close()


if __name__ == "__main__":
    main()
