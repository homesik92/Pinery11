# Project instructions

A small website for a homeowners association: annual dues, rules and announcements. This repository is
**public**, so nothing personal, no credentials and no resident data is ever committed.

## Engineering discipline

Work follows the **`dev-workflow` skill**: invoke it before any session that changes code or docs. In short:
plan and wait for a go, work on a branch and land by pull request, review proportionally, and merge or deploy
only on the session owner's explicit go.

## Verification

There is no automated test suite yet. Check a change by opening the affected pages in a browser, at phone
width as well, and confirm nothing in the diff includes keys or resident information.

## Standing hazards

- **Public repository.** Grep the staged diff for secrets and personal information before every push.
- **Resident data is not for the repository.** Dues, addresses and accounts live in the database, not in files.
- **The custom domain** is set by the `CNAME` file; do not remove it.
