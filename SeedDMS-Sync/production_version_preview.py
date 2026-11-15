import os
#!/usr/bin/env python3
"""Read-only, resumable SeedDMS production integrity audit."""

import argparse
import fcntl
import hashlib
import sqlite3
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

import auto_sync

PROJECT = Path.home() / "SeedDMS-Sync"
SOURCE = Path.home() / "Documents"
DATABASE = PROJECT / "progress.sqlite3"
CHECKPOINT = PROJECT / "production_audit_checkpoint.sqlite3"
EXPECTED_HOST = os.environ.get("SEEDDMS_EXPECTED_HOST", "")
DESTINATION = os.environ.get("SEEDDMS_EXPECTED_DESTINATION", "")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest(), path.stat().st_size


def sha256_remote(session, url):
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
                f"Remote verification failed: HTTP {response.status_code}"
            )

        for chunk in response.iter_content(1048576):
            if chunk:
                digest.update(chunk)
                size += len(chunk)

    return digest.hexdigest(), size


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


def validate_environment(sync, config):
    if (
        config["dry_run"],
        config["allow_overwrite"],
        config["delete_remote_files"]
    ) != (True, False, False):
        raise RuntimeError("SAFETY STOP: Unsafe configuration")

    root = Path(config["source_directory"]).resolve(strict=True)
    db = Path(config["database"]).resolve(strict=True)
    url = urlsplit(config["webdav_url"])

    if root != SOURCE.resolve() or db != DATABASE.resolve():
        raise RuntimeError("SAFETY STOP: Production paths changed")

    if (
        url.scheme != "https"
        or url.hostname != EXPECTED_HOST
        or url.username is not None
        or url.password is not None
        or url.query
        or url.fragment
        or unquote(url.path).rstrip("/") + "/" != DESTINATION
    ):
        raise RuntimeError("SAFETY STOP: Destination changed")

    return root, db


def start_or_resume(checkpoint, resume):
    if resume:
        row = checkpoint.execute(
            """
            SELECT run_id
            FROM audit_runs
            WHERE status = 'running'
            ORDER BY run_id DESC
            LIMIT 1
            """
        ).fetchone()

        if row is None:
            raise RuntimeError(
                "SAFETY STOP: No interrupted audit to resume"
            )

        return row[0]

    existing = checkpoint.execute(
        "SELECT run_id FROM audit_runs WHERE status = 'running'"
    ).fetchone()

    if existing:
        raise RuntimeError(
            "SAFETY STOP: Incomplete audit exists. "
            "Use --resume or inspect it before starting a new run."
        )

    cursor = checkpoint.execute(
        "INSERT INTO audit_runs(status) VALUES ('running')"
    )
    checkpoint.commit()
    return cursor.lastrowid


def save_result(checkpoint, run_id, relative, local, remote,
                classification, error=None):
    checkpoint.execute(
        """
        INSERT INTO audit_results
        (run_id, path, local_sha256, local_size,
         remote_sha256, remote_size, classification, error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id, path) DO UPDATE SET
            local_sha256=excluded.local_sha256,
            local_size=excluded.local_size,
            remote_sha256=excluded.remote_sha256,
            remote_size=excluded.remote_size,
            classification=excluded.classification,
            verified_at=CURRENT_TIMESTAMP,
            error=excluded.error
        """,
        (
            run_id,
            relative,
            local[0] if local else None,
            local[1] if local else None,
            remote[0] if remote else None,
            remote[1] if remote else None,
            classification,
            error
        )
    )
    checkpoint.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-audit", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    if not args.execute_audit:
        raise SystemExit(
            "SAFETY STOP: Explicit --execute-audit flag required"
        )

    sync = auto_sync.load_sync_module()
    config = sync.load_config(PROJECT / "config.json")
    root, db = validate_environment(sync, config)

    lock_path = PROJECT / ".production-batch.lock"

    with lock_path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)

        production = sqlite3.connect(
            db.as_uri() + "?mode=ro", uri=True
        )
        production.execute("PRAGMA query_only=ON")

        checkpoint = sqlite3.connect(CHECKPOINT)
        checkpoint.execute("PRAGMA foreign_keys=ON")

        session = sync.make_session(config)

        try:
            if checkpoint.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0] != "ok":
                raise RuntimeError(
                    "SAFETY STOP: Checkpoint database integrity failed"
                )

            rows = production.execute(
                """
                SELECT path, sha256, size, status
                FROM processed_files
                ORDER BY path
                """
            ).fetchall()

            run_id = start_or_resume(checkpoint, args.resume)

            print("===== PRODUCTION INTEGRITY AUDIT =====", flush=True)
            print("Audit run:", run_id, flush=True)
            print("Tracked files:", len(rows), flush=True)
            print("Mode: READ ONLY REMOTE", flush=True)
            print("Production SQLite: READ ONLY", flush=True)

            for index, (name, old_hash, old_size, status) in enumerate(
                rows, 1
            ):
                previous = checkpoint.execute(
                    """
                    SELECT classification
                    FROM audit_results
                    WHERE run_id=? AND path=?
                    """,
                    (run_id, name)
                ).fetchone()

                if previous and previous[0] != "ERROR":
                    continue

                relative = Path(name)
                local = None
                remote = None
                classification = "ERROR"
                error = None

                try:
                    if (
                        relative.is_absolute()
                        or not relative.parts
                        or ".." in relative.parts
                        or "\\" in name
                        or name != relative.as_posix()
                    ):
                        classification = "UNSAFE_PATH"

                    else:
                        source = root / relative

                        if not source.exists():
                            classification = "MISSING_LOCAL"

                        elif (
                            not safe_source(source, root)
                            or source.name.startswith("~$")
                            or source.name.lower().endswith(
                                (".bak", ".backup", ".tmp", ".part", ".swp")
                            )
                            or sync.excluded(source, relative, config)
                        ):
                            classification = "EXCLUDED"

                        elif status != "done":
                            classification = "CONFLICT"

                        else:
                            local = sha256_file(source)
                            baseline = (old_hash, old_size)
                            url = sync.remote_url(config, relative)

                            if not sync.remote_exists(session, url):
                                classification = "MISSING_REMOTE"
                            else:
                                remote = sha256_remote(session, url)

                                if local == baseline and remote == baseline:
                                    classification = "UNCHANGED"
                                elif local != baseline and remote == baseline:
                                    classification = "MODIFIED"
                                elif local != baseline and remote == local:
                                    classification = "RECOVERY"
                                else:
                                    classification = "CONFLICT"

                except Exception as exc:
                    classification = "ERROR"
                    error = str(exc)

                save_result(
                    checkpoint, run_id, name,
                    local, remote, classification, error
                )

                print(
                    f"[{index}/{len(rows)}] "
                    f"{classification}: {name}",
                    flush=True
                )

                if classification == "ERROR":
                    raise RuntimeError(
                        f"Audit stopped at {name}: {error}"
                    )

            summary = Counter(dict(checkpoint.execute(
                """
                SELECT classification, COUNT(*)
                FROM audit_results
                WHERE run_id=?
                GROUP BY classification
                """,
                (run_id,)
            ).fetchall()))

            print("\n===== AUDIT SUMMARY =====")
            for category in (
                "UNCHANGED", "MODIFIED", "RECOVERY",
                "CONFLICT", "MISSING_LOCAL",
                "MISSING_REMOTE", "EXCLUDED",
                "UNSAFE_PATH", "ERROR"
            ):
                print(f"{category}: {summary[category]}")

            if sum(summary.values()) != len(rows):
                raise RuntimeError(
                    "SAFETY STOP: Incomplete audit result count"
                )

            checkpoint.execute(
                """
                UPDATE audit_runs
                SET completed_at=CURRENT_TIMESTAMP,
                    status='completed'
                WHERE run_id=?
                """,
                (run_id,)
            )
            checkpoint.commit()

            print("\nAudit status: COMPLETED")
            print("Remote uploads: NONE")
            print("Remote deletions: NONE")
            print("Production SQLite modifications: NONE")

        finally:
            session.close()
            checkpoint.close()
            production.close()


if __name__ == "__main__":
    main()
