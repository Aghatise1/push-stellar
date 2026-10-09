# Push ecosystem and architecture

## Purpose

Push connects clients with independent workers and keeps the agreed brief, project communication, delivery evidence and payment state in one workflow. The pilot uses Stellar testnet. Test assets have no monetary value; participation does not promise earnings or employment.

A concrete use case is a client commissioning a design from a worker they have not previously hired. They agree a deliverable and budget, the client funds contract escrow, the worker submits the design, and the client signs release. If they disagree, authorised staff review the evidence and sign an allowed settlement. This is an illustrative workflow, not a claim of customer demand.

## System boundaries

| Component | Responsibility | Not responsible for |
| --- | --- | --- |
| Django application and database | Accounts, access, private messages, scope snapshots, delivery links, prepared transactions and audit records | Holding private wallet keys or deciding blockchain success from a button click |
| Freighter | User approval and wallet signatures | Automatically approving jobs or resolving disputes |
| Stellar RPC and Soroban contract | Contract simulation, submission, confirmation, token escrow and authorised state changes | Judging whether creative work satisfies a brief |
| Horizon | Classic Stellar account and payment queries used by the wallet integration | Replacing Soroban contract state verification |
| Owner, Admin, Trust & Support | Review disputed work within granted permissions | Reviewing every routine deposit or client approval |

Messages and private documents stay in the application. Public blockchain activity includes addresses, amounts and contract interactions. A private workroom does not make its blockchain transfers private. Never put private delivery content or personal details into public transaction metadata.

## Agreement and settlement

1. A client posts a brief and selects a worker. The worker accepts preserved terms.
2. The agreement pins separate valid client and worker addresses, asset, amount, delivery deadline, review window and revision limit. Both parties must understand the asset before funding.
3. The client connects the matching testnet wallet and approves the prepared funding transaction. Acceptance alone cannot debit a wallet.
4. Push records funding only after confirmed chain evidence. The worker should not treat an unconfirmed request as funded.
5. The worker submits delivery evidence and signs the contract submission. The client can approve release or request an allowed revision.
6. Either participant can raise a contract dispute in an allowed state. Ordinary release is then blocked. An authorised staff wallet signs a release, refund or split to the original participants.
7. Contract expiry paths require an authorised signed transaction. A clock reaching a deadline does not automatically send tokens.

## Why Stellar

The contract makes the deposit and permitted settlement transitions verifiable independently of Push's interface. XLM and USDC use the configured testnet token contracts. This ties payment evidence to a particular work agreement. Stellar does not guarantee work quality or remove human judgement from disputes.

## Current scope and future decisions

The pilot supports test XLM and test USDC, not real money. XLM amounts are token amounts, not fixed dollar values. USDC test assets are not redeemable dollars. Mainnet deployment, real payment services, local currency rails, platform fees and legal operating scope need separate decisions and review. No proprietary Push token is required.

## Implementation map

Read `core/escrow_views.py` for agreement preparation and requests, `core/escrow_policy.py` for action permissions, `core/escrow.py` for chain operations, `core/escrow_records.py` for reconciliation, and `core/escrow_staff.py` for staff proof and permission management. The current contract is `contracts/contracts/push-escrow-staff/src/lib.rs`. Earlier contracts remain historical implementations and must not be confused with the staff governed deployment.
