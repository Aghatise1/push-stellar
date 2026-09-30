# Push product rules

This document is the current operating model for the Push prototype. It separates rules already enforced in software from decisions that still require product, legal, financial and operational work.

## Product promise

Push gives hiring teams and independent workers one shared record from a clear brief through delivery and settlement. Push does not issue a token. The product should make the next action, the current terms and the evidence behind every final status easy to inspect.

## Roles and accounts

- One person may hire and work from the same account.
- A person cannot apply to their own job.
- Email verification is required before posting, applying or managing an assignment.
- Profiles are private until their owner publishes them.
- Email addresses, proposals and assignments are never displayed on public profiles.
- A future identity-verification programme must be optional until a specific payment, risk or regulatory requirement makes it necessary.
- Internal operations use three roles: Owner, Administrator, and a combined Trust & Support role.
- Trust & Support handles member tickets, reported listings, account context and disputes from one case workspace.
- Only the Owner may preview another operations workspace; assigned staff permissions never change through the interface.

## MVP technology boundaries

- The invited pilot remains on Stellar testnet; mainnet and real-money custody are outside the current release.
- Push does not embed an AI assistant, AI job reviewer or AI dispute decision-maker in this MVP.
- The LLM Council used during product planning is a private development workflow and is not a Push user feature.
- Large delivery files and videos use external links during the pilot. Push records the link and delivery evidence but does not host video.

## Job and application rules

- A brief must state the project, title, category, description, deliverables, budget and deadline.
- An open brief can be edited only before the first application arrives.
- Once anyone applies, the brief becomes read-only so the considered terms cannot be silently changed.
- One worker can submit one application per brief.
- A worker may withdraw an application while the brief remains open. The record is retained and cannot be resubmitted in the prototype.
- A hiring account may close an unassigned brief. Existing applications remain in the private record.
- Selecting one applicant closes the brief to other selections and creates one assignment.

## Assignment rules

- Selection creates a preserved assignment containing the accepted scope and budget.
- The worker must accept the assignment before a payment route is selected or work is submitted.
- The hiring account selects the payment route.
- In the current prototype, bank/card and generic USDC are simulations. Stellar USDC uses testnet only.
- The worker submits delivery notes and may attach an external work link.
- The hiring account may request a specific revision, returning the assignment to work-in-progress.
- Approval is terminal for the assignment and marks the job complete.
- Repeated approval, duplicated selection and invalid state changes are rejected by the server.

## Payment rules

- Push never requests or stores a wallet recovery phrase or private key.
- The browser cannot change the agreed assignment amount during approval.
- Stellar testnet settlement must match the assignment recipient, exact amount, official testnet USDC issuer, unique memo and successful transaction status.
- A Stellar transaction hash can settle only one assignment.
- Push does not currently provide escrow or hold user funds.
- Mainnet payments remain blocked until provider selection, jurisdiction review, error recovery, refunds, monitoring and an independent security review are complete.

## Disputes and cancellations

- Either participant may raise a dispute after the payment route is selected and before approval.
- A dispute freezes normal approval and settlement.
- The current prototype records disputes but does not decide them.
- An assignment may be cancelled only before the payment route is selected.
- Future dispute policy must define evidence deadlines, reviewer independence, appeals, partial payment, refunds and abandoned work.

## Reputation and marketplace integrity

- Reputation should be calculated only from completed, attributable activity.
- Written ratings should be allowed only after a real completed assignment and should be available to both parties.
- Paid ranking, purchased reviews, wash activity and self-dealing must not influence marketplace status.
- Public metrics must distinguish test, sample and production activity.
- Moderation rules must prohibit fraud, impersonation, unlawful work, harassment, malware and requests for credentials.

## Decisions still required before launch

1. First launch countries and the legal entity operating Push.
2. Production bank/card provider and stablecoin wallet/on-ramp partners.
3. Whether Push ever provides escrow or remains a non-custodial workflow and verification layer.
4. Platform fee, payer, refund treatment and fee disclosure.
5. Dispute-resolution operator and service-level targets.
6. Identity, sanctions and transaction-monitoring obligations by country and payment route.
7. Privacy retention periods, account deletion and legal-request handling.
8. Customer support channels, incident response and payment recovery.

These unresolved decisions are launch gates, not features to improvise during development.
