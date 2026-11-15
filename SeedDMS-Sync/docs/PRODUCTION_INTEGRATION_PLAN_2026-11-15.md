# SeedDMS Sync — production integration plan

Status: **Production integration authorised by project owner on 2026-11-15; deployment NOT yet performed.**

This plan records the authorisation to develop and deploy a safe create-only synchronizer. It does **not** authorise destructive document changes or bypassing safety gates.

## Verified baseline (2026-11-15)
- SeedDMS 6.0.42; destination root `Laptop Docs`, folder ID 306.
- 82 folders, 547 documents, 551 content versions under destination root.
- Lenovo SQLite tracking records: 543. Four-record discrepancy remains to be reconciled before broad rollout.
- Existing WebDAV PUT ignores `If-None-Match: *` and can update an existing document.
- `tblDocuments` has no unique `(folder,name)` constraint; `tblDocumentContent` has a unique `(document,version)` index.
- Standard access callbacks are grant-oriented and do not provide a deny-only create permission.
- `SeedDMS_Core_Folder::addDocument()` uses a transaction but does not atomically enforce name uniqueness.

## Required implementation
1. Implement a separately authenticated, scoped create-only upload mechanism. Validate canonical destination paths and folder ancestry on the server.
2. Enforce no-update/no-duplicate behavior atomically across **all relevant write paths**. A lock respected only by the new endpoint is not sufficient. Evaluate a compatible scoped database reservation mechanism or enforced isolation; do not add a global unique index without compatibility review.
3. Preserve SeedDMS document creation semantics and avoid direct modification of production core files where possible.
4. Require HTTPS with verified certificates, least-privilege credentials, request limits, and audit logs that do not expose secrets or document contents.
5. Update both Lenovo upload paths to use the verified mechanism; retain source snapshots, GET SHA-256/size verification, and SQLite progress tracking. On uncertain results, stop and reconcile rather than blindly retry.
6. Reconcile the 547 remote documents against 543 tracking records without overwriting or deleting anything.
7. Test in an isolated SeedDMS instance, including simultaneous requests, ordinary UI/WebDAV competition, interrupted requests, duplicate names, and rollback.
8. Take and restore-test backups of MariaDB, SeedDMS document storage and configuration, and Lenovo synchronizer before any production deployment.
9. Conduct a small explicitly reviewed production pilot, verify unchanged preexisting documents and versions, then consider larger batches. Unattended scheduling remains off until separately approved.

## Deployment gates
- No deployment until concurrency protection is demonstrated across competing write paths.
- No production upload until baseline reconciliation, restore testing, and pilot plan are approved.
- No overwrite, deletion, automatic retry after uncertain response, or unattended scheduling.
- No secrets, local config, SQLite operational databases, or document content in this public repository.

## Current status
This branch is for review and implementation. Creating it and this plan **does not modify** the Raspberry Pi, Lenovo laptop, SeedDMS installation, database, or production documents.
