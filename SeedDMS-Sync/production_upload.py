#!/usr/bin/env python3
"""Single-document SeedDMS commissioning uploader."""

import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path

import auto_sync

PROJECT = Path.home() / "SeedDMS-Sync"
EXPECTED_FILE = "Document_Open_Test.txt"
EXPECTED_HASH = (
    "4b4c286b442bf76d62ac6b79576d16b3b38318a94dec7ba11bec213692e2a6ed"
)
EXPECTED_SIZE = 40


def main():
    sync = auto_sync.load_sync_module()
    config = sync.load_config(PROJECT / "config.json")
    auth = json.loads(
        (PROJECT / "production_authorization.json").read_text()
    )

    if not (
        config["dry_run"] is True
        and config["allow_overwrite"] is False
        and config["delete_remote_files"] is False
    ):
        raise RuntimeError("SAFETY STOP: Unsafe configuration")

    if not (
        auth["relative_path"] == EXPECTED_FILE
        and auth["expected_sha256"] == EXPECTED_HASH
        and auth["expected_size"] == EXPECTED_SIZE
        and auth["operation"] == "NEW"
        and auth["execution_enabled"] is True
        and auth["approved_for_upload"] is True
    ):
        raise RuntimeError("SAFETY STOP: Upload not authorised")

    root = Path(config["source_directory"]).resolve(strict=True)
    source = root / EXPECTED_FILE

    if source.is_symlink() or not source.is_file():
        raise RuntimeError("SAFETY STOP: Invalid source")

    if sync.excluded(source, Path(EXPECTED_FILE), config):
        raise RuntimeError("SAFETY STOP: Excluded source")

    if source.stat().st_size != EXPECTED_SIZE:
        raise RuntimeError("SAFETY STOP: Size mismatch")

    if sync.calculate_sha256(source) != EXPECTED_HASH:
        raise RuntimeError("SAFETY STOP: SHA-256 mismatch")

    database = Path(config["database"]).resolve(strict=True)
    conn = sqlite3.connect(database)
    session = sync.make_session(config)
    snapshot = None

    try:
        if sync.get_tracked_file(conn, EXPECTED_FILE) is not None:
            raise RuntimeError("SAFETY STOP: Already tracked")

        url = sync.remote_url(config, Path(EXPECTED_FILE))

        if sync.remote_exists(session, url):
            raise RuntimeError("SAFETY STOP: Remote file already exists")

        with tempfile.NamedTemporaryFile(
            prefix="seeddms-production-",
            delete=False
        ) as temporary:
            snapshot = Path(temporary.name)
            with source.open("rb") as handle:
                data = handle.read()
            temporary.write(data)

        if hashlib.sha256(snapshot.read_bytes()).hexdigest() != EXPECTED_HASH:
            raise RuntimeError("SAFETY STOP: Snapshot mismatch")

        if not sync.verify_source_integrity(
            source, EXPECTED_HASH, EXPECTED_SIZE
        ):
            raise RuntimeError("SAFETY STOP: Source changed")

        if sync.remote_exists(session, url):
            raise RuntimeError("SAFETY STOP: Remote appeared before upload")

        print("[UPLOAD] Sending authorised production test document")

        authorization_path = PROJECT / "production_authorization.json"
        disabled_auth = dict(auth)
        disabled_auth["execution_enabled"] = False
        disabled_auth["approved_for_upload"] = False

        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=PROJECT,
            prefix=".production-auth-",
            delete=False
        ) as temporary_auth:
            json.dump(disabled_auth, temporary_auth, indent=2)
            temporary_auth.write("\n")
            temporary_auth.flush()
            os.fsync(temporary_auth.fileno())
            temporary_auth_path = Path(temporary_auth.name)

        temporary_auth_path.chmod(0o600)
        os.replace(temporary_auth_path, authorization_path)

        print("[SAFETY] Single-use authorisation consumed")

        with snapshot.open("rb") as handle:
            response = session.put(
                url,
                data=handle,
                headers={
                    "Content-Type": "application/octet-stream",
                    "If-None-Match": "*",
                },
                timeout=(10, 120),
                allow_redirects=False,
            )

        if response.status_code not in (200, 201, 204):
            raise RuntimeError(
                "PUT outcome requires investigation: HTTP "
                + str(response.status_code)
            )

        digest = hashlib.sha256()
        size = 0

        with session.get(
            url, stream=True, timeout=(10, 120),
            allow_redirects=False
        ) as remote:
            if remote.status_code != 200:
                raise RuntimeError("SAFETY STOP: Remote verification failed")
            for chunk in remote.iter_content(1048576):
                if chunk:
                    digest.update(chunk)
                    size += len(chunk)

        if digest.hexdigest() != EXPECTED_HASH or size != EXPECTED_SIZE:
            raise RuntimeError("SAFETY STOP: Remote checksum mismatch")

        if not sync.verify_source_integrity(
            source, EXPECTED_HASH, EXPECTED_SIZE
        ):
            raise RuntimeError("SAFETY STOP: Source changed after upload")

        sync.record_uploaded_file(
            conn, EXPECTED_FILE, EXPECTED_HASH, EXPECTED_SIZE
        )

        print("PASS: Remote SHA-256 verified")
        print("PASS: SQLite tracking committed")
        print("PASS: Single-document commissioning upload complete")

    finally:
        if snapshot is not None:
            snapshot.unlink(missing_ok=True)
        session.close()
        conn.close()


if __name__ == "__main__":
    main()
