# SeedDMS Sync — Installation and Recovery Guide

## 1. Purpose

This document describes how to restore the SeedDMS Sync Python
project from its GitHub source repository.

The procedure restores the application source and Python environment.

It does not restore SeedDMS server data, MariaDB databases,
operational SQLite databases, credentials or source documents.

Those require separate, secure backups.

## 2. Original development environment

Verified on 15 November 2026:

- Client: Lenovo Linux laptop
- Python: 3.12.15
- Python virtual environment: .venv
- HTTP library: requests 2.34.2
- Server: Raspberry Pi
- Document management system: SeedDMS 6.0.42
- Database service: MariaDB
- Transfer protocol: WebDAV

The original project was located at:

    ~/SeedDMS-Sync

## 3. System requirements

A replacement installation requires:

- Linux operating system
- Python 3.12-compatible interpreter
- Python virtual environment support
- pip
- Git
- Network connectivity to the SeedDMS server
- An operational SeedDMS WebDAV endpoint
- Valid SeedDMS authentication credentials

Python 3.12.15 was the original version.

Other Python versions have not been verified for this project.

## 4. Install operating system packages

On a Debian or Ubuntu-based Linux system:

    sudo apt update

    sudo apt install git python3 python3-venv python3-pip

Confirm:

    python3 --version

The Python version supplied by the distribution may differ
from the original development environment.

## 5. Clone the source repository

    cd ~

    git clone git@github.com:wynandkui/Pyhton-projects.git

    cd Pyhton-projects/SeedDMS-Sync

The repository name intentionally uses the spelling
Pyhton-projects.

GitHub SSH authentication must be configured before cloning
with the SSH address.

Alternatively, use the HTTPS clone address.

## 6. Create the Python environment

    python3 -m venv .venv

    .venv/bin/python -m pip install --upgrade pip

Install the direct dependency:

    .venv/bin/python -m pip install -r requirements.txt

For a closer reproduction of the recorded environment:

    .venv/bin/python -m pip install -r requirements-lock.txt

The locked versions were recorded from the original installation.

Their availability and compatibility must be verified during
restoration.

## 7. Verify the Python environment

    .venv/bin/python --version

    .venv/bin/python -m pip check

    .venv/bin/python -c "import requests; print(requests.__version__)"

Expected original requests version:

    2.34.2

## 8. Restore local configuration

The synchronizer uses a local configuration file.

The exact configuration schema must be followed.

Important settings include:

- source_directory
- webdav_url
- username
- credentials_file
- database
- log_file
- ca_certificate
- dry_run
- allow_overwrite
- delete_remote_files
- excluded_directories
- excluded_extensions
- maximum_file_size_bytes

Never place real passwords or credential files in GitHub.

Do not assume that example configuration values are suitable
for production.

## 9. Destination validation settings

Some scripts require these environment variables:

    SEEDDMS_EXPECTED_HOST
    SEEDDMS_EXPECTED_DESTINATION

The first represents the permitted SeedDMS hostname.

The second represents the permitted WebDAV destination path.

These settings must match the configured WebDAV endpoint.

The public-repository changes to destination validation still
require complete restoration and regression testing.

## 10. Initial safety policy

Before running any upload operation, verify:

    dry_run = true
    allow_overwrite = false
    delete_remote_files = false

Use a dedicated test directory containing disposable files.

Do not initially point the synchronizer at an entire
production document directory.

## 11. Validation before production

Complete the following checks:

1. Confirm source directory identity.
2. Confirm the WebDAV destination.
3. Confirm authentication and TLS settings.
4. Confirm local and remote permissions.
5. Confirm dry-run behavior.
6. Confirm exclusion rules.
7. Confirm SQLite tracking behavior.
8. Confirm duplicate-upload prevention.
9. Confirm remote SHA256 verification.
10. Confirm recovery after interrupted uploads.
11. Confirm the source-root mismatch handling.
12. Confirm remote overwrite protection.

A controlled test previously succeeded, but the public
repository version has not yet passed a full reinstall test.

## 12. Production restrictions

The original project was deliberately left in a
non-production state.

Do not enable:

- Unattended synchronization
- Remote file deletion
- Remote overwriting
- Automatic production uploads

without a separate review and explicit authorization.

## 13. Restoring operational state

The GitHub repository contains source code and documentation.

It does not contain the original SQLite progress database.

Restoring an old database requires checking its relationship
to the source files and remote SeedDMS documents.

Never assume that an empty SQLite database means all existing
remote documents can safely be uploaded again.

## 14. Server recovery

Rebuilding the Raspberry Pi requires a separate SeedDMS
server recovery procedure.

That procedure must address:

- SeedDMS installation
- SeedDMS application configuration
- MariaDB database restoration
- SeedDMS document storage
- WebDAV configuration
- Authentication
- File permissions
- Network configuration
- Backup verification

The client repository alone cannot recreate the server data.

## 15. Recovery acceptance criteria

A restoration is considered successful only after:

- Python dependencies install successfully.
- Configuration validation passes.
- Source-root identity is verified.
- Dry-run testing succeeds.
- A controlled test document uploads successfully.
- Remote SHA256 matches the source.
- Duplicate retries do not create unwanted documents.
- Existing remote documents remain protected.
- Logs and progress tracking operate correctly.

Do not enable unattended production synchronization
until all applicable checks pass.
