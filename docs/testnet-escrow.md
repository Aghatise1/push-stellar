# Disabled testnet escrow integration

This release connects the new workroom and named staff-review workflow, but defaults `PUSH_TESTNET_ESCROW_ENABLED` to false and the contract setting to empty. It does not enable escrow on the public site or support mainnet. Existing assignments retain their original flow; the migration defaults `escrow_required` to false.

## Implemented

- New assignments use escrow only when explicitly configured and enabled. An incomplete enabled configuration blocks selection rather than silently selecting a simulated payment route.
- Client selects a non-participant, approved owner/admin/Trust & Support reviewer with a distinct public testnet wallet. Worker sees the pinned wallets, reviewer, amount, asset and terms before acceptance. XLM requires a separate price acknowledgement.
- The client signs atomic contract creation and funding. Application state advances only after successful ledger confirmation; insufficient funds do not unlock work.
- Worker signs delivery, client signs release or bounded revision; either participant can dispute. The pinned reviewer signs a full release, refund or whole-token split. Existing moderator simulation and direct-payment endpoints cannot settle escrow assignments.
- Separate review period starts with delivery; revision creates a fresh delivery window. Contract enforces overdue-delivery refund and post-review worker claim. Disputed funds cannot use normal release/expiry routes.
- Exact prepared envelope and expected wallet signature are checked. Signed requests are stored before broadcast; retries reuse the same hash. Expired requests are cleared only when RPC history covers the whole possible inclusion period. Uncertain results remain blocked.
- Job selector supports test USDC or XLM behind the feature flag. XLM records are labelled explicitly and excluded from dollar-labelled aggregates; the payment page shows separate XLM totals.

## Verified

Public evidence is in `contracts/deployments/testnet-escrow.json`. A disposable 1-test-XLM agreement completed funding, delivery and release through the application's builder/signature validator and deployed contract. A second completed funding, dispute and reviewer-authorised full refund. CLI identities remained local and ignored; no signing secrets were added to the application or repository.

Application tests cover role separation, disabled routes, worker acknowledgement, exact signature matching, failed/pending transactions, idempotent confirmation, legacy settlement isolation, expiry-history coverage and separate token totals. Contract tests cover insufficient balance rollback, missing authorisation, duplicate payout protection, disputes, refunds, review periods and revisions.

## Required before enabling the shared testnet pilot

1. Exercise test USDC end to end with the official configured testnet issuer and funded disposable accounts, including trustline/receiving-limit failures.
2. Exercise the actual Freighter browser approval/cancellation flow end to end. The recorded live checks used CLI signatures from disposable wallets; they are not evidence of a tested browser extension flow.
3. Nominate an eligible staff reviewer and confirm their public wallet and availability. The disposable QA arbiter is not a production staff appointment.
4. Validate migrations, concurrent requests and rollback on a separate staging database; exercise unavailable RPC and delayed confirmation recovery.
5. Establish recovery for externally advanced contract state, stale RPC history, archived contract storage and unavailable reviewer keys. The application currently blocks these uncertain cases for manual reconciliation rather than guessing payment outcomes.
6. Review the security implications of staff access: revoking app access prevents signing through Push but does not revoke an address already pinned in an on-chain agreement. A reviewed key-management/recovery policy is required.
7. Confirm public product/help/terms copy accurately describes the enabled pilot. This disabled release does not claim active public escrow.

Only after these checks should a controlled testnet deployment set `PUSH_TESTNET_ESCROW_CONTRACT` to the verified contract and explicitly enable the flag. Check `/healthz/` for the effective flag and release. Never configure a mainnet RPC or real assets.

## Before mainnet

Independent contract/application security review, legal review of escrow and dispute authority, reviewed terms, operational monitoring, storage lifetime/recovery, reviewer key governance and incident procedures are required. No platform fee or fee recipient has been specified or implemented. No automatic migration of existing assignments is provided. This contract prototype is not independently audited.
