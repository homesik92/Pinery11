# Pinery Filing 11 HOA site

Static site for GitHub Pages plus a Supabase database for sign-in and private dues balances. No build step for the site itself.

## Pages

- `index.html`: announcements, a "your dues" card, how to pay, governing documents, FAQ.
- `account.html`: create an account or sign in, request your address, see your own statement.
- `board.html`: board only. Dues ledger, sign-up approvals, announcements, dues settings.
- `guidelines.html`: the full architectural guidelines text and an FAQ that links to each rule. Rebuild it with `python3 tools/build_guidelines.py` (needs `pdftotext`).

## Setup (one time)

1. In Supabase, open SQL Editor, paste `supabase/schema.sql`, and run it. It creates the tables, the privacy rules and the 45 lots.
2. Add the board: run a statement that inserts the board emails into `public.board_members` (see the comment at the end of `schema.sql`). Do not commit that list to this public repo.
3. In Supabase, open Authentication, then URL Configuration. Set Site URL to the GitHub Pages address and add the same address under Redirect URLs. Keep "Confirm email" turned on, because board access is matched by email.
4. `assets/config.js` already holds the project URL and the publishable key. Both are meant to be public. Never put a `service_role` or secret key in this repo.

## Privacy model

Residents sign up with email and password, then ask for an address. A board member approves the request on the Board page. Only after that can the resident read the payments and adjustments for that one address. The rules are enforced in the database (row level security), not in the page. Announcements, the lot list and the yearly dues amount are public.

## Editing content

- `assets/config.js`: payment instructions, contact, documents, and fallback dues numbers.
- Dues amount, due date and late fee per year: Board page, Dues settings.
- Announcements: Board page, Announcements.
- `docs/`: PDFs listed under `documents` in `config.js`.
