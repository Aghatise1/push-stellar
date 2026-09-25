# Push security baseline

This checklist applies to the private prototype and every future deployment.

## Secrets

- Keep signing keys, email credentials, OAuth client secrets and payment-provider secrets in the deployment environment.
- Never place a secret in HTML, JavaScript, screenshots, documentation, a database fixture or a committed environment file.
- Public identifiers such as an OAuth client ID still need provider-side restrictions.
- Rotate any credential previously published in frontend source. Deleting it from a file does not revoke it.
- `private-demo-credentials.txt`, `.env`, `.local-key`, local databases and development mail are excluded from version control.

## Authentication

- Email/password accounts use Django's password hashing and validation.
- Registration, login, password reset and verification endpoints are rate-limited.
- Password reset credentials expire and become invalid after use.
- Sessions are HTTP-only, same-site and expire when the browser closes.
- Google sign-in must use an approved OAuth callback, exact allowed origins and a server-side client secret. It remains disabled until real credentials are configured.

## Authorisation

- Workspace, profile, posting, applications and assignments require authentication.
- Posting, applying and assignment changes also require verified email.
- Every record-specific action checks ownership or participation on the server.
- A guessed URL returns login or not-found rather than private data.
- State changes use POST and CSRF protection.

## Payments

- Push does not collect recovery phrases or private wallet keys.
- Browser input cannot replace the assignment amount or recipient.
- Testnet and simulated records must remain visibly distinct from production money.
- Production Paystack, card or stablecoin integrations require webhook verification, idempotency, provider key restrictions and a security review.

## Before any public deployment

1. Scan the working tree and repository history for credentials.
2. Rotate every credential that has ever appeared in browser code or shared archives.
3. Use HTTPS, secure cookies and a managed secret store.
4. Configure exact hosts, origins and OAuth callbacks.
5. Add production monitoring, backups, dependency scanning and incident response.
6. Run an independent penetration test focused on account recovery, object access and payment verification.
