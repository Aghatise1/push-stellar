# Push system design

This is the controllable operating model for Push. It describes who can do what, which records are created, how those records change and which launch decisions remain blocked. `PRODUCT-RULES.md` contains the public policy; this document is the internal blueprint.

## Product boundary

Push is a marketplace and work-record system for Web3 teams and independent workers. It covers discovery, agreement, delivery, review, disputes and settlement evidence. It does not issue a token, store private wallet keys or claim to provide production escrow in the current build.

The Django application in this folder is the canonical product. The original static site at `C:\Users\USER\Desktop\push-protocol-landing` is source material and an archive, not a second application to maintain.

## People and authority

### Visitor

- May read the product pages, operating rules, public profiles and open briefs.
- May create an account or sign in.
- Cannot post, apply, accept work or change an assignment.

### Member

- Uses one account for hiring and independent work.
- Must verify their email before marketplace actions.
- Controls whether their profile is public.
- Cannot apply to a brief they own.

### Hiring participant

- Creates and edits a brief until the first application arrives.
- Reads private proposals submitted to their brief.
- Selects one available applicant.
- Selects the payment route after the worker accepts.
- Reviews a delivery, requests a revision, approves it or opens a dispute.

### Worker participant

- Applies once to an eligible brief and may withdraw while it remains open.
- Accepts or rejects the preserved assignment terms.
- Submits evidence against the agreed deliverables.
- Responds to revision requests or opens a dispute.
- Supplies a receiving address only for a payment route that needs one.

### Future operator

- Trust & Support handles member questions, reports, prohibited content, fraud and dispute administration from one protected case workspace.
- Must use logged, role-limited tools. Direct database edits are not an acceptable operating process.
- Cannot silently alter a preserved brief, proposal, assignment event or payment record.

## Core records

| Record | Purpose | Visibility | Mutability |
| --- | --- | --- | --- |
| Account | Authentication and private identity | Owner and authorised operators | Member-editable fields; security fields server-controlled |
| Profile | Skills, bio, portfolio and payment destination | Private by default; public by explicit choice | Owner editable |
| Brief | Project, outcome, deliverables, category, budget and deadline | Public while listed | Editable until first application; then preserved |
| Application | A worker's private proposal | Applicant and hiring account | Withdrawable while open; retained as history |
| Assignment | Preserved scope, participants, budget and status | Participants and authorised operators | State changes only through allowed actions |
| Submission | Delivery notes and external evidence link | Assignment participants | Append-only record |
| Event | Who did what and when | Assignment participants and authorised operators | Append-only |
| Payment | Settlement method, amount and verification reference | Participants and authorised operators | Created once; transaction reference unique |
| Message | Work discussion attached to one assignment | Selected worker and hiring participant only | Append-only; sender and time are preserved |
| Dispute | Reason, evidence, status and resolution | Participants and authorised operators | Append-only evidence; controlled status changes |
| Community post | Skill exchange, collaboration, questions and progress | Verified members; staff for moderation | Author may close/reopen; staff may remove after a report |
| Community reply | Constructive response attached to one community post | Verified members; staff for moderation | Append-only during the pilot |
| Community report | Private safety concern about a post | Reporter and authorised operators | One open record per reporter and post; resolved through Trust & Support |

## Brief and application state rules

```text
draft -> open -> assigned -> completed
            \-> closed
```

- A published brief needs a title, project, category, description, deliverables, positive budget and future deadline.
- The first valid application freezes the published terms.
- Closing blocks new applications and selection but retains existing applications.
- Selecting one non-withdrawn application atomically closes selection and creates one assignment.
- Sample briefs are visibly labelled and cannot accept applications.

## Assignment state machine

```text
awaiting_acceptance
  -> awaiting_funding
      -> funded
          -> submitted
              -> funded       (specific revision requested)
              -> paid         (approved and settlement recorded)
              -> disputed
          -> disputed
      -> cancelled
  -> cancelled
```

Every state change requires the current state, actor and action to match. The server rejects stale or duplicate actions.

| Action | Actor | Required state | Result |
| --- | --- | --- | --- |
| Accept scope | Worker | Awaiting acceptance | Awaiting funding |
| Cancel before payment route | Either participant under policy | Awaiting acceptance/funding | Cancelled |
| Select payment route | Hiring participant | Awaiting funding | Funded |
| Submit work | Worker | Funded | Submitted |
| Request revision | Hiring participant | Submitted | Funded |
| Approve | Hiring participant | Submitted | Paid/completed |
| Open dispute | Either participant | Funded/submitted | Disputed |

## Payments

The product uses a payment-route abstraction so marketplace logic does not depend on one chain.

- **Stellar XLM/USDC testnet:** the server builds an exact, short-lived transaction; Freighter signs it; the server rejects altered envelopes, submits it to Horizon and records the confirmed hash.
- **Soroban milestone contract:** implemented and deployed on testnet for transparent evaluation, but disabled in the web application's custody path until independent security review.
- **Generic USDC:** simulated until a production wallet/provider and network policy are selected.
- **Bank/card:** simulated until a regulated provider and country scope are selected.

Amount comes from the assignment, recipient from the worker profile, and one transaction hash can settle only one assignment. A chain payment must match network, asset/issuer, recipient, amount, unique assignment memo and success status. No private key, recovery phrase or service credential belongs in browser code or version control.

The wallet page links a public Stellar address. Freighter proves control when it signs each payment, and the server verifies that signature against the connected address before submission. Manually entering an address alone is still not proof of ownership. Push has no internal wallet balance to withdraw; future bank cash-out requires a regulated provider.

The original concept proposed a 12.5% platform fee. That figure is preserved as research history, not an active rule. Before launch, Push must decide the fee, payer, charging point, refund treatment and disclosure.

## Disputes

The current build records a dispute and freezes normal approval. Production needs an evidence window, independent reviewer or named provider, decision standard tied to scope, partial-payment and refund outcomes, an appeal rule and logged operator actions. Until those exist, Push must not advertise guaranteed dispute resolution.

## Reputation

- Only completed, attributable assignments may affect reputation.
- Sample, testnet and production activity must be distinguishable.
- Reviews should be bilateral and available only after completion.
- Purchased reviews, self-dealing, wash activity and paid ranking must not contribute.
- Portable credentials may reference verified events without requiring a Push token or NFT.

## Security and privacy

- Authentication, authorisation and state validation happen on the server.
- Email and proposals remain private; profile publication is opt-in.
- Credentials load from environment configuration.
- Write actions use CSRF protection, rate limits and database transactions where state races matter.
- Production needs managed secrets, HTTPS, secure cookies, backups, monitoring, dependency updates and an independent security review.
- Retention, export and deletion periods require a written privacy policy before launch.

## Product surfaces

| Surface | Purpose |
| --- | --- |
| Home | Core promise, four-stage overview and current sample briefs |
| Product | Original mission, problem, solution, roles, comparison, roadmap, FAQ and founder context |
| How it works | Public operating rules and current limitations |
| Opportunities | Searchable working preview of briefs |
| Account and profile | Identity, privacy and payment destination |
| Workspace | Owned briefs, applications and assignments |
| Wallet | Linked public address, testnet send/receive request, earnings and payment record |
| Assignment | Scope, private participant messages, status, submissions, revisions, disputes and payment evidence |
| Community | Verified-member collaboration, skill exchange, questions, progress and Stellar builder conversations |

## Launch gates

1. Choose initial countries and legal operator.
2. Select production bank/card and stablecoin providers.
3. Decide whether Push remains non-custodial or introduces regulated escrow.
4. Approve the fee and refund policy.
5. Combined Trust & Support case and dispute operations.
6. Complete privacy, terms and prohibited-work policies.
7. Complete threat modelling, penetration testing and incident response.
8. Run a small invitation-only pilot before a public marketplace launch.
