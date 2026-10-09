# Push: Stellar testnet MVP

## Current implementation

Push coordinates freelance briefs, applications, private workrooms and contract escrow using test XLM and test USDC. New assignments use the staff governed Soroban escrow flow. Legacy simulation records are historical; they are not real deposits or customer revenue. General wallet transfers are blocked in the current assignment only flow.

The client signs funding after worker acceptance. The worker signs delivery, the client signs release, and authorised staff sign disputed settlements. Push never stores private wallet keys. Staff and customer signing sessions are separate. Contract authority is separate from the saved proof of wallet ownership.

The pilot was previously activated on Render. Confirm current health and configuration before demonstrations. Mainnet is not supported by this release. Test assets have no monetary value. Recorded QA is not an independent security audit or proof of a complete Freighter browser test.

Start with [current documentation](docs/README.md), [architecture](docs/ecosystem.md), [wallet operation](docs/testnet-escrow.md), [acceptance checks](docs/pilot-acceptance.md) and [security readiness](docs/security-readiness.md). Older planning files describe historical phases and must not override current implementation evidence.

The pilot uses invitations. The intended future mainnet platform is publicly accessible subject to review and launch decisions. The founder owns the funding roadmap; no sprint budget or 30 day plan is defined by this documentation update.

See STAGING.md for staging setup. A staging configuration file is not evidence that a staging service has been provisioned.

## Open the preview

While the local server is running, open http://127.0.0.1:8765/ in a browser on this computer. `start-local.ps1` starts it again. The original Desktop website remains separate and unchanged.

From PowerShell in this folder:

```powershell
.\start-local.ps1
```

## Local reviewer accounts

Create or refresh the two verified showcase identities and their representative workflow:

```powershell
..\..\work\push-venv\Scripts\python.exe manage.py seed_showcase --rotate-passwords
```

The command writes the random passwords to `private-demo-credentials.txt`. That file is ignored by version control. Use the **Atise** account to inspect the worker experience and the **Demo Studio** account to inspect the hiring experience. The command cannot run when `PUSH_ENV=production`.

Google sign-in appears only when both OAuth credentials are configured. The production client must authorise `https://pushearn.xyz` and its exact callback; follow `GOOGLE-OAUTH-SETUP.md`. Secrets belong in the ignored `.env` file or the deployment secret manager.

## Supabase database for a shared test deployment

Local development continues to use the existing SQLite database. For a hosted persistent Django service, create a Supabase project and copy its PostgreSQL **Session pooler** URL (port 5432) into the host's protected `PUSH_DATABASE_URL` environment variable. Do not expose the database password or Supabase service-role key in HTML, JavaScript, screenshots, or a committed `.env` file. The website uses Django's existing account and session system; Supabase provides the hosted PostgreSQL database rather than introducing a second, conflicting login system.

After configuring the protected URL on the host, install the requirements and run `python manage.py migrate` once against that database. Production mode now refuses to start without a managed PostgreSQL connection, which prevents an accidental public deployment on an ephemeral SQLite file.

On a new computer with Python 3.12 or newer, prepare the environment first:

```powershell
py -m venv .runtime-venv
.\.runtime-venv\Scripts\python.exe -m pip install -r requirements.txt
.\start-local.ps1
```

The start script applies local database migrations and starts a development server bound only to this computer. Stop it with Ctrl+C. It does not install packages, create accounts, or deploy anything. If port 8765 is occupied by this app, use the existing preview.

## Try a complete workflow

1. Create a hiring account with a unique test email and a password of at least 12 characters. Avoid real customer data in this preview.
2. Local development writes email to `private-mail` instead of sending it. Open the newest file there in a text editor, copy its verification link into the browser, and confirm the address. These files contain private, temporary account links; never publish them.
3. Publish a job with a scope, illustrative USD budget and deadline.
4. Use a separate browser profile or sign out, create a second worker account, verify it, and apply to the job.
5. As the hiring account, select the application. As the worker, accept the scope.
6. Use the private assignment thread to discuss the work. Only the selected worker and hiring account can read or send these messages.
7. From **Wallet**, connect a Freighter wallet set to Stellar testnet. Push stores only the public G-address; it never receives a secret key or recovery phrase. The profile form remains available for manually entering a public testnet address during local testing.
8. As the hiring account, select simulated USDC, simulated bank/card, or Stellar testnet USDC. The Stellar route requires the worker to have a public testnet G-address connected.
9. As the worker, submit notes and an optional work link. The hiring account can request revisions or approve. For Stellar testnet, Push prepares the exact test-USDC transaction and Freighter shows the recipient, amount and memo before approval. Push validates the signed transaction, submits it to Horizon and records the confirmed hash. An existing matching transaction can still be verified manually.
10. Both participants can raise a dispute before approval; disputes freeze the preview workflow. Cancellation is available before the route is confirmed.

The three sample jobs are labelled and do not accept applications. To add them to a fresh database, run `python manage.py seed_demo` with the prepared Python environment. No shared demo password or login bypass exists. Profiles appear publicly only after their owner enables publication.

## What has been implemented

- Django-managed password hashing, session login/logout, signed email verification and expiring password recovery.
- Server-side ownership and participant checks; private proposals and assignments.
- Hiring accounts can close unassigned jobs; workers can withdraw applications while a job is open. Both actions retain records, require confirmation, and are terminal in this preview.
- Hiring accounts can edit an open brief until its first application arrives. The terms then become read-only to protect what applicants considered.
- CSRF protection, database-backed request limits, a hard daily email-recipient cap, form validation, escaped output, restricted profile fields and security headers.
- Server-controlled assignment state changes, stored agreement scope/budget and a chronological event record.
- One simulated payment record per assignment; browser-supplied amounts cannot change the agreed amount.
- Non-custodial Stellar testnet sends signed in Freighter, with server-controlled recipient, asset, amount and memo; the server rejects altered envelopes, submits the signed transaction to Horizon and records its unique hash.
- A Soroban milestone contract with role authorisation, exact token locking, delivery hashes, release, expiry, dispute and split-resolution paths; tested locally and through a complete Stellar testnet lifecycle, but kept out of the active custody path until independent review.
- A participant-only inbox and project conversations backed by server-side access checks. These messages are private to assignment participants but are not end-to-end encrypted.
- Separate Wallet and Payments areas: Wallet handles Freighter, send and receive actions; Payments handles earnings, pending work and settlement history.
- Dashboard earnings/progress summaries and a Freighter testnet public-address connection.
- Separate public and signed-in interfaces, with a bold wallet-style balance, responsive work console, custom mark and reduced-motion-safe payment animation. GSAP is vendored locally, so the interface makes no third-party runtime request.

The included tests cover account flows, job editing/closure, application withdrawal, access restrictions, invalid state changes, simulated payment methods, signed Stellar transaction validation and repeated approval. Run:

```powershell
.\.runtime-venv\Scripts\python.exe manage.py test core
.\.runtime-venv\Scripts\python.exe manage.py check
cd contracts
cargo test -p push-milestone
stellar contract build --package push-milestone
```

On this computer the existing prepared Python also lives at `../../work/push-venv/Scripts/python.exe`. Tests use a separate disposable database, not your preview accounts.

## Configuration and private files

`.env.example` documents environment variables. For local development, the app loads an ignored `.env` file; operating-system environment variables take precedence. Production settings should be supplied through the host's protected secret configuration. A missing local signing key is generated in `.local-key`. Keep it private and stable; replacing it invalidates existing sessions and signed links.

Never upload `.local-key`, `.env`, `db.sqlite3`, database journals, `private-mail`, or any environment folder. `.gitignore` excludes them, but a manual ZIP may still include them. Do not serve this project directory as static files: only the `static` directory contains public assets.

`PUSH_ENV=production` disables debug output, requires a long signing key, an email transport and an HTTPS site origin, and enables secure cookies and HTTPS protections. The deployed testnet MVP uses Render, Supabase PostgreSQL and the Brevo HTTPS mail API described in `EMAIL-SETUP.md`. Backups, external monitoring and real payment integration remain release gates. See `LAUNCH-CHECKLIST.md`.

No system can honestly promise zero bugs or immunity to attack. This is a tested foundation with explicit release gates, not a completed independent security audit.
