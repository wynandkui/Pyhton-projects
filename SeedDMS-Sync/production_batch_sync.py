#!/usr/bin/env python3
"""Resumable SeedDMS production uploader: NEW files only."""

import argparse
import fcntl
import hashlib
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

import auto_sync

PROJECT = Path.home() / "SeedDMS-Sync"
SOURCE = Path.home() / "Documents"
DATABASE = PROJECT / "progress.sqlite3"
EXPECTED_HOST = os.environ.get("SEEDDMS_EXPECTED_HOST", "")
DESTINATION = os.environ.get("SEEDDMS_EXPECTED_DESTINATION", "")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_source(path, root):
    if path.is_symlink() or not path.is_file():
        return False
    if not path.resolve(strict=True).is_relative_to(root):
        return False
    current = path.parent
    while current != root:
        if current.is_symlink():
            return False
        current = current.parent
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-new", action="store_true")
    parser.add_argument("--max-files", type=int, default=25)
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()

    if not 1 <= args.max_files <= 543:
        raise SystemExit("SAFETY STOP: Invalid batch limit")

    if args.execute_new and args.confirm != "UPLOAD-NEW-ONLY":
        raise SystemExit("SAFETY STOP: Explicit confirmation required")

    sync = auto_sync.load_sync_module()
    config = sync.load_config(PROJECT / "config.json")

    if (config["dry_run"], config["allow_overwrite"],
            config["delete_remote_files"]) != (True, False, False):
        raise SystemExit("SAFETY STOP: Unsafe configuration")

    root = Path(config["source_directory"]).resolve(strict=True)
    db = Path(config["database"]).resolve(strict=True)
    url_parts = urlsplit(config["webdav_url"])

    if root != SOURCE.resolve() or db != DATABASE.resolve():
        raise SystemExit("SAFETY STOP: Production paths changed")

    if (url_parts.hostname != EXPECTED_HOST
            or unquote(url_parts.path).rstrip("/") + "/" != DESTINATION
            or url_parts.scheme != "https"):
        raise SystemExit("SAFETY STOP: Destination changed")

    lock_path = PROJECT / ".production-batch.lock"
    with lock_path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)

        if args.execute_new:
            conn = sqlite3.connect(db)
        else:
            conn = sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)
            conn.execute("PRAGMA query_only=ON")

        session = sync.make_session(config)
        counts = {
            "NEW": 0, "DONE": 0, "EXCLUDED": 0,
            "BLOCKED": 0, "UPLOADED": 0
        }

        try:
            files = sorted(
                p for p in root.rglob("*") if p.is_file() or p.is_symlink()
            )

            print("===== SEEDDMS PRODUCTION BATCH =====", flush=True)
            print("Mode:", "EXECUTE NEW" if args.execute_new else "PREVIEW")
            print("Maximum uploads:", args.max_files, flush=True)

            for source in files:
                relative = source.relative_to(root)

                if (not safe_source(source, root)
                        or source.name.startswith("~$")
                        or source.name.lower().endswith(
                            (".bak", ".backup", ".tmp", ".part", ".swp")
                        )
                        or sync.excluded(source, relative, config)):
                    counts["EXCLUDED"] += 1
                    continue

                tracked = sync.get_tracked_file(
                    conn, relative.as_posix()
                )

                if tracked is not None:
                    if (tracked[2] == "done"
                            and tracked[0] == sha256(source)
                            and tracked[1] == source.stat().st_size):
                        counts["DONE"] += 1
                    else:
                        counts["BLOCKED"] += 1
                        print("[BLOCKED: TRACKED CHANGE]", relative,
                              flush=True)
                    continue

                url = sync.remote_url(config, relative)

                if sync.remote_exists(session, url):
                    counts["BLOCKED"] += 1
                    print("[BLOCKED: REMOTE EXISTS]", relative,
                          flush=True)
                    continue

                counts["NEW"] += 1

                if not args.execute_new:
                    print("[NEW]", relative, flush=True)
                    continue

                if counts["UPLOADED"] >= args.max_files:
                    print("[LIMIT] Batch limit reached", flush=True)
                    break

                snapshot = None
                try:
                    original_size = source.stat().st_size
                    original_hash = sha256(source)

                    with tempfile.NamedTemporaryFile(
                        prefix="seeddms-batch-", delete=False
                    ) as temporary:
                        snapshot = Path(temporary.name)

                    shutil.copyfile(source, snapshot)

                    if (snapshot.stat().st_size != original_size
                            or sha256(snapshot) != original_hash):
                        raise RuntimeError("Snapshot verification failed")

                    if not sync.verify_source_integrity(
                        source, original_hash, original_size
                    ):
                        raise RuntimeError("Source changed")

                    if sync.get_tracked_file(
                        conn, relative.as_posix()
                    ) is not None:
                        raise RuntimeError("Tracking record appeared")

                    if sync.remote_exists(session, url):
                        raise RuntimeError("Remote document appeared")

                    for depth in range(1, len(relative.parts)):
                        folder = Path(*relative.parts[:depth])
                        folder_url = (
                            sync.remote_url(config, folder).rstrip("/") + "/"
                        )

                        if sync.remote_exists(session, folder_url):
                            continue

                        response = session.request(
                            "MKCOL",
                            folder_url,
                            timeout=20,
                            allow_redirects=False
                        )

                        if response.status_code != 201:
                            raise RuntimeError(
                                "Remote folder creation failed: "
                                + str(folder)
                                + " HTTP "
                                + str(response.status_code)
                            )

                        if not sync.remote_exists(session, folder_url):
                            raise RuntimeError(
                                "Remote folder verification failed: "
                                + str(folder)
                            )

                        print("[FOLDER CREATED]", folder, flush=True)

                    print("[UPLOADING]", relative, flush=True)

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
                            "Uncertain PUT result: HTTP "
                            + str(response.status_code)
                        )

                    digest = hashlib.sha256()
                    remote_size = 0

                    with session.get(
                        url, stream=True, timeout=(10, 120),
                        allow_redirects=False
                    ) as remote:
                        if remote.status_code != 200:
                            raise RuntimeError(
                                "Remote verification failed"
                            )
                        for chunk in remote.iter_content(1048576):
                            if chunk:
                                digest.update(chunk)
                                remote_size += len(chunk)

                    if (digest.hexdigest() != original_hash
                            or remote_size != original_size):
                        raise RuntimeError("Remote checksum mismatch")

                    if not sync.verify_source_integrity(
                        source, original_hash, original_size
                    ):
                        raise RuntimeError("Source changed after PUT")

                    sync.record_uploaded_file(
                        conn, relative.as_posix(),
                        original_hash, original_size
                    )

                    counts["UPLOADED"] += 1
                    print("[VERIFIED]", relative, flush=True)

                except Exception as exc:
                    print("[SAFETY STOP]", relative, str(exc),
                          flush=True)
                    raise
                finally:
                    if snapshot is not None:
                        snapshot.unlink(missing_ok=True)

            print("===== SUMMARY =====")
            for key, value in counts.items():
                print(f"{key}: {value}")

            print("Remote deletions: NONE")
            print("Existing remote files overwritten: NONE")

        finally:
            session.close()
            conn.close()


if __name__ == "__main__":
    main()
