# Push escrow workflow and Orbio design

## Objective

Repair excessive testnet escrow fees, reduce repeated agreement actions, keep workrooms current without manual refreshes, and add optional Orbio assistance without changing who controls money or disputed settlements.

## Product rules

1. Posting a job never transfers tokens. The worker and final terms are not known yet.
2. Selecting a worker creates the application agreement automatically when both saved wallets are ready.
3. The worker confirms the scope, fixed token amount, deadlines, wallet and XLM volatility notice when applicable.
4. The client funds only after worker acceptance. Stellar confirms the deposit before Push marks the work funded.
5. Normal release remains a client signed action. It does not require staff approval.
6. Every disputed settlement remains a human decision and a transaction signed by an authorised staff wallet.
7. Orbio may draft scope, summarise activity, organise evidence and recommend escalation. It cannot verify chain state, choose a worker, approve a profile, decide a dispute, or sign a transaction.
8. Existing agreements remain bound to their recorded contract. A new contract identifier applies only to new agreements.

## Contract fee repair

The current contract extends every agreement entry to a fixed thirty day lifetime. Testnet simulation measured an approximately 11.1 XLM maximum fee and approximately 9.66 XLM charged for a one XLM deposit. The application correctly rejected that transaction.

The next contract version will calculate storage lifetime from the agreement deadline and review period with a bounded safety margin. It will avoid refreshing completed records for another fixed thirty days. Tests will prove live agreements retain enough lifetime and closed agreements do not receive unnecessary extension. A disposable testnet deployment must demonstrate the prepared and charged fee before the application is reconfigured.

The one XLM safety limit remains a protection. It may only change after a measured fee budget is documented. The interface will distinguish the escrow amount from the network fee.

## Simplified workflow

Selection attempts to create the off chain escrow agreement immediately. If either participant has no valid saved wallet, the workroom explains exactly whose wallet is missing and creates the agreement as soon as the client returns after both wallets are ready. The worker sees one acceptance action. The client then sees one funding action.

The server owns all state transitions. A small authenticated status endpoint returns a version derived from assignment, escrow and latest event state. The workroom checks it only while visible and reloads when the version changes. Transaction submission continues to use its existing idempotent reconciliation path.

## Orbio boundary

Orbio is disabled by default and configured only on the server. The request contains the minimum workroom text required for the selected assistant action. Responses use a validated structured shape with a summary, observations, missing information, suggested next step and an escalation flag. The interface labels the output as an AI draft requiring human review.

Stellar Horizon and Soroban remain the only source of truth for transaction and contract state. Push staff remain the source of profile approval. An authorised human reviewer remains the source of every disputed release, refund or split.

## Compatibility and release

No existing agreement rows are rewritten. Historical simulated payment records remain read only. New behaviour is covered by contract and Django tests. Deployment occurs only after contract tests, application tests, release checks and a disposable testnet fee measurement pass.
