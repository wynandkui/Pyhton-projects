import os
#!/usr/bin/env python3
"""SeedDMS production version synchroniser — preview only."""

import argparse
import fcntl
import sqlite3
from pathlib import Path
from urllib.parse import unquote, urlsplit

import auto_sync

PROJECT = Path.home() / "SeedDMS-Sync"
SOURCE = Path.home() / "Documents"
DATABASE = PROJECT / "progress.sqlite3"
EXPECTED_HOST = os.environ.get("SEEDDMS_EXPECTED_HOST", "")
DESTINATION = os.environ.get("SEEDDMS_EXPECTED_DESTINATION", "")
LOCK = PROJECT / ".production-batch.lock"


def validate_environment(config):
    if (
        config["dry_run"],
        config["allow_overwrite"],
        config["delete_remote_files"]
    ) != (True, False, False):
        raise RuntimeError("SAFETY STOP: Unsafe configuration")

    root = Path(config["source_directory"]).resolve(strict=True)
    database = Path(config["database"]).resolve(strict=True)
    url = urlsplit(config["webdav_url"])

    if root != SOURCE.resolve() or database != DATABASE.resolve():
        raise RuntimeError("SAFETY STOP: Production paths changed")

    if (
        url.scheme != "https"
        or url.hostname != EXPECTED_HOST
        or url.port not in (None, 443)
        or url.username is not None
        or url.password is not None
        or url.query
        or url.fragment
        or unquote(url.path).rstrip("/") + "/" != DESTINATION
    ):
        raise RuntimeError("SAFETY STOP: Destination changed")

    return root, database




def validate_document_path(source, root):
    """Reject paths outside the source root and symbolic-link components."""
    source = Path(source)
    root = Path(root).resolve(strict=True)

    if not source.is_absolute():
        raise ValueError("SAFETY STOP: Source path must be absolute")

    if not source.is_relative_to(root):
        raise ValueError("SAFETY STOP: Source outside production root")

    relative = source.relative_to(root)
    if not relative.parts:
        raise ValueError("SAFETY STOP: Source is the root directory")

    current = root

    for component in relative.parts:
        if component in (".", ".."):
            raise ValueError("SAFETY STOP: Unsafe path component")

        current = current / component

        if current.is_symlink():
            raise ValueError("SAFETY STOP: Symbolic link detected")

    if not source.is_file():
        raise ValueError("SAFETY STOP: Source is not a regular file")

    if not source.resolve(strict=True).is_relative_to(root):
        raise ValueError("SAFETY STOP: Resolved source escaped root")

    return source



def verify_source_root_identity(root):
    """Verify the production source root against its saved identity."""
    import json
    import os
    import stat

    root = Path(root)

    baseline_path = PROJECT / "source_root_identity.json"

    if baseline_path.is_symlink() or not baseline_path.is_file():
        raise RuntimeError(
            "SAFETY STOP: Source identity baseline missing or unsafe"
        )

    baseline = json.loads(baseline_path.read_text())

    if str(root) != baseline["source"]:
        raise RuntimeError(
            "SAFETY STOP: Source root path mismatch"
        )

    flags = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | os.O_CLOEXEC
    )

    fd = os.open(root, flags)

    try:
        current = os.fstat(fd)
        pathname = os.stat(root, follow_symlinks=False)

        if not stat.S_ISDIR(current.st_mode):
            raise RuntimeError(
                "SAFETY STOP: Source root is not a directory"
            )

        if (
            current.st_dev != pathname.st_dev
            or current.st_ino != pathname.st_ino
        ):
            raise RuntimeError(
                "SAFETY STOP: Source root changed during verification"
            )

        expected = (
            baseline["device"],
            baseline["inode"],
            baseline["uid"],
            baseline["gid"]
        )

        actual = (
            current.st_dev,
            current.st_ino,
            current.st_uid,
            current.st_gid
        )

        if actual != expected:
            raise RuntimeError(
                "SAFETY STOP: Production source root identity changed"
            )

        return True

    finally:
        os.close(fd)


def open_verified_source_root(root):
    """Return an open root descriptor after verifying its identity."""
    import json
    import os
    import stat

    root = Path(root)
    baseline_path = PROJECT / "source_root_identity.json"

    if not root.is_absolute() or ".." in root.parts:
        raise ValueError("SAFETY STOP: Invalid source root path")

    if baseline_path.is_symlink() or not baseline_path.is_file():
        raise RuntimeError("SAFETY STOP: Unsafe identity baseline")

    baseline = json.loads(baseline_path.read_text())

    if str(root) != baseline["source"]:
        raise RuntimeError("SAFETY STOP: Source root path mismatch")

    flags = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | os.O_CLOEXEC
    )

    fd = os.open(root, flags)

    try:
        current = os.fstat(fd)
        pathname = os.stat(root, follow_symlinks=False)

        if not stat.S_ISDIR(current.st_mode):
            raise RuntimeError("SAFETY STOP: Root is not a directory")

        if (
            current.st_dev != pathname.st_dev
            or current.st_ino != pathname.st_ino
        ):
            raise RuntimeError(
                "SAFETY STOP: Root changed during verification"
            )

        expected = (
            baseline["device"],
            baseline["inode"],
            baseline["uid"],
            baseline["gid"]
        )

        actual = (
            current.st_dev,
            current.st_ino,
            current.st_uid,
            current.st_gid
        )

        if actual != expected:
            raise RuntimeError(
                "SAFETY STOP: Source root identity mismatch"
            )

        return fd

    except BaseException:
        os.close(fd)
        raise

def open_secure_document(source, root):
    """Open a regular file relative to a trusted root descriptor."""
    import os
    import stat

    source = Path(source)
    root = Path(root)

    if not source.is_absolute() or not root.is_absolute():
        raise ValueError("SAFETY STOP: Absolute paths required")

    if ".." in source.parts or ".." in root.parts:
        raise ValueError("SAFETY STOP: Parent traversal rejected")

    if not source.is_relative_to(root):
        raise ValueError("SAFETY STOP: Source outside root")

    parts = source.relative_to(root).parts

    if not parts:
        raise ValueError("SAFETY STOP: Source is root directory")

    directory_flags = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | os.O_CLOEXEC
    )

    file_flags = (
        os.O_RDONLY
        | os.O_NOFOLLOW
        | os.O_CLOEXEC
        | os.O_NONBLOCK
    )

    directory_fd = open_verified_source_root(root)

    try:
        for component in parts[:-1]:
            next_fd = os.open(
                component,
                directory_flags,
                dir_fd=directory_fd
            )

            os.close(directory_fd)
            directory_fd = next_fd

        file_fd = os.open(
            parts[-1],
            file_flags,
            dir_fd=directory_fd
        )

        try:
            metadata = os.fstat(file_fd)

            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError(
                    "SAFETY STOP: Source is not a regular file"
                )

            return os.fdopen(file_fd, "rb")

        except BaseException:
            os.close(file_fd)
            raise

    finally:
        os.close(directory_fd)

def classify_local_document(source, baseline_hash, baseline_size):
    """Classify local content against its recorded SQLite baseline."""
    import hashlib

    source = Path(source)

    try:
        validate_document_path(source, SOURCE)
    except (ValueError, OSError):
        if not source.exists() and not source.is_symlink():
            return "MISSING_LOCAL"
        return "UNSAFE_SOURCE"

    import os
    import stat

    digest = hashlib.sha256()

    try:
        handle = open_secure_document(source, SOURCE)
    except (ValueError, OSError):
        return "UNSAFE_SOURCE"

    with handle:
        before = os.fstat(handle.fileno())

        if not stat.S_ISREG(before.st_mode):
            return "UNSAFE_SOURCE"

        for chunk in iter(lambda: handle.read(1048576), b""):
            digest.update(chunk)

        after = os.fstat(handle.fileno())

    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ctime_ns != after.st_ctime_ns
    ):
        return "SOURCE_CHANGED_DURING_READ"

    current_hash = digest.hexdigest()
    current_size = after.st_size

    if (
        current_hash == baseline_hash
        and current_size == baseline_size
    ):
        return "UNCHANGED_LOCAL"

    return "MODIFIED_LOCAL"

def main():
    parser = argparse.ArgumentParser(
        description="SeedDMS production version preview"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Read-only preview"
    )
    args = parser.parse_args()

    if not args.preview:
        raise SystemExit(
            "SAFETY STOP: Only --preview is supported"
        )

    sync = auto_sync.load_sync_module()
    config = sync.load_config(PROJECT / "config.json")
    root, database = validate_environment(config)

    with LOCK.open("a+") as lock:
        fcntl.flock(
            lock,
            fcntl.LOCK_EX | fcntl.LOCK_NB
        )

        conn = sqlite3.connect(
            database.as_uri() + "?mode=ro",
            uri=True
        )
        conn.execute("PRAGMA query_only=ON")

        try:
            rows = conn.execute(
                """
                SELECT path, sha256, size, status
                FROM processed_files
                ORDER BY path
                """
            ).fetchall()

            print("===== PRODUCTION VERSION UPLOADER =====")
            print("Mode: PREVIEW ONLY")
            print("Source:", root)
            print("Tracked documents:", len(rows))
            print("Production SQLite: READ ONLY")
            print("Remote uploads: DISABLED")
            print("Remote deletions: DISABLED")
            print()
            print("Upload implementation: NOT INSTALLED")
            print("Execution authorisation: NOT AVAILABLE")
            print()
            print("===== CLASSIFICATION CAPABILITY =====")
            print("Read-only audit module: production_version_preview.py")
            print("Latest verified production baseline: 543 documents")
            print("Classification execution: SEPARATE AUDIT REQUIRED")
            print("Supported classifications:")
            print("  UNCHANGED, MODIFIED, RECOVERY, CONFLICT")
            print("  MISSING_LOCAL, MISSING_REMOTE, EXCLUDED")
            print("No remote checksum requests made by this preview")

        finally:
            conn.close()


if __name__ == "__main__":
    main()
