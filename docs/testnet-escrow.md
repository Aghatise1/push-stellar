# Wallets and testnet escrow

Current staff governed implementation, updated 9 October 2026. This replaces the earlier disabled integration guide. Configuration controls availability; never infer activation from a saved address.

## Three separate states

1. Connection is the current Push signing session. Disconnect ends that session; Freighter may retain its site permission separately.
2. Ownership verification is a saved signed proof linking a staff wallet to an account. It survives disconnect and does not mean currently connected.
3. Contract activation and permission determine whether the configured escrow is available and a staff wallet may act. Verification alone does not grant permission.

Staff reconnect requires a fresh signed proof checked locally, never broadcast. Push never requests private keys or recovery phrases. Staff and customer wallet sessions are separate. Staff use separate customer accounts for freelance work.

## Funding and settlement

New testnet assignments use escrow with separate participant wallets and test XLM or test USDC. The client signs funding after agreement acceptance. Acceptance alone cannot debit a wallet. Only confirmed chain evidence advances the funding state.

The worker signs delivery. The client signs release or a permitted revision. Staff do not approve routine payments. Contract disputes block ordinary release until an authorised staff wallet resolves the case. Settlement can only pay the original participant wallets. Expiry refund and claim paths require an authorised signed transaction and contract timing checks; time alone does not move tokens.

Wallet addresses are pinned to the agreement. Changing a profile cannot change a funded agreement. Cancel and prepare a new unfunded agreement if its wallets are incorrect.

## Staff authority

App role, active account, verified email, wallet proof and chain permission all matter. Owner is role 3, administrator role 2, reviewer role 1 and revoked role 0. Only the owner grants administrator authority. Administrators manage reviewers. Participants cannot review their own agreements.

App suspension blocks application access. Removing chain authority requires a separately signed revocation. Owner rotation is not implemented. Staff wallet replacement is not automatic. A recovery procedure must not be claimed until implemented and tested.

## Configuration and evidence

Testnet only mode uses PUSH_TESTNET_ESCROW_ENABLED and PUSH_TESTNET_ESCROW_STAFF_CONTRACT. Defaults remain conservative. The deployed staff contract is recorded in contracts/deployments/testnet-owner-escrow.json with owner and XLM/USDC lifecycle hashes. Earlier deployment files are historical evidence.

The pilot was previously enabled on Render. Recheck /healthz/ and deployment settings before a demonstration; this document is not a live health check. Never use mainnet assets in the pilot.

## Verification limits

Recorded QA transactions used command line signatures. Actual owner dispute signing and complete Freighter browser acceptance remain outstanding. See [acceptance checks](pilot-acceptance.md). Uncertain submissions remain pending for reconciliation and must not be blindly replaced or marked paid.

See [security readiness](security-readiness.md) before real money use. No platform fee or staff compensation system is specified here.
