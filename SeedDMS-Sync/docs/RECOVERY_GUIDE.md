# SeedDMS Sync — Reconstruction and Recovery Guide

## 1. Purpose

This guide describes how to recover the preserved SeedDMS Sync
project on a replacement Linux computer.

The project provides a one-way synchronization implementation
between a local Linux Documents directory and a SeedDMS server
using WebDAV.

The preserved implementation is development-stage software.
It must not be enabled for unattended production synchronization
until its outstanding safety and restoration tests are completed.

## 2. Preserved repository

Repository:
https://github.com/wynandkui/Pyhton-projects

Project directory:
SeedDMS-Sync

Initial preservation commit:
6349548

The repository preserves:

- Eleven Python source files
- Python dependency manifests
- Installation documentation
- Configuration documentation
- Development history
- This recovery guide

Operational credentials, local databases and private configuration
files are intentionally excluded.

## 3. Original development environment

Original computer:
Lenovo Linux laptop

Original Python version:
3.12.15

Original operational project:
~/SeedDMS-Sync

Original source directory:
~/Documents

Destination platform:
Raspberry Pi running SeedDMS 6.0.42

Destination folder:
Laptop Docs

These details describe the historical development environment,
not guaranteed requirements for future systems.

## 4. Restore the source code

Install Git and Python using the package manager appropriate
to the replacement Linux distribution.

Clone the preserved repository:

    git clone https://github.com/wynandkui/Pyhton-projects.git

Enter the project directory:

    cd Pyhton-projects/SeedDMS-Sync

Verify the source files:

    ls -la

Verify the documentation:

    ls -la docs

## 5. Rebuild the Python environment

Create a virtual environment:

    python3 -m venv .venv

Activate it:

    source .venv/bin/activate

Upgrade pip:

    python -m pip install --upgrade pip

Install the preserved dependency version:

    python -m pip install -r requirements.txt

The requirements-lock.txt file records the dependency versions
observed during the original development process.

Dependency installation and compatibility on a new machine
must be verified independently.

## 6. Verify Python source integrity

Run:

    python -m compileall -q .

This checks Python syntax only.

It does not verify WebDAV connectivity, configuration correctness,
synchronization behavior or operational safety.

## 7. Restore private configuration

Read:

    docs/CONFIGURATION.md

The original configuration and credentials are not included
in the public repository.

Reconstruct the configuration from trusted private records.

Do not copy passwords, tokens or authentication credentials
into GitHub.

The preserved public code uses environment-based destination
checks, including:

    SEEDDMS_EXPECTED_DESTINATION
    SEEDDMS_EXPECTED_HOST

Review the exact requirements of each script before setting
these variables.

Do not assume the public configuration changes have passed
end-to-end restoration testing.

## 8. Restore the SeedDMS server

The original destination used SeedDMS 6.0.42 on a Raspberry Pi.

A complete server recovery requires separately preserved:

- SeedDMS application files and version information
- SeedDMS database backup
- Document storage backup
- Server configuration
- WebDAV configuration
- User and folder permissions
- Authentication configuration

These server components are not included in the Python
project repository.

Do not assume that cloning the Python repository restores
the SeedDMS server or its documents.

## 9. Restore synchronization state

The original implementation used SQLite to track
synchronization progress.

Operational SQLite databases are intentionally excluded
from the public repository.

Restoring the Python source alone does not restore the
original synchronization history.

Do not start uploads against an existing production
destination without first reconciling its contents and
the synchronization tracking state.

## 10. Known WebDAV limitation

The original investigation established that the SeedDMS
WebDAV endpoint did not reliably enforce:

    If-None-Match: *

Therefore, an HTTP conditional upload cannot currently
be treated as sufficient protection against overwriting
an existing destination file.

Create-only behavior requires additional verified safeguards.

Do not enable unattended production uploads until this
limitation has been addressed and tested.

## 11. Known unfinished work

The following work remained outstanding at preservation:

- Full clean-machine restoration test
- Verification of public environment-based destination checks
- Source-root identity mismatch regression handling
- Reliable create-only overwrite prevention
- Complete production acceptance testing
- Unattended scheduling authorization

These are known limitations, not completed features.

## 12. Original controlled test

The original development process successfully tested
a nested file upload:

    Level_A/Level_B/nested-test.txt

The uploaded file was SHA256-verified.

SQLite tracking was tested.

A duplicate retry was blocked.

This was a controlled development test.

It does not establish that the entire production
synchronization process is safe.

## 13. Safe restoration acceptance procedure

Before considering a restored installation operational:

1. Verify the Python environment and dependencies.
2. Reconstruct private configuration securely.
3. Confirm the correct SeedDMS destination.
4. Verify authentication with a non-production test.
5. Test nested directory creation.
6. Test a new file upload in an isolated test folder.
7. Compare source and destination SHA256 hashes.
8. Verify synchronization tracking.
9. Verify duplicate uploads are rejected.
10. Verify existing destination files cannot be overwritten.
11. Verify incorrect destination settings are rejected.
12. Verify source-root identity mismatch handling.
13. Run production preview without modifying files.
14. Review and approve the proposed production scope.

Do not proceed to unattended production operation
merely because the application starts successfully.

## 14. Historical production scope

At the original development stopping point:

Total source files:
558

Eligible files:
555

Excluded files:
3

Production synchronization remained in dry-run mode.

These historical figures must not be assumed to reflect
the current contents of the source directory.

## 15. Explicitly deferred changes

The original project did not authorize:

- Unattended production scheduling
- Overwriting existing destination documents
- Deleting remote documents
- MariaDB hardening changes

These restrictions must be reviewed before any
future production deployment.

## 16. Recovery success criteria

A recovery is considered complete only when:

- The repository has been restored successfully.
- Python dependencies are installed and verified.
- Private configuration is reconstructed securely.
- The intended SeedDMS server is identified.
- Synchronization state is understood or reconciled.
- Controlled tests pass.
- Existing destination files are protected.
- Production scope is independently reviewed.
- Operational deployment is explicitly authorized.

## 17. Important distinction

GitHub preserves the project source code and documentation.

It does not automatically preserve:

- Live credentials
- Operational SQLite databases
- SeedDMS server databases
- SeedDMS document storage
- Linux service configuration
- Local scheduling configuration
- Private server settings

These require separate secure backups.

## 18. Final recovery principle

Restore and validate the system in an isolated test
environment before reconnecting it to production data.

The priority is preservation of existing documents,
not automatic resumption of synchronization.
