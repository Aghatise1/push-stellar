# Push release gates

Updated 24 September 2026. This checklist distinguishes the working local preview from a production service. No paid service has been purchased or connected.

## Completed locally

- [x] Accounts, verification, sign-in, sign-out and password recovery.
- [x] Profiles private by default, optional publication, private emails.
- [x] Jobs, applications, hiring-account selection and worker acceptance.
- [x] Owner-only job closure and worker-only application withdrawal, preserving records.
- [x] Owner-only job editing before the first application; terms lock once an applicant relies on them.
- [x] Submission, revision, dispute freeze and pre-funding cancellation.
- [x] Explicitly simulated USDC and bank/card workflows, with repeated approval protection.
- [x] Separate non-custodial wallet controls from the platform payment record.
- [x] Participant-only project inbox and message sending with desktop/mobile layouts.
- [x] Server-side permissions, CSRF checks, password hashing and security headers.
- [x] Remove video/glass from this new workspace; original website preserved separately.
- [x] Automated tests and desktop/mobile preview inspection.
- [x] Dedicated database-backed deployment health check at `/healthz/`.
- [x] Fail-fast production configuration and release-readiness validation.
- [x] Official Stellar testnet Horizon endpoint and USDC issuer verified against current Stellar documentation.
- [x] Supabase connectivity, migration state and live Stellar Horizon connectivity checked.

## Information required from the founder

1. **Operating country and initial customer countries.** These determine which payment providers can support receiving funds and paying workers. A card checkout alone does not establish a worker-payout service.
2. **Business/account owner.** Confirm whether an existing registered business will operate the service. Provider onboarding and verification must be completed by that owner.
3. **Launch budget ceiling.** Local development needs no paid service today. Production domain, email, hosting, backups and transaction costs require a current quote before purchase; no indefinite free-operation promise is made.
4. **Rules of the marketplace.** Agree fees, revision limits, acceptance deadlines, cancellation/refund rules and who resolves disputes. No platform fee has been invented or charged.
5. **Brand/domain.** Confirm a cleared product name and domain before publishing; “Push” is a working name. The earlier research identified an existing Push Protocol brand.

Do not send private keys, seed phrases, card numbers or API secrets in chat. When providers are chosen, enter credentials directly into protected server settings.

## Implementation gates before accepting real users or money

- [ ] Choose supported bank/card collection and worker-payout services; implement provider-hosted sensitive payment forms.
- [x] Implement a non-custodial Freighter connection for a Stellar testnet public address and verify direct test-USDC settlement evidence through Horizon.
- [ ] Choose the production USDC network, regulated cash-out provider and supported countries. Stellar is the implemented testnet route; Arc and Solana remain future alternatives. See `../push-stellar-path.md`.
- [ ] Build separate payment adapters with authenticated, replay-resistant webhooks, reconciliation and verified settlement. Never mark a real payment successful because the browser says so.
- [ ] Test duplicate, delayed and out-of-order notifications, failed payouts, refunds, chargebacks and network failures in provider sandboxes.
- [ ] Define dispute resolution and an audited support interface. Preview disputes currently remain frozen.
- [ ] Set up a verified email sender and HTTPS email API on Render Free (see `EMAIL-SETUP.md`), then test real invitation, verification and recovery delivery.
- [ ] Provision production hosting, TLS, restricted hosts, secret storage, static serving, trusted proxy configuration and deployment rollback.
- [ ] Replace local SQLite with the chosen production database; retest concurrency and permissions against it. Current tests do not prove distributed concurrency behaviour.
- [ ] Configure edge/distributed request limits and monitoring. Current database/IP throttling is for the local foundation and can group users behind the same proxy.
- [ ] Add administrator MFA, least-privilege support access, incident response and credential rotation procedures.
- [ ] Implement account deletion/export, retention policy, moderation and abuse handling before collecting real user data.
- [ ] Define project ownership verification. A typed project name in the preview is not proof of affiliation; team memberships are not implemented.
- [ ] Agree post-cancellation behaviour for the pilot. Basic pre-application editing, closure and withdrawal are implemented, but reopening and resubmission are not. A cancelled preview assignment is terminal; republish a new job to restart.
- [ ] Validate email-length/storage constraints and accessibility across supported browsers, keyboards and screen readers.
- [ ] Back up production data securely, test restoring it, and schedule expired-session/rate-limit cleanup.
- [ ] Obtain an independent security review, fix material findings, and run a small invited pilot before public launch.

## Cost and scope boundaries

This preview runs on the founder's computer with open-source dependencies and no paid API. It does not establish that hosting or payment processing will be free. Live payment cost estimates must follow country/provider/network selection and expected transaction volume. Building a second unrelated product solely for a grant is not part of this implementation.
