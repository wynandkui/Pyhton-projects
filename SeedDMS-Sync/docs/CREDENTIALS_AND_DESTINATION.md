# SeedDMS Sync — Credentials and Destination Configuration

## Authentication

The preserved sync.py uses HTTP Basic Authentication.

The username is read from the `username` configuration field.

The password is read from the file identified by
`credentials_file`.

The password file contains the password as plain text.
Trailing CR and LF characters are removed when it is read.

Never commit the password file to GitHub.

On Linux, protect the password file with:

    chmod 600 /path/to/private/credentials

The file should be owned by the account running the application.

## TLS certificate verification

The `ca_certificate` configuration field is passed directly
to the Python Requests session verification setting.

Use:

    true

to verify certificates against the normal trusted CA store.

Alternatively, provide the path to a trusted CA certificate
bundle where required.

Do not disable TLS verification for production connections.

## Destination validation

The preserved sync.py uses the environment variable:

    SEEDDMS_EXPECTED_DESTINATION

This must match the configured WebDAV destination URL
with exactly one trailing slash.

Example placeholder:

    export SEEDDMS_EXPECTED_DESTINATION="https://YOUR_SEEDDMS_SERVER/REPLACE_WITH_WEBDAV_PATH/"

The value must match the actual destination configured
in config.json after its trailing slash is normalized.

Other production scripts may additionally require:

    SEEDDMS_EXPECTED_HOST

Their validation behavior must be tested independently.

## Important upload restrictions

The preserved sync.py restricts experimental uploads to:

    ~/SeedDMS-Sync/upload-test/source

and the corresponding isolated test database.

It also requires:

    dry_run = true
    allow_overwrite = false
    delete_remote_files = false

These restrictions must not be bypassed merely to
enable production synchronization.

## Recovery limitations

The public repository does not include operational
passwords, private configuration or SQLite databases.

Reconstruct those separately from secure private backups.

The configuration example is a reference template.
It has not passed a complete clean-machine restoration test.
