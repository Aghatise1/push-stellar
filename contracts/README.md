# Push milestone contract

`push-milestone` is a Soroban testnet contract for one funded freelance milestone. The client creates and funds an agreement, the worker records a delivery hash, and the client can release the exact locked amount. Expired or disputed agreements have explicit refund, claim and arbiter-split paths.

The contract never stores private keys. Every client, worker and arbiter action requires the corresponding Stellar address to authorise the invocation. State is updated before token transfers, terminal states cannot pay twice, and dispute splits must equal the originally funded amount.

## Status

The contract is deployed and its create → fund → submit → approve lifecycle has been exercised on Stellar testnet. Deployment evidence is in `deployments/testnet.json`. It has automated contract tests, but it has **not** received an independent security audit. Push therefore publishes it for testnet evaluation while keeping contract-held payments disabled in the web application. The current wallet flow sends test assets directly from Freighter.

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
