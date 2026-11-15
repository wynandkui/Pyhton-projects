import os
import argparse
#!/usr/bin/env python3

import json
import logging
import sqlite3
import hashlib
from collections import Counter
from pathlib import Path
from urllib.parse import quote

import requests
from requests.auth import HTTPBasicAuth


BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"


def load_config(config_path=None):
    selected_config = (
        Path(config_path) if config_path else CONFIG_FILE
    )

    with selected_config.open(encoding="utf-8") as f:
        config = json.load(f)

    if config.get("dry_run") is not True:
        raise RuntimeError(
            "Safety stop: this version supports dry-run only."
        )

    if config.get("allow_overwrite") is not False:
        raise RuntimeError("Overwriting must remain disabled.")

    if config.get("delete_remote_files") is not False:
        raise RuntimeError("Remote deletion must remain disabled.")

    return config


def setup_logging(config):
    logging.basicConfig(
        filename=config["log_file"],
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def open_database(config):
    conn = sqlite3.connect(config["database"])

    conn.execute("""
        CREATE TABLE IF NOT EXISTS processed_files (
            path TEXT PRIMARY KEY,
            sha256 TEXT,
            size INTEGER,
            status TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    return conn



def calculate_sha256(path):
    """Calculate SHA-256 without loading the whole file into memory."""
    digest = hashlib.sha256()

    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()



def verify_source_integrity(path, expected_hash, expected_size):
    """Verify that a source file still matches its initial snapshot."""
    if path.stat().st_size != expected_size:
        raise RuntimeError(
            "Source file size changed during processing"
        )

    actual_hash = calculate_sha256(path)

    if actual_hash != expected_hash:
        raise RuntimeError(
            "Source file content changed during processing"
        )

    return True


def get_tracked_file(conn, relative_path):
    """Return the last recorded upload state."""
    return conn.execute(
        """
        SELECT sha256, size, status
        FROM processed_files
        WHERE path = ?
        """,
        (str(relative_path),)
    ).fetchone()


def record_uploaded_file(conn, relative_path, sha256, size):
    """Record a verified successful upload."""
    conn.execute(
        """
        INSERT INTO processed_files
            (path, sha256, size, status, updated_at)
        VALUES (?, ?, ?, 'done', CURRENT_TIMESTAMP)
        ON CONFLICT(path) DO UPDATE SET
            sha256 = excluded.sha256,
            size = excluded.size,
            status = excluded.status,
            updated_at = CURRENT_TIMESTAMP
        """,
        (str(relative_path), sha256, size)
    )
    conn.commit()


def make_session(config):
    password = Path(
        config["credentials_file"]
    ).read_text(encoding="utf-8").rstrip("\r\n")

    session = requests.Session()
    session.auth = HTTPBasicAuth(
        config["username"], password
    )
    session.verify = config["ca_certificate"]
    session.trust_env = False

    return session


def remote_url(config, relative_path):
    parts = [
        quote(part, safe="")
        for part in relative_path.parts
    ]

    return config["webdav_url"].rstrip("/") + "/" + "/".join(parts)


def remote_exists(session, url):
    response = session.request(
        "PROPFIND",
        url,
        headers={"Depth": "0"},
        timeout=20,
        allow_redirects=False,
    )

    if response.status_code == 207:
        return True

    if response.status_code == 404:
        return False

    raise RuntimeError(
        f"Unexpected WebDAV response: HTTP {response.status_code}"
    )


def excluded(path, relative, config):
    if relative.as_posix() in config.get("excluded_files", []):
        return "excluded file"

    if any(
        part in config["excluded_directories"]
        for part in relative.parts[:-1]
    ):
        return "excluded directory"

    if path.suffix.lower() in config["excluded_extensions"]:
        return "excluded extension"

    if path.stat().st_size > config["maximum_file_size_bytes"]:
        return "oversized file"

    return None



def validate_upload_environment(config):
    """Permit experimental uploads only in the isolated test environment."""
    project = (Path.home() / "SeedDMS-Sync").resolve()
    expected_source = (project / "upload-test/source").resolve()
    expected_database = (
        project / "upload-test/test-progress.sqlite3"
    ).resolve()

    expected_destination = os.environ.get(
        "SEEDDMS_EXPECTED_DESTINATION", ""
    )
    if not expected_destination:
        raise RuntimeError("Expected destination is not configured")

    source = Path(config["source_directory"]).resolve()
    database = Path(config["database"]).resolve()
    destination = config["webdav_url"].rstrip("/") + "/"

    if source != expected_source:
        raise RuntimeError(
            "SAFETY STOP: Upload source is not the isolated test directory."
        )

    if database != expected_database:
        raise RuntimeError(
            "SAFETY STOP: Upload database is not the test database."
        )

    if destination != expected_destination:
        raise RuntimeError(
            "SAFETY STOP: Upload destination is not the test folder."
        )

    if config["allow_overwrite"] is not False:
        raise RuntimeError("SAFETY STOP: Overwriting is prohibited.")

    if config["delete_remote_files"] is not False:
        raise RuntimeError("SAFETY STOP: Remote deletion is prohibited.")

    if config["dry_run"] is not True:
        raise RuntimeError(
            "SAFETY STOP: Dry-run must remain enabled during preparation."
        )

    return True




def ensure_remote_directories(config, session, relative_path):
    """Create missing parent directories in the authorised test folder."""

    validate_upload_environment(config)

    parts = relative_path.parts[:-1]

    for depth in range(1, len(parts) + 1):
        folder = Path(*parts[:depth])
        url = remote_url(config, folder).rstrip("/") + "/"

        if remote_exists(session, url):
            continue

        response = session.request(
            "MKCOL",
            url,
            timeout=20,
            allow_redirects=False
        )

        if response.status_code != 201:
            raise RuntimeError(
                f"Cannot create {folder}: HTTP {response.status_code}"
            )

        if not remote_exists(session, url):
            raise RuntimeError(
                f"Remote folder verification failed: {folder}"
            )

        print(f"[FOLDER CREATED] {folder}")

    return True



def calculate_remote_sha256(config, session, relative_path):
    """Download and hash a file from the isolated SeedDMS test folder."""

    import hashlib

    validate_upload_environment(config)

    url = remote_url(config, relative_path)

    digest = hashlib.sha256()
    total_bytes = 0

    with session.get(
        url,
        stream=True,
        timeout=(10, 120),
        allow_redirects=False
    ) as response:

        if response.status_code != 200:
            raise RuntimeError(
                f"Remote download failed: HTTP {response.status_code}"
            )

        for chunk in response.iter_content(chunk_size=1048576):
            if chunk:
                digest.update(chunk)
                total_bytes += len(chunk)

    return digest.hexdigest(), total_bytes



def verify_remote_upload_target(config, session, relative_path):
    """Reject existing files before a controlled test upload."""

    validate_upload_environment(config)

    relative_path = Path(relative_path)

    if relative_path.is_absolute():
        raise RuntimeError(
            "SAFETY STOP: Absolute remote paths are prohibited."
        )

    if not relative_path.parts or any(
        part in (".", "..") for part in relative_path.parts
    ):
        raise RuntimeError(
            "SAFETY STOP: Invalid relative upload path."
        )

    url = remote_url(config, relative_path)

    if remote_exists(session, url):
        raise RuntimeError(
            f"SAFETY STOP: Remote file already exists: {relative_path}"
        )

    return url



def create_source_snapshot(config, source_path):
    """Create and verify a temporary copy of a test source file."""

    import tempfile
    import shutil

    validate_upload_environment(config)

    source_path = Path(source_path)
    source_root = Path(config["source_directory"]).resolve()

    if source_path.is_symlink():
        raise RuntimeError("SAFETY STOP: Symlink source prohibited.")

    resolved = source_path.resolve(strict=True)

    if not resolved.is_relative_to(source_root):
        raise RuntimeError(
            "SAFETY STOP: Source outside isolated test directory."
        )

    if not resolved.is_file():
        raise RuntimeError("Source is not a regular file.")

    original_size = resolved.stat().st_size
    original_hash = calculate_sha256(resolved)

    with tempfile.NamedTemporaryFile(
        prefix="seeddms-snapshot-",
        suffix=".tmp",
        delete=False
    ) as temporary:
        snapshot = Path(temporary.name)

    try:
        shutil.copyfile(resolved, snapshot)

        snapshot_size = snapshot.stat().st_size
        snapshot_hash = calculate_sha256(snapshot)

        if snapshot_size != original_size:
            raise RuntimeError(
                "SAFETY STOP: Snapshot size mismatch."
            )

        if snapshot_hash != original_hash:
            raise RuntimeError(
                "SAFETY STOP: Snapshot checksum mismatch."
            )

        if not verify_source_integrity(
            resolved,
            original_hash,
            original_size
        ):
            raise RuntimeError(
                "SAFETY STOP: Source changed during snapshot."
            )

        return snapshot, snapshot_hash, snapshot_size

    except BaseException:
        snapshot.unlink(missing_ok=True)
        raise




def recover_verified_upload(config, session, relative_path, conn):
    """Recover tracking for an identical remote test document."""

    validate_upload_environment(config)

    relative_path = Path(relative_path)
    allowed = Path("Level_A/Level_B/nested-test.txt")

    if relative_path != allowed:
        raise RuntimeError(
            "SAFETY STOP: Recovery path not authorised."
        )

    if conn is None:
        raise RuntimeError(
            "SAFETY STOP: Database connection required."
        )

    key = relative_path.as_posix()

    if get_tracked_file(conn, key) is not None:
        raise RuntimeError(
            "SAFETY STOP: Tracking record already exists."
        )

    source_root = Path(config["source_directory"]).resolve()
    source_path = source_root / relative_path

    if source_path.is_symlink():
        raise RuntimeError(
            "SAFETY STOP: Symlink source prohibited."
        )

    resolved = source_path.resolve(strict=True)

    if not resolved.is_relative_to(source_root):
        raise RuntimeError(
            "SAFETY STOP: Source outside test directory."
        )

    snapshot = None

    try:
        snapshot, local_hash, local_size = create_source_snapshot(
            config, resolved
        )

        expected_hash = (
            "a6c51cd53952f658179ccd1a6ddcacfd260"
            "a5d197a0051792321d2904f3fe3c5"
        )

        if local_hash != expected_hash or local_size != 37:
            raise RuntimeError(
                "SAFETY STOP: Unexpected test document content."
            )

        url = remote_url(config, relative_path)

        if not remote_exists(session, url):
            raise RuntimeError(
                "SAFETY STOP: Remote document is missing."
            )

        remote_hash, remote_size = calculate_remote_sha256(
            config, session, relative_path
        )

        if remote_hash != local_hash or remote_size != local_size:
            raise RuntimeError(
                "SAFETY STOP: Remote document differs from source."
            )

        if not verify_source_integrity(
            resolved, local_hash, local_size
        ):
            raise RuntimeError(
                "SAFETY STOP: Source changed during verification."
            )

        if get_tracked_file(conn, key) is not None:
            raise RuntimeError(
                "SAFETY STOP: Tracking record appeared during recovery."
            )

        record_uploaded_file(
            conn, key, local_hash, local_size
        )

        return True

    finally:
        if snapshot is not None:
            snapshot.unlink(missing_ok=True)


def upload_file_safely(config, session, source_path, relative_path, conn):
    """Perform one explicitly invoked, isolated test upload."""

    validate_upload_environment(config)

    if config["dry_run"] is not True:
        raise RuntimeError("SAFETY STOP: Dry-run configuration required.")

    relative_path = Path(relative_path)
    source_path = Path(source_path)

    allowed = Path("Level_A/Level_B/nested-test.txt")

    if relative_path != allowed:
        raise RuntimeError("SAFETY STOP: Test filename not authorised.")

    source_root = Path(config["source_directory"]).resolve(strict=True)

    if source_path.is_symlink():
        raise RuntimeError("SAFETY STOP: Symlink prohibited.")

    expected_source = (source_root / allowed).resolve(strict=True)

    if source_path.resolve(strict=True) != expected_source:
        raise RuntimeError("SAFETY STOP: Source path mismatch.")

    if conn is None:
        raise RuntimeError("SAFETY STOP: Database connection required.")

    if get_tracked_file(conn, relative_path.as_posix()) is not None:
        raise RuntimeError("SAFETY STOP: File already tracked.")

    snapshot = None

    try:
        snapshot, checksum, size = create_source_snapshot(
            config, source_path
        )

        if size != 37 or checksum != (
            "a6c51cd53952f658179ccd1a6ddcacfd260"
            "a5d197a0051792321d2904f3fe3c5"
        ):
            raise RuntimeError("SAFETY STOP: Unexpected test content.")

        url = verify_remote_upload_target(
            config, session, relative_path
        )

        if not verify_source_integrity(
            source_path, checksum, size
        ):
            raise RuntimeError("SAFETY STOP: Source changed.")

        print("[UPLOAD] Sending isolated test document")

        with snapshot.open("rb") as handle:
            response = session.put(
                url,
                data=handle,
                headers={
                    "Content-Type": "application/octet-stream",
                    "If-None-Match": "*"
                },
                timeout=(10, 120),
                allow_redirects=False
            )

        if response.status_code not in (200, 201, 204):
            raise RuntimeError(
                f"PUT failed: HTTP {response.status_code}"
            )

        print(f"[PUT] HTTP {response.status_code}")

        remote_hash, remote_size = calculate_remote_sha256(
            config, session, relative_path
        )

        if remote_hash != checksum or remote_size != size:
            raise RuntimeError(
                "SAFETY STOP: Remote checksum or size mismatch."
            )

        print("[PASS] Remote SHA-256 verified")

        record_uploaded_file(
            conn, relative_path.as_posix(), checksum, size
        )

        print("[PASS] SQLite completion recorded")

        return True

    finally:
        if snapshot is not None:
            snapshot.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(
        description="SeedDMS synchronisation"
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Alternative configuration file"
    )
    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config)

    source = Path(config["source_directory"])

    if not source.is_dir():
        raise RuntimeError("Source directory does not exist.")

    conn = open_database(config)
    session = make_session(config)

    counts = Counter()

    print("===== SEEDDMS SYNCHRONISATION DRY RUN =====")
    print("Source:", source)
    print("Destination:", config["webdav_url"])
    print("Dry run:", config["dry_run"])
    print()

    try:
        files = sorted(
            p for p in source.rglob("*") if p.is_file()
        )

        print("Local files found:", len(files))
        print()

        for index, path in enumerate(files, 1):
            relative = path.relative_to(source)

            reason = excluded(path, relative, config)

            if reason:
                counts["excluded"] += 1
                print(f"[EXCLUDED] {relative} ({reason})")
                continue

            try:
                url = remote_url(config, relative)

                tracked = get_tracked_file(conn, relative)
                exists = remote_exists(session, url)

                if tracked and tracked[2] == "done":
                    current_hash = calculate_sha256(path)

                    if current_hash != tracked[0]:
                        counts["modified"] += 1
                        print(f"[MODIFIED LOCAL] {relative}")

                    elif exists:
                        counts["unchanged"] += 1
                        print(f"[UNCHANGED] {relative}")

                    else:
                        counts["missing_remote"] += 1
                        print(f"[MISSING REMOTE] {relative}")

                elif exists:
                    counts["existing"] += 1
                    print(f"[EXISTS UNTRACKED] {relative}")

                else:
                    counts["pending"] += 1
                    print(f"[WOULD UPLOAD] {relative}")

            except Exception as exc:
                counts["errors"] += 1
                logging.error(
                    "Error checking %s: %s", relative, exc
                )
                print(f"[ERROR] {relative}: {exc}")

            if index % 50 == 0:
                print(f"Progress: {index}/{len(files)}")

        print()
        print("===== DRY-RUN SUMMARY =====")
        print("Total local files:", len(files))
        print("Already existing:", counts["existing"])
        print("Unchanged tracked:", counts["unchanged"])
        print("Modified local:", counts["modified"])
        print("Missing remote:", counts["missing_remote"])
        print("Would upload:", counts["pending"])
        print("Excluded:", counts["excluded"])
        print("Errors:", counts["errors"])
        print("Remote changes made: NONE")

        logging.info(
            "Dry run: total=%s existing=%s pending=%s "
            "excluded=%s errors=%s",
            len(files),
            counts["existing"],
            counts["pending"],
            counts["excluded"],
            counts["errors"],
        )

    finally:
        session.close()
        conn.close()


if __name__ == "__main__":
    main()
