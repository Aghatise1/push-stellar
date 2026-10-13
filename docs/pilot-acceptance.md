# Browser acceptance checklist

Updated 13 October 2026 using the supplied 12 October browser recording. This is a partial evidence record, not a completed acceptance signoff. No item is marked passed merely because code exists. Use disposable testnet assets and separate client, worker and staff accounts. Record date, release, browser, asset, transaction hash, expected result and actual result. Never record recovery phrases, secret keys or session cookies.

| Check | Expected result | Browser result |
| --- | --- | --- |
| Connect and reject approval | Rejection shows a recoverable message; no funding state change | Pending |
| Disconnect and reload | Saved address is not presented as an active signing session | Pending |
| Wrong network or different wallet | Clear recovery instruction; signing blocked | Pending |
| Missing worker wallet or shared address | Correct person identified; agreement cannot silently use another address | Pending |
| Accept an agreement | Asset, amount and wallets remain fixed; no automatic debit | Observed in recording: acceptance precedes a separate funding action. Wallet immutability and balance behaviour were not independently verified. |
| Fund with test XLM | Correct signer approves; one confirmed deposit unlocks work | Pending |
| Fund with test USDC | Correct token and receiving prerequisites checked | Observed in recording: a 100 test USDC agreement proceeds through funding to ready for work. Issuer, transaction hash and receiving prerequisites still need an evidence check. |
| Insufficient balance or receiving capacity | No false success or unlocked work | Pending |
| Repeat submit or refresh while pending | No duplicate transfer; status can be checked | Pending |
| Worker delivery and client release | Worker receives the agreed token amount after confirmation | Observed in recording: delivery, release processing and a completed agreement; displayed earnings change from 87 to 187 test USDC. Recipient and amount still need reconciliation against a recorded transaction hash. |
| Revision | Allowed revision updates workflow without releasing tokens | Pending |
| Dispute and actual owner signature | Ordinary release blocked; authorised resolution pays only agreed wallets | Pending |
| Staff permission grant and revoke | Application role and chain permission both enforced | Pending |
| Staff as a participant | Reviewer cannot settle their own work | Pending |
| Expired delivery refund and expired review claim | Contract timing and signer enforced; no automatic payout | Pending |
| RPC outage or uncertain submission | Pending or error state stays honest; do not send a replacement blindly | Pending |
| Mobile and keyboard navigation | Controls, addresses and errors remain visible and usable | Pending |

Existing command line transaction evidence is under `contracts/deployments/`. It is not a substitute for these Freighter browser checks. The user's successful wallet connection is acknowledged; it does not prove the remaining payment paths.

## Recording evidence and limits

Source: `Screen Recording 2026-10-12 203808.mp4`, supplied by the founder, duration 7 minutes 7 seconds. The recording is a local review asset, not a public repository attachment. Times below are approximate positions in the original recording, not the edited video.

| Original recording position | Observed interface activity |
| --- | --- |
| 0:00 to 2:30 | Job creation, application and worker selection |
| 3:10 to 3:20 | Worker agreement acceptance before funding |
| 3:30 to 4:00 | Project communication |
| 4:10 to 5:00 | Test USDC funding and transition to ready for work |
| 5:10 to 5:50 | Delivery submission and wallet interaction |
| 6:00 to 7:07 | Release processing, completed agreement and updated earnings display |

These observations establish a demonstrated normal browser path, not an independent chain reconciliation. The release commit, browser version, exact transaction hashes, issuer and final wallet balances were not captured in this checklist. Record those before promoting the observations to fully verified acceptance results. No XLM browser path, completed staff dispute settlement, negative case or recovery scenario is marked passed by this recording.
