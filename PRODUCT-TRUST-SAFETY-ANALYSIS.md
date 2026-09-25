# Push trust, payment and moderation analysis

Source: the approximately 30-minute conversation supplied on 25 September 2026. The transcript contains overlapping speech and dictation errors, so this document normalises the intended product concepts rather than treating every phrase literally.

## Executive conclusion

The conversation identified Push's real product problem: a freelance marketplace needs to protect both sides of a digital job.

- A client can fund a job and receive nothing or receive unusable work.
- A freelancer can deliver valid work and face dishonest rejection or non-payment.
- Either party can exploit vague requirements.
- Bad actors can return under new accounts.
- Fake, discriminatory, impossible or low-quality job posts can waste applicants' time.

Payment alone does not solve these problems. Push needs a connected trust workflow: a structured brief, preserved terms, staged funding, evidence-bearing communication, explicit delivery, a response deadline, dispute review and proportionate sanctions.

## Normalised terminology

The transcript moves between employer, employee, customer, producer, A and B. Push should use:

- **Client**: the person or organisation buying a defined service.
- **Freelancer**: the independent person delivering it.
- **Brief**: the original job description.
- **Agreement**: the accepted scope, price, milestones and deadline.
- **Funded amount**: money committed through an approved payment or escrow partner.
- **Delivery**: the freelancer's submitted work and evidence.
- **Acceptance criteria**: observable conditions used to judge whether the agreement was met.
- **Moderator**: an authorised human who reviews disputes using the record.

“Employee” should be avoided unless Push is deliberately creating employment relationships. The proposed model is independent contracting.

## What the conversation decided well

### 1. The trust problem is bilateral

The discussion correctly rejected the simple assumption that only freelancers can scam clients. A dishonest client can take a design, video or document, claim it is unsatisfactory and refuse to pay. Every rule must therefore be symmetric.

### 2. Money should not go directly to the freelancer before delivery

The proposed “50% inside the app” is an early description of milestone escrow. The important idea is that committed funds remain unavailable to either party until a defined event occurs. Sending 50% directly to the freelancer does not provide the same protection.

### 3. The original requirements must be preserved

Moderation is impossible when the brief is vague or can be edited later. Push already has the right foundation: freeze the agreed scope, budget, deadline and acceptance criteria when an assignment begins.

### 4. Work communication must stay attached to the assignment

The requested chat system is not merely messaging. It is evidence. Questions, approvals, revision requests, delivery links and deadline changes should remain inside the workroom with timestamps.

### 5. Human review is necessary for contested cases

AI can flag suspicious listings, missing fields, prohibited content and unreasonable requirements. It should not make final payment decisions in subjective creative disputes. A trained human should review the evidence and written agreement.

### 6. Fraud cannot be eliminated, only made harder and less profitable

This is the most realistic statement in the conversation. Push needs deterrence, traceability and recovery procedures rather than a promise of perfect safety.

## Ideas that need correction

### “Pay 50%” is incomplete

The unanswered question in the recording—who decides where the 50% goes—is exactly the escrow problem. A percentage does not determine whether delivery was valid. Push needs release rules and dispute authority.

A better future model is milestone funding:

1. The client funds a milestone through a licensed payment or escrow provider.
2. The freelancer sees that funding is confirmed before starting.
3. The freelancer submits a preview and delivery evidence.
4. The client accepts, requests a permitted revision, or opens a dispute within a response window.
5. No response triggers a clearly disclosed automatic release process.
6. A dispute pauses release until a moderator decides release, refund or split.

Push should not hold real customer money itself until legal, custody, reconciliation and licensing questions are resolved.

### A moderator on every job will not scale

Reviewing every brief and every delivery manually would create long delays and a large payroll before Push has revenue. Human moderation should be reserved for flagged listings, appeals and disputes. Routine jobs should pass deterministic validation and automated risk checks.

### A mandatory one-day listing delay is too blunt

Good listings should be publishable quickly. Use immediate structured validation, risk scoring and a moderation queue for suspicious cases. High-risk or first-time posters can receive additional review.

### BVN and NIN collection is premature and high-risk

Raw identity documents create security, privacy and regulatory responsibilities. They also increase abandonment and do not guarantee honest behaviour. If stronger identity checks become necessary, use a licensed identity-verification provider and store only the verification result and provider reference. Do not store raw BVN, NIN or document images in Push.

Start with progressive verification:

1. Verified email or trusted Google identity.
2. Verified phone number.
3. Public wallet or payment-method verification where relevant.
4. Completed work history and mutual reviews.
5. Enhanced identity checks only for higher limits, suspicious activity or regulated payment features.

Device and network risk signals can support fraud detection, but must be disclosed, protected and never treated as certain proof that two people are the same.

### An acknowledgement checkbox is not automatically an NDA

The proposed checkbox should initially confirm that the freelancer read the scope and accepts the platform rules. A legally useful NDA requires proper terms, parties, jurisdiction and consent. Push can later provide an optional agreement template reviewed by counsel.

### Do not promise a 70% or 90% chance of getting work

Push cannot honestly guarantee job success without controlling demand, applicant quality and client selection. Better positioning is: “clearer briefs, credible work records and fewer wasted applications.”

### “The client cannot cancel” is too absolute

Cancellation needs explicit states:

- Before selection: client may close the listing.
- After agreement but before funding: either party may cancel under stated rules.
- After funding but before work: cancellation may refund the client, possibly minus an agreed fee.
- After work begins: cancellation requires milestone compensation or dispute review.
- After delivery: the client must accept, request a valid revision or dispute; silent cancellation is not permitted.

## Recommended dispute system

The moderator should judge compliance with the written agreement, not personal taste.

### Evidence available to the moderator

- Frozen brief and acceptance criteria.
- Accepted proposal and price.
- Milestones and deadlines.
- In-app messages and change approvals.
- Submitted previews, links, file hashes and timestamps.
- Revision requests and responses.
- Funding and payment references.
- Prior account conduct, used carefully and without prejudging the case.

### Decision options

- Release the funded milestone to the freelancer.
- Refund the client.
- Split the funded amount when only part of the milestone was completed.
- Permit one final revision with a deadline.
- Cancel without penalty where both parties agree.
- Apply account warnings, temporary restrictions or bans for proven misconduct.

### Case states

`open → awaiting evidence → under review → decision issued → resolved`

There should eventually be an appeal route for high-value cases, but one-level administrator review is sufficient for the MVP demonstration.

## Preventing stolen creative work

The conversation identifies a client receiving usable work and then refusing payment. Product controls should reduce that opportunity:

- Allow watermarked or lower-resolution previews before release.
- Let freelancers withhold editable source files until acceptance or payment release.
- Record file hashes and submission timestamps.
- Keep client feedback and revision requests in the workroom.
- Limit revisions in the agreement.
- Require disputes to identify which acceptance criterion allegedly failed.

These controls are more effective than asking a moderator to make a purely subjective quality judgement.

## Job-listing quality

Different work categories require different structured fields. A video-editing brief and a UI/UX brief should not use identical requirements.

Every brief should contain:

- Desired outcome.
- Deliverables and formats.
- Examples or references.
- Required skills.
- Evidence applicants may provide, including personal or practice work.
- Budget and payment route.
- Milestones and deadline.
- Number of included revisions.
- Acceptance criteria.
- Usage rights and confidentiality needs.

Automated checks should flag impossible experience requirements, discriminatory language, requests for unpaid speculative work, missing budgets, external-payment pressure, suspicious links and prohibited services. A moderator reviews only flagged or reported listings.

## Recommended MVP scope

### P0 — needed for a credible hackathon or investor demonstration

1. Structured briefs with category-specific fields.
2. Immutable agreement snapshot after selection.
3. In-app workroom with messages and timestamps.
4. Milestone status: agreed, funded/simulated, in progress, submitted, revision, approved, disputed and resolved.
5. Delivery evidence with links and file metadata.
6. Client response deadline.
7. Human-admin dispute screen with release/refund/split simulation.
8. Account warnings and bans.
9. Email/Google verification and basic abuse rate limits.
10. Clear labels that current payments are simulated or Stellar testnet.

### P1 — after the workflow is proven

1. Mutual reviews after completed assignments.
2. Phone verification.
3. Watermarked previews and controlled source-file release.
4. Automated listing risk checks and reporting tools.
5. Notifications for proposals, funding, delivery, revisions and disputes.
6. Moderator queues, case assignment and internal notes.

### P2 — requires legal, financial and operational preparation

1. Real milestone escrow through a licensed partner.
2. Bank/card and stablecoin settlement with webhooks and reconciliation.
3. Enhanced identity verification through a specialist provider.
4. Appeals and a larger moderator operation.
5. Portable on-chain completion credentials.
6. Advanced duplicate-account and device-risk analysis.

## Monetisation recommendation

Start the invited beta free. A listing fee would reduce the number of jobs at the exact moment Push needs liquidity. Advertising would damage trust and distract from the workflow.

When real settlement exists, test a transparent success fee only on completed paid work. The final percentage must be based on payment-provider costs, dispute staffing, refunds, fraud losses and competitor pricing. The proposed 10–12.5% was rejected in the conversation without a cost model; a smaller percentage may feel better but still cannot be chosen responsibly until those costs are known.

Possible later revenue:

- Completion fee on successfully settled milestones.
- Optional client subscription for team tools and higher limits.
- Optional freelancer subscription for analytics or portfolio tools, never for basic access to work.
- Enhanced verification or expedited dispute service where legally appropriate.

## Decisions still required

1. Is the initial market Nigerian creators and digital freelancers, or a global Web3-first audience?
2. Which two or three work categories will the MVP support deeply?
3. Will real payments first use bank/card, existing stablecoins, or both?
4. Which licensed provider can hold or conditionally release funds in the target countries?
5. What response period triggers escalation or automatic release?
6. Who has authority to resolve the first disputes?
7. What evidence formats can Push safely store?
8. Which misconduct causes a warning, suspension or permanent ban?

## Recommended immediate build order

1. Add acceptance criteria, milestones, revision allowance and cancellation terms to the brief/agreement.
2. Make the agreement immutable once accepted.
3. Finish the workroom message and delivery-evidence flow.
4. Add dispute creation with evidence and explicit case states.
5. Build a small administrator moderation dashboard.
6. Simulate release, refund and split decisions; do not hold real money yet.
7. Add mutual reviews only after a completed assignment.
8. Test the complete workflow with two client accounts, two freelancer accounts and deliberate failure cases.
9. Measure where testers become confused before adding KYC, AI judgement or real custody.

## Product statement derived from the discussion

**Push helps clients and independent talent agree on the work, keep the evidence together and complete payment with a clear record.**

This is stronger and more defensible than promising guaranteed jobs. It describes the problem the conversation repeatedly returned to: trust between agreement and settlement.
