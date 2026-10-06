# Push testnet contracts

The current escrow implementation is `push-escrow-staff`. It accepts the configured test XLM and official test USDC asset contracts, locks funds before work, and uses individually authorised staff wallets for disputes. `push-escrow` and `push-milestone` remain historical versions; existing agreements keep their original authority.

Build the current version with `stellar contract build --package push-escrow-staff`; test all versions with `cargo test --locked --workspace`.

The staff contract constructor requires `owner`, `xlm` and `usdc` addresses. The owner is fixed for this testnet version. `set_staff(actor, wallet, role)` uses roles 0 (revoked), 1 (reviewer), 2 (administrator); the constructor owner is role 3. Administrators can manage reviewers; only the owner can manage administrators. `resolve(id, reviewer, client_amount, worker_amount)` requires that reviewer's signature and current contract permission, and rejects client/worker conflicts. Every split goes only to the agreement's original wallets.

Public disposable QA evidence, including Django endpoint tests, is in `deployments/testnet-staff-escrow-qa.json`. **That QA owner is not the live Push owner.** Register the real owner's wallet through Operations > Escrow signing access before deploying a distinct live-testnet instance and enabling it. No private key belongs in server settings.

Simulation/direct-payment actions have been retired in the application. New assignments require escrow, and payment controls remain unavailable until the staff contract is configured and activated. Mainnet is unsupported. These contracts have not received an independent security audit. See `../docs/testnet-transition-plan.md` for activation and recovery limitations.

## Historical milestone contract

`push-milestone` is a Soroban testnet contract for one funded freelance milestone. The client creates and funds an agreement, the worker records a delivery hash, and the client can release the exact locked amount. Expired or disputed agreements have explicit refund, claim and arbiter-split paths.

The contract never stores private keys. Every client, worker and arbiter action requires the corresponding Stellar address to authorise the invocation. State is updated before token transfers, terminal states cannot pay twice, and dispute splits must equal the originally funded amount.

## Status

The historical milestone contract is deployed and its create → fund → submit → approve lifecycle was exercised on Stellar testnet. Deployment evidence is in `deployments/testnet.json`. It is retained for historical evaluation, not used for new staff-governed agreements.

## Build and test

Install Rust 1.84 or newer, the `wasm32v1-none` target, and Stellar CLI 28 or newer. From this directory:

```text
cargo test -p push-milestone
stellar contract build --package push-milestone
```

The compiled WASM is generated under `target/` and is intentionally excluded from version control. Rebuild it from the reviewed source rather than trusting a binary attachment.

## Contract methods

- `create`: client creates an unfunded agreement with distinct client, worker and arbiter addresses.
- `fund`: client transfers the exact token amount into the contract.
- `submit`: worker records a 32-byte delivery hash.
- `approve`: client releases the full amount to the worker.
- `cancel_unfunded`: client cancels before any assets move.
- `refund_expired`: client recovers an unsubmitted funded milestone after its deadline.
- `claim_expired`: worker claims submitted work after the review deadline.
- `open_dispute`: either participant freezes a funded or submitted agreement.
- `resolve`: arbiter pays an exact client/worker split without creating value.
- `get`: reads the current agreement.

Testnet assets have no monetary value. Do not use this deployment for real funds.
