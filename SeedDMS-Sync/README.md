# SeedDMS Sync

## Project overview

SeedDMS Sync is a Python-based project for synchronizing documents
from a Linux laptop to a SeedDMS document management system using WebDAV.

The project was developed for a Lenovo Linux laptop and a Raspberry Pi
running SeedDMS 6.0.42.

Its primary objective is to provide controlled, verifiable document
uploads while protecting the original source documents.

## Project architecture

    Lenovo Linux Laptop
    |
    | Local documents
    | Python synchronization scripts
    | SQLite progress database
    |
    | HTTPS/HTTP WebDAV connection
    v
    Raspberry Pi
    |
    | SeedDMS 6.0.42
    | MariaDB database
    | Document storage

The WebDAV server address and authentication details must be supplied
through local configuration. They are not included in this repository.

## Current development status

This repository preserves a development-stage implementation.

Verified during development:

- Controlled test-file upload
- SHA256 verification of uploaded test content
- SQLite progress tracking
- Duplicate-upload prevention in the controlled test
- Source-file exclusion rules
- Dry-run operation
- Destination validation checks

Important limitations:

- Production synchronization has not been authorized.
- Unattended scheduling has not been enabled.
- Remote overwriting and deletion are not authorized.
- WebDAV If-None-Match enforcement requires additional safeguards.
- Source-root identity and recovery error handling require further
  regression testing.
- The public-repository configuration changes require restoration testing.

Do not assume this repository is ready for unattended production use.

## Safety requirements

The intended operating policy is:

    dry_run = true
    allow_overwrite = false
    delete_remote_files = false

These settings must be verified before any synchronization operation.

Never publish:

- Passwords or API tokens
- Private configuration files
- Credential files
- SQLite operational databases
- Personal or business documents
- Private keys or certificates containing private keys

## Python environment

Original verified environment:

- Python 3.12.15
- requests 2.34.2

See:

- requirements.txt
- requirements-lock.txt

## Project files

- sync.py — Core synchronization and WebDAV functions
- auto_sync.py — Automatic synchronization orchestration
- run_test_sync.py — Test synchronization entry point
- production_preview.py — Production preview
- production_sync.py — Production synchronization entry point
- production_upload.py — Production upload workflow
- production_batch_sync.py — Batch synchronization
- production_version_preview.py — Version preview and tracking
- production_version_sync.py — Version synchronization
- production_version_uploader.py — Version upload and validation
- versioning.py — Supporting version-upload functionality

## Documentation

Detailed technical documentation is maintained in the docs directory.

Planned documentation includes:

1. System architecture
2. Installation and dependencies
3. Configuration and credentials
4. Script reference
5. Synchronization workflow
6. Safety and verification procedures
7. Troubleshooting
8. Disaster recovery
9. Development history and outstanding work

## Reinstallation

A future installation should follow the documented recovery procedure,
configure credentials locally, and begin with isolated dry-run tests.

Do not enable production uploads until the destination, source identity,
permissions, upload safeguards and checksum verification have been tested.

## Repository purpose

This repository is intended to preserve the source code, technical
documentation and development history needed to reconstruct the project
after equipment replacement, operating system reinstallation or failure.

Operational credentials, databases and document contents must be backed
up separately using an appropriately secured backup system.

## Upstream SeedDMS project

Official upstream GitHub organization: [SeedDMS](https://github.com/SeedDMS).

This synchronizer is an independent integration project. Consult the upstream organization for the SeedDMS application source and releases.
