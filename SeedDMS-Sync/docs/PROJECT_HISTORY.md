# SeedDMS Sync — Development History and Recovery Record

Last documented: 15 November 2026

## 1. Project objective

Develop a one-way document synchronization system from a
Linux laptop to SeedDMS 6.0.42 on a Raspberry Pi.

The intended operating model is create-only synchronization,
with source-file protection, duplicate prevention, progress
tracking and upload verification.

## 2. Original environment

Client:
- Lenovo Linux laptop
- Python 3.12.15
- Python virtual environment
- requests 2.34.2

Server:
- Raspberry Pi
- SeedDMS 6.0.42
- MariaDB
- WebDAV interface

Original client project:
~/SeedDMS-Sync

## 3. Original synchronization scope

The development project targeted the laptop's Documents
directory for one-way synchronization.

At the recorded development checkpoint:

- 558 source files were identified.
- 555 files were eligible.
- 3 files were excluded.

These figures are historical, not live inventory values.

Production synchronization remained in dry-run mode.

## 4. Verified controlled test

A controlled test uploaded a disposable file in a nested
directory structure:

Level_A/Level_B/nested-test.txt

The test confirmed:

- Remote directory creation
- Document upload
- SHA256 content verification
- SQLite progress tracking
- Duplicate retry prevention

This successful test does not establish production readiness.

## 5. Safety design

The intended safety policy is:

- One-way synchronization
- No remote deletion
- No unauthorized overwriting
- Dry-run before production
- Source-root identity verification
- File integrity verification
- Progress tracking
- Controlled error handling

## 6. WebDAV limitation

Testing established that the SeedDMS WebDAV endpoint did
not reliably enforce the If-None-Match: * condition.

Therefore, a conditional HTTP upload request alone cannot
be relied upon to guarantee create-only behavior.

Additional protection and regression testing are required.

## 7. Known unfinished work

The following work remains outstanding:

1. Complete regression testing of source-root identity
   mismatch handling.

2. Verify the public-repository destination configuration
   changes against the actual intended URL and path rules.

3. Confirm create-only protection under concurrent or
   interrupted upload conditions.

4. Complete a clean restoration test from GitHub.

5. Verify the restored SQLite tracking behavior.

6. Confirm that all documentation matches the source code.

7. Review and authorize production operation separately.

## 8. Explicitly deferred work

The following changes were not authorized:

- Unattended production scheduling
- Remote file deletion
- Remote file overwriting
- MariaDB hardening changes

Do not infer authorization from the presence of scripts
whose names contain production or upload.

## 9. GitHub preservation strategy

The public GitHub repository preserves:

- Python source code
- Dependency manifests
- Installation instructions
- Configuration reference
- Development history
- Recovery procedures

It deliberately excludes:

- Credentials
- Private operational configuration
- SQLite progress databases
- Personal documents
- Operational logs
- Private keys

## 10. Recovery sequence

When restoring the project:

1. Restore or verify the SeedDMS server independently.
2. Clone the GitHub repository.
3. Recreate the Python virtual environment.
4. Install the documented dependencies.
5. Restore credentials from secure backup.
6. Recreate local configuration.
7. Verify the source directory and source-root identity.
8. Verify the WebDAV destination.
9. Start with dry-run operation.
10. Test using disposable files.
11. Verify remote SHA256 checksums.
12. Test duplicate prevention.
13. Test interrupted-upload recovery.
14. Confirm overwrite and deletion protections.
15. Review all outstanding issues before production use.

## 11. Restoration acceptance

A restored installation is not production-ready merely
because the Python scripts execute successfully.

It must pass controlled end-to-end tests and all applicable
safety checks before production synchronization is enabled.

## 12. Project status at preservation

Development-stage project.

Controlled test upload: VERIFIED.

Production synchronization: NOT AUTHORIZED.

Unattended scheduling: NOT ENABLED.

Public GitHub copy: REQUIRES FINAL REVIEW AND RESTORATION TEST.
