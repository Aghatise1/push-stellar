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

The seeded showcase contains historical simulation data for inspecting the interface. It does not demonstrate a funded escrow. Create a fresh agreement and use separate testnet wallets for the current payment workflow.

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
3. Publish a job with a clear scope, deliverables, exact test XLM or test USDC amount and deadline. Test assets have no monetary value.
4. Use a separate account and browser profile for the worker. Verify that account and apply to the job.
5. Each participant connects their own Freighter wallet on Stellar testnet. The client and worker must have different valid wallet addresses. Push never requests private keys or recovery phrases.
6. The client selects the worker. Push prepares the agreement automatically from the accepted job terms and saved participant wallets. If a wallet is missing, the workroom preserves the assignment and shows the exact recovery step. The worker reviews and accepts the agreement. Acceptance alone does not debit a wallet; accepted wallet addresses remain pinned to the agreement.
7. With testnet escrow enabled and the configured contract available, the client reviews and signs funding in Freighter. The contract receives the agreed test tokens. Begin work only after Push records confirmed funding on Stellar. If submission is uncertain, check its status before retrying.
8. Use the private workroom for messages and delivery evidence. The worker submits the delivery and signs the contract delivery action.
9. The client reviews the work and signs release or a permitted revision. Routine release transfers the escrowed tokens to the agreed worker wallet without staff approval. Push updates payment status after confirmation.
10. Either participant may open a dispute in an eligible funded or submitted state. Ordinary release is blocked. Authorised staff with contract permission can sign a release, refund or split restricted to the original participant wallets. Staff cannot resolve their own work.
11. Unfunded cancellation and expiry refund or claim paths follow contract state, timing and signer rules. Passing a deadline does not automatically transfer tokens.

New assignments do not offer simulated bank/card payments or general direct wallet transfers. Historical simulation and direct payment records are retained as earlier records. Profiles, conversations and delivery files remain in the application; contract financial actions are recorded on Stellar.

The three sample jobs are labelled and do not accept applications. To add them to a fresh database, run `python manage.py seed_demo` with the prepared Python environment. No shared demo password or login bypass exists. Profiles appear publicly only after their owner enables publication.

## What has been implemented

- Django-managed password hashing, session login/logout, signed email verification and expiring password recovery.
- Server-side ownership and participant checks; private proposals and assignments.
- Hiring accounts can close unassigned jobs; workers can withdraw applications while a job is open. Both actions retain records, require confirmation, and are terminal in this preview.
- Hiring accounts can edit an open brief until its first application arrives. The terms then become read-only to protect what applicants considered.
- CSRF protection, database-backed request limits, a hard daily email-recipient cap, form validation, escaped output, restricted profile fields and security headers.
- Server-controlled assignment state changes, stored agreement scope/budget and a chronological event record.
- Agreement bound testnet escrow with server validated transactions and confirmation checks. Pending requests are not treated as payments.
- Freighter signing for client funding, worker delivery, client release and authorised dispute settlement. Push never stores wallet private keys.
- The staff governed Soroban contract in `contracts/contracts/push-escrow-staff`, with exact token locking, role authorisation, delivery hashes, revision, release, expiry and dispute resolution paths. The fee efficient deployment and measured XLM funding cost are recorded in `contracts/deployments/testnet-owner-escrow-v4.json`. Existing agreements retain their recorded contract addresses; earlier deployment files remain historical evidence.
- An optional Orbio workroom assistant can summarise scope, delivery evidence and dispute records. It is disabled unless a server key and exact model are configured. Its output is advisory: Stellar confirms transactions, participants approve routine payments, and authorised staff sign every disputed settlement.
- Private project conversations with participant access checks and authorised support review. Messages are not encrypted end to end.
- Separate Wallet and Payments areas for wallet connection, earnings and settlement records. Payment actions belong to an accepted workroom agreement.
- Dashboard earnings/progress summaries and a Freighter testnet public-address connection.
- Separate public and signed-in interfaces, with a bold wallet-style balance, responsive work console, custom mark and reduced-motion-safe payment animation. GSAP is vendored locally, so the interface makes no third-party runtime request.

The included tests cover account flows, access restrictions, transaction validation and escrow state and permission checks, alongside historical payment behaviour. Automated checks do not replace the browser evidence described in [the acceptance checklist](docs/pilot-acceptance.md). Run:

```powershell
.\.runtime-venv\Scripts\python.exe manage.py test core
.\.runtime-venv\Scripts\python.exe manage.py check
cd contracts
cargo test -p push-escrow-staff
stellar contract build --package push-escrow-staff
```

On this computer the existing prepared Python also lives at `../../work/push-venv/Scripts/python.exe`. Tests use a separate disposable database, not your preview accounts.

## Configuration and private files

`.env.example` documents environment variables. For local development, the app loads an ignored `.env` file; operating-system environment variables take precedence. Production settings should be supplied through the host's protected secret configuration. A missing local signing key is generated in `.local-key`. Keep it private and stable; replacing it invalidates existing sessions and signed links.

Never upload `.local-key`, `.env`, `db.sqlite3`, database journals, `private-mail`, or any environment folder. `.gitignore` excludes them, but a manual ZIP may still include them. Do not serve this project directory as static files: only the `static` directory contains public assets.

`PUSH_ENV=production` disables debug output, requires a long signing key, an email transport and an HTTPS site origin, and enables secure cookies and HTTPS protections. The deployed testnet MVP uses Render, Supabase PostgreSQL and the Brevo HTTPS mail API described in `EMAIL-SETUP.md`. Backups, external monitoring and real payment integration remain release gates. See `LAUNCH-CHECKLIST.md`.

No system can honestly promise zero bugs or immunity to attack. This is a tested foundation with explicit release gates, not a completed independent security audit.
