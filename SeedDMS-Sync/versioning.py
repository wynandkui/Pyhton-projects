from pathlib import Path


def upload_changed_version_safely(
    sync, config, session, source_path, relative_path, conn
):
    """Upload a changed isolated document as a new SeedDMS version."""

    sync.validate_upload_environment(config)

    relative_path = Path(relative_path)
    allowed = Path("Level_A/Level_B/nested-test.txt")

    if relative_path != allowed:
        raise RuntimeError("SAFETY STOP: Unauthorised test document")

    source_root = Path(config["source_directory"]).resolve(strict=True)
    source_path = Path(source_path)

    if source_path.is_symlink():
        raise RuntimeError("SAFETY STOP: Symlink prohibited")

    if source_path.resolve(strict=True) != (
        source_root / allowed
    ).resolve(strict=True):
        raise RuntimeError("SAFETY STOP: Invalid source path")

    if conn is None:
        raise RuntimeError("SAFETY STOP: SQLite connection required")

    tracked = sync.get_tracked_file(conn, relative_path.as_posix())

    if tracked is None or tracked[2] != "done":
        raise RuntimeError("SAFETY STOP: No successful upload baseline")

    old_hash, old_size, _ = tracked
    snapshot = None

    try:
        snapshot, new_hash, new_size = sync.create_source_snapshot(
            config, source_path
        )

        url = sync.remote_url(config, relative_path)

        if not sync.remote_exists(session, url):
            raise RuntimeError("SAFETY STOP: Remote document missing")

        remote_hash, remote_size = sync.calculate_remote_sha256(
            config, session, relative_path
        )

        if (remote_hash, remote_size) == (new_hash, new_size):
            if not sync.verify_source_integrity(
                source_path, new_hash, new_size
            ):
                raise RuntimeError(
                    "SAFETY STOP: Source integrity failed"
                )
            sync.record_uploaded_file(
                conn, relative_path.as_posix(), new_hash, new_size
            )
            print("[RECOVERED/UNCHANGED] Remote content verified")
            return "recovered_or_unchanged"

        if (remote_hash, remote_size) != (old_hash, old_size):
            raise RuntimeError(
                "SAFETY STOP: Remote content differs from last "
                "synchronised version; manual reconciliation required"
            )

        if (new_hash, new_size) == (old_hash, old_size):
            print("[UNCHANGED] No upload required")
            return "unchanged"

        if not sync.verify_source_integrity(
            source_path, new_hash, new_size
        ):
            raise RuntimeError(
                "SAFETY STOP: Source integrity failed"
            )

        check_hash, check_size = sync.calculate_remote_sha256(
            config, session, relative_path
        )

        if (check_hash, check_size) != (old_hash, old_size):
            raise RuntimeError("SAFETY STOP: Remote changed before PUT")

        print("[NEW VERSION] Uploading isolated test document")

        with snapshot.open("rb") as handle:
            response = session.put(
                url,
                data=handle,
                headers={"Content-Type": "application/octet-stream"},
                timeout=(10, 120),
                allow_redirects=False,
            )

        print("[PUT] HTTP", response.status_code)

        if response.status_code not in (200, 201, 204):
            raise RuntimeError(
                "PUT status uncertain; inspect remote before retrying: "
                + str(response.status_code)
            )

        verified_hash, verified_size = sync.calculate_remote_sha256(
            config, session, relative_path
        )

        if (verified_hash, verified_size) != (new_hash, new_size):
            raise RuntimeError(
                "SAFETY STOP: Uploaded content verification failed"
            )

        if not sync.verify_source_integrity(
            source_path, new_hash, new_size
        ):
            raise RuntimeError(
                "SAFETY STOP: Source integrity failed"
            )

        sync.record_uploaded_file(
            conn, relative_path.as_posix(), new_hash, new_size
        )

        print("[PASS] New content verified and tracked")
        return "version_uploaded"

    finally:
        if snapshot is not None:
            snapshot.unlink(missing_ok=True)
