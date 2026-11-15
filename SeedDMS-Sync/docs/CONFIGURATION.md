# SeedDMS Sync — Configuration and Security Guide

## 1. Purpose

This guide records the configuration settings used by the
SeedDMS Sync Python project.

The configuration must be recreated locally after restoring
the project from GitHub.

Never store operational credentials or private configuration
files in the public repository.

## 2. Configuration keys identified in the source

The main sync.py module references these settings:

| Setting | Purpose |
|---|---|
| source_directory | Local document source directory |
| webdav_url | SeedDMS WebDAV endpoint |
| username | WebDAV authentication username |
| credentials_file | Local file containing authentication credentials |
| database | SQLite progress database location |
| log_file | Synchronization log location |
| ca_certificate | TLS certificate verification configuration |
| dry_run | Controls simulation versus actual changes |
| allow_overwrite | Controls permission to overwrite remote documents |
| delete_remote_files | Controls remote deletion policy |
| excluded_directories | Directories excluded from synchronization |
| excluded_extensions | File extensions excluded from synchronization |
| maximum_file_size_bytes | Maximum permitted source-file size |

These keys were identified through static source-code inspection.

Their precise data types, defaults and validation rules must
be confirmed against sync.py before creating a live configuration.

## 3. Required safety settings

The intended operating policy is:

    dry_run: true
    allow_overwrite: false
    delete_remote_files: false

These are conceptual settings, not a complete configuration file.

The exact configuration syntax must match the Python implementation.

Production synchronization remains disabled pending validation.

## 4. Authentication

The project uses a username and a credentials file.

The credentials file must remain outside the GitHub repository.

Recommended precautions:

- Restrict access to the operating-system user.
- Avoid printing credentials in logs.
- Never commit authentication secrets.
- Never embed passwords in WebDAV URLs.
- Do not share credentials through screenshots or terminal output.

A credential file must be restored separately from a secure backup.

## 5. WebDAV configuration

The WebDAV URL identifies the destination SeedDMS endpoint.

The public repository uses configurable destination checks.

Relevant environment variables include:

    SEEDDMS_EXPECTED_HOST
    SEEDDMS_EXPECTED_DESTINATION

The hostname setting identifies the permitted server.

The destination setting identifies the permitted WebDAV path.

Both must be configured correctly before any upload is attempted.

The current public-copy validation changes require regression
testing before operational use.

## 6. Source-directory protection

The source directory contains the documents selected for
synchronization.

The project includes source validation and exclusion logic.

During recovery:

1. Verify the source directory exists.
2. Verify the intended source-root identity.
3. Verify permissions and ownership.
4. Verify exclusion rules.
5. Use disposable test documents initially.
6. Confirm no unintended source modifications occur.

Source-root identity mismatch handling has an outstanding
regression issue and must be tested before production use.

## 7. SQLite progress database

The project uses SQLite to track synchronization progress.

The database must not be committed to GitHub.

If restoring a previous operational database:

- Preserve a backup of the original.
- Verify database integrity.
- Confirm source and remote document identities.
- Verify that tracked uploads correspond to remote files.
- Avoid automatically replaying incomplete transactions.

Do not assume an empty progress database is safe for
an existing populated SeedDMS destination.

## 8. Remote overwrite protection

The project is intended to support create-only synchronization.

Controlled testing previously confirmed duplicate prevention.

However, the SeedDMS WebDAV endpoint did not enforce
If-None-Match: * as expected.

Therefore, HTTP conditional requests alone must not be
treated as sufficient protection against remote overwrites.

Additional server-side or application-level safeguards
require verification before production operation.

## 9. Logging

Logs may contain:

- Document paths
- Server addresses
- Error messages
- Synchronization status
- Upload verification results

Treat logs as operationally sensitive.

Exclude them from GitHub and restrict access appropriately.

## 10. Certificate verification

The ca_certificate setting is referenced by sync.py.

Its exact behavior must be confirmed against the source.

Use trusted TLS certificates for network communication
where supported.

Do not disable certificate verification merely to
bypass connection errors.

## 11. Environment restoration checklist

Before attempting synchronization:

- [ ] Python environment restored
- [ ] Dependencies installed
- [ ] Configuration created locally
- [ ] Credentials restored securely
- [ ] Source directory verified
- [ ] WebDAV endpoint verified
- [ ] Expected hostname configured
- [ ] Expected destination path configured
- [ ] SQLite database location verified
- [ ] Logging configured
- [ ] Dry-run enabled
- [ ] Remote overwrites disabled
- [ ] Remote deletion disabled
- [ ] Exclusion rules verified
- [ ] Controlled test directory prepared

## 12. Production authorization

The GitHub repository is a project preservation copy.

Restoring the repository does not authorize production
synchronization.

Production operation requires separate validation and
explicit authorization.
