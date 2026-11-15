# SeedDMS Sync — Python Script Reference

## Purpose

This document inventories the Python source files preserved
in the GitHub repository.

The information below is extracted from Python source code.
It documents source structure, not verified runtime behavior.

## Project inventory

Python scripts: 11

## auto_sync.py

Source lines: 199

### Imports

- `argparse`
- `collections`
- `importlib.util`
- `json`
- `pathlib`
- `sqlite3`

### Classes

No classes detected.

### Functions

- `classify_file`
- `load_sync_module`
- `main`

### Command-line arguments

- `--config`

### Restoration notes

Review this script's configuration, dependencies,
filesystem access and WebDAV operations before execution.

Do not assume production safety from syntax validation.

## production_batch_sync.py

Source lines: 281

### Imports

- `argparse`
- `auto_sync`
- `fcntl`
- `hashlib`
- `os`
- `pathlib`
- `shutil`
- `sqlite3`
- `tempfile`
- `urllib.parse`

### Classes

No classes detected.

### Functions

- `main`
- `safe_source`
- `sha256`

### Command-line arguments

- `--confirm`
- `--execute-new`
- `--max-files`

### Restoration notes

Review this script's configuration, dependencies,
filesystem access and WebDAV operations before execution.

Do not assume production safety from syntax validation.

## production_preview.py

Source lines: 123

### Imports

- `auto_sync`
- `collections`
- `pathlib`
- `sqlite3`

### Classes

No classes detected.

### Functions

- `main`

### Command-line arguments

No argparse-style arguments detected.

### Restoration notes

Review this script's configuration, dependencies,
filesystem access and WebDAV operations before execution.

Do not assume production safety from syntax validation.

## production_sync.py

Source lines: 103

### Imports

- `argparse`
- `auto_sync`
- `json`
- `pathlib`
- `sqlite3`

### Classes

No classes detected.

### Functions

- `main`

### Command-line arguments

- `--preflight`

### Restoration notes

Review this script's configuration, dependencies,
filesystem access and WebDAV operations before execution.

Do not assume production safety from syntax validation.

## production_upload.py

Source lines: 174

### Imports

- `auto_sync`
- `hashlib`
- `json`
- `os`
- `pathlib`
- `sqlite3`
- `tempfile`

### Classes

No classes detected.

### Functions

- `main`

### Command-line arguments

No argparse-style arguments detected.

### Restoration notes

Review this script's configuration, dependencies,
filesystem access and WebDAV operations before execution.

Do not assume production safety from syntax validation.

## production_version_preview.py

Source lines: 356

### Imports

- `argparse`
- `auto_sync`
- `collections`
- `fcntl`
- `hashlib`
- `os`
- `pathlib`
- `sqlite3`
- `urllib.parse`

### Classes

No classes detected.

### Functions

- `main`
- `safe_source`
- `save_result`
- `sha256_file`
- `sha256_remote`
- `start_or_resume`
- `validate_environment`

### Command-line arguments

- `--execute-audit`
- `--resume`

### Restoration notes

Review this script's configuration, dependencies,
filesystem access and WebDAV operations before execution.

Do not assume production safety from syntax validation.

## production_version_sync.py

Source lines: 151

### Imports

- `auto_sync`
- `collections`
- `hashlib`
- `pathlib`
- `sqlite3`

### Classes

No classes detected.

### Functions

- `checksum`
- `main`
- `remote_checksum`

### Command-line arguments

No argparse-style arguments detected.

### Restoration notes

Review this script's configuration, dependencies,
filesystem access and WebDAV operations before execution.

Do not assume production safety from syntax validation.

## production_version_uploader.py

Source lines: 423

### Imports

- `argparse`
- `auto_sync`
- `fcntl`
- `hashlib`
- `json`
- `os`
- `pathlib`
- `sqlite3`
- `stat`
- `urllib.parse`

### Classes

No classes detected.

### Functions

- `classify_local_document`
- `main`
- `open_secure_document`
- `open_verified_source_root`
- `validate_document_path`
- `validate_environment`
- `verify_source_root_identity`

### Command-line arguments

- `--preview`

### Restoration notes

Review this script's configuration, dependencies,
filesystem access and WebDAV operations before execution.

Do not assume production safety from syntax validation.

## run_test_sync.py

Source lines: 109

### Imports

- `argparse`
- `auto_sync`
- `pathlib`
- `sqlite3`
- `versioning`

### Classes

No classes detected.

### Functions

- `main`

### Command-line arguments

- `--execute-isolated-test`

### Restoration notes

Review this script's configuration, dependencies,
filesystem access and WebDAV operations before execution.

Do not assume production safety from syntax validation.

## sync.py

Source lines: 719

### Imports

- `argparse`
- `collections`
- `hashlib`
- `json`
- `logging`
- `os`
- `pathlib`
- `requests`
- `requests.auth`
- `shutil`
- `sqlite3`
- `tempfile`
- `urllib.parse`

### Classes

No classes detected.

### Functions

- `calculate_remote_sha256`
- `calculate_sha256`
- `create_source_snapshot`
- `ensure_remote_directories`
- `excluded`
- `get_tracked_file`
- `load_config`
- `main`
- `make_session`
- `open_database`
- `record_uploaded_file`
- `recover_verified_upload`
- `remote_exists`
- `remote_url`
- `setup_logging`
- `upload_file_safely`
- `validate_upload_environment`
- `verify_remote_upload_target`
- `verify_source_integrity`

### Command-line arguments

- `--config`

### Restoration notes

Review this script's configuration, dependencies,
filesystem access and WebDAV operations before execution.

Do not assume production safety from syntax validation.

## versioning.py

Source lines: 134

### Imports

- `pathlib`

### Classes

No classes detected.

### Functions

- `upload_changed_version_safely`

### Command-line arguments

No argparse-style arguments detected.

### Restoration notes

Review this script's configuration, dependencies,
filesystem access and WebDAV operations before execution.

Do not assume production safety from syntax validation.

## Known project limitations

- Full clean-machine restoration remains untested.
- Create-only WebDAV overwrite prevention requires verification.
- Public destination configuration requires runtime testing.
- Source-root identity mismatch handling requires regression testing.
- Production scheduling remains disabled.

## Related documentation

- README.md
- docs/INSTALLATION.md
- docs/CONFIGURATION.md
- docs/PROJECT_HISTORY.md
- docs/RECOVERY_GUIDE.md
