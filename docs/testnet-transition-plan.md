# Push testnet-only implementation plan

Requested 6 October 2026. No mainnet or real-money launch.

## Already exists

Disabled Soroban escrow, fixed XLM/USDC terms, worker acceptance, reviewer signing, ledger confirmation, history and access controls. XLM happy-path and dispute refund were verified on the deployed testnet contract.

## Change now

1. Remove simulated payment choices and reject simulation writes server-side. Preserve old records without counting them as testnet earnings.
2. New assignments always require escrow. If escrow configuration is unavailable, show a specific setup status; never fall back to simulation.
3. Give unfunded legacy assignments an explicit conversion action that resets acceptance and requires both sides to accept pinned escrow terms. Do not convert settled or already-paid records, discard evidence, or imply an old simulation funded a contract.
4. Offer test USDC and test XLM. Show fixed token units everywhere; separate balances and earnings per asset. Preserve the XLM volatility acknowledgement and a concise testnet/no-monetary-value notice.
5. Check funded accounts, asset balances and recipient USDC trustlines before funding. Transaction preparation additionally enforces network reserve, fee and token rules.
6. Reconcile known prepared/pending transaction hashes without asking users to sign a new transfer. Uncertain or externally changed state blocks further writes and remains visibly pending for staff investigation.
7. Improve wallet review, rejection, timeout, retry and confirmation messaging. Add setup guidance for official faucets and USDC trustlines.
8. Replace obsolete no-escrow and simulated-cash banners, public workflow explanations and dashboard totals with truthful descriptions of the deployment state. Historical simulation receipts remain marked as such.
9. Validate tests, mobile layouts, real testnet USDC, Freighter signing and staging behaviour before enabling the shared pilot. Deploy source changes through CI and verify the live feature flag.

## Required human configuration

The deployment owner registers their own testnet wallet in Operations > Escrow signing access, proving ownership with a signature that is never broadcast. Deploy the staff-governed contract with that verified address as its initial owner. Owner/Admin/Trust & Support staff register their own wallets. The owner grants administrator permissions; owner or administrators grant/revoke reviewer permissions through wallet-signed contract calls. Push roles alone do not grant on-chain authority. No shared private wallet or QA key becomes the live authority. Staff who are parties to an agreement cannot resolve it. Existing v1 agreements retain their original authority; new v2 agreements use the staff registry.

## Recovery and release constraints

No automatic payouts from web timers: the appropriate wallet signs a contract call. Dispute decisions are explicit releases/refunds/splits. Existing signed contract authority cannot be revoked merely by changing an app role. Unavailable reviewer keys, expired ledger history and external contract actions must be handled without inventing settlement records. Keep mainnet unsupported; security/legal/key-governance review remains a separate prerequisite for real money.

## Definition of done

No reachable simulation-write path; no fake earnings mixed into token totals; no work marked funded before ledger confirmation; exact asset/amount/recipient verified; tested funding/release/refund/dispute paths; explicit pending/error recovery; UI and backend agree on the enabled state; CI passes and live release matches the tested revision.

## Verification completed in this revision

- Separate `push-escrow-staff` contract; v1 source and deployed agreements preserved.
- Real testnet XLM funding, signed delivery and release.
- Real testnet USDC funding, dispute and support-wallet split.
- Actual on-chain staff grant, revocation, rejected revoked settlement and re-grant.
- Django endpoint flow with disposable accounts: wallet proof, staff grant, client configuration, worker acceptance, funding, delivery/release and support dispute settlement. Evidence: `contracts/deployments/testnet-staff-escrow-qa.json`.
- Responsive staff, funding, dispute and payment screens at 320, 768 and 1280 CSS pixels: no document overflow.
- Application and Rust tests; PostgreSQL concurrency check included in CI.

## Still required before live pilot activation

1. Publish this revision so the actual owner can register their wallet through the UI.
2. Owner verifies their own wallet in Freighter. The agent cannot supply that identity or sign on their behalf.
3. Deploy a distinct live-testnet contract with that owner and the pinned test XLM/USDC contracts; set `PUSH_TESTNET_ESCROW_STAFF_CONTRACT` and enable `PUSH_TESTNET_ESCROW_ENABLED` after readiness checks.
4. Confirm the real browser/Freighter approval path. Gateway and endpoint tests use disposable CLI signing; these do not substitute for an extension interaction test.

Funding activation is not completed by committing this code. Mainnet, commercial/legal readiness, independent security audit, ownership-key recovery/rotation, appeal policy and automated externally initiated transaction reconciliation remain outside this activation. Unknown ledger state fails closed. The constructor owner is fixed in this version; losing that key requires a migration/recovery design, not a database edit.
