# Push escrow workflow and Orbio implementation plan

Spec: `docs/superpowers/specs/2026-10-24-push-escrow-workflow-orbio-design.md`

## Global constraints

Preserve existing escrow agreements and their contract identifiers. Preserve unrelated working tree changes. Use tests before production changes. Keep all token movements wallet signed. Keep disputed settlements human signed. Keep Orbio disabled until credentials and an explicit environment flag are present.

## Task 1: Repair agreement storage lifetime

Add contract tests for deadline based lifetime and terminal state behaviour. Replace fixed agreement lifetime extension with calculated lifetime based on the active agreement deadlines. Build and run the complete contract suite. Deploy a disposable testnet contract and measure a one XLM create and fund transaction. Do not activate it unless the fee is materially lower and within the application guard.

## Task 2: Make agreement creation automatic

Add Django tests proving selection automatically creates an agreement when wallets and staff authority are ready, preserves a clear recovery path when they are not, and never moves tokens at job posting or selection. Extract one agreement creation service and use it from selection and the workroom recovery action. Remove the redundant visible preparation step when no recovery is needed.

## Task 3: Add workroom state synchronisation

Add tests for an authenticated participant only status endpoint and stable version changes. Add visible tab polling to the workroom and reload only when another request changes state. Keep transaction reconciliation idempotent.

## Task 4: Add guarded Orbio assistance

Add tests for disabled configuration, input limits, structured response validation, and failure without state changes. Add a server only Orbio client and optional workroom actions for scope, delivery and dispute summaries. Label all output as advisory. Do not expose any transaction action to the assistant.

## Task 5: Documentation, validation and deployment

Update environment documentation and product wording. Run the full Django suite, contract suite, deployment checks and browser checks. Deploy the measured contract version, configure new agreements to use it, deploy the application, then verify the public health endpoint and the escrow workroom. Existing agreements must continue to point to their original contract.

## Review focus

Review token authority, transaction idempotency, contract lifetime calculations, old agreement compatibility, access control on status and assistant endpoints, privacy of Orbio inputs, and any path that could let AI trigger or decide a payment.
