# Browser acceptance checklist

Prepared for the next supervised test session. No item is marked passed merely because code exists. Use disposable testnet assets and separate client, worker and staff accounts. Record date, release, browser, asset, transaction hash, expected result and actual result. Never record recovery phrases, secret keys or session cookies.

| Check | Expected result | Browser result |
| --- | --- | --- |
| Connect and reject approval | Rejection shows a recoverable message; no funding state change | Pending |
| Disconnect and reload | Saved address is not presented as an active signing session | Pending |
| Wrong network or different wallet | Clear recovery instruction; signing blocked | Pending |
| Missing worker wallet or shared address | Correct person identified; agreement cannot silently use another address | Pending |
| Accept an agreement | Asset, amount and wallets remain fixed; no automatic debit | Pending |
| Fund with test XLM | Correct signer approves; one confirmed deposit unlocks work | Pending |
| Fund with test USDC | Correct token and receiving prerequisites checked | Pending |
| Insufficient balance or receiving capacity | No false success or unlocked work | Pending |
| Repeat submit or refresh while pending | No duplicate transfer; status can be checked | Pending |
| Worker delivery and client release | Worker receives the agreed token amount after confirmation | Pending |
| Revision | Allowed revision updates workflow without releasing tokens | Pending |
| Dispute and actual owner signature | Ordinary release blocked; authorised resolution pays only agreed wallets | Pending |
| Staff permission grant and revoke | Application role and chain permission both enforced | Pending |
| Staff as a participant | Reviewer cannot settle their own work | Pending |
| Expired delivery refund and expired review claim | Contract timing and signer enforced; no automatic payout | Pending |
| RPC outage or uncertain submission | Pending or error state stays honest; do not send a replacement blindly | Pending |
| Mobile and keyboard navigation | Controls, addresses and errors remain visible and usable | Pending |

Existing command line transaction evidence is under `contracts/deployments/`. It is not a substitute for these Freighter browser checks. The user's successful wallet connection is acknowledged; it does not prove the remaining payment paths.
