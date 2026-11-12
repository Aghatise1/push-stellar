# Push architecture and financial state flows

Updated 12 November 2026. This document describes the deployed Stellar testnet pilot. Test assets have no monetary value. It is not a mainnet readiness claim or a security audit.

## System architecture

```mermaid
flowchart LR
    Client[Client browser] -->|Jobs, applications, workroom, evidence| Web[Push Django application]
    Worker[Worker browser] -->|Acceptance, delivery, messages| Web
    Staff[Authorised human reviewer] -->|Dispute review and permitted settlement request| Web

    Web -->|Private application records| DB[(PostgreSQL)]
    Web -->|Prepare unsigned transaction| SDK[Stellar SDK and RPC adapter]
    SDK --> RPC[Stellar testnet RPC and Horizon]

    Client -->|Approve with own wallet| Wallet[Stellar wallet]
    Worker -->|Approve with own wallet| Wallet
    Staff -->|Approve with authorised reviewer wallet| Wallet
    Wallet -->|Signed transaction| Network[Stellar testnet]
    Network --> Contract[Soroban escrow contract]
    Contract --> Tokens[Test XLM or test USDC]
    RPC -->|Confirmed transaction and contract state| Web

    Web -->|Verification and recovery email| Email[Brevo]
    Web -->|Health and release metadata| Render[Render deployment]
```

### Trust boundaries

1. Push stores accounts, job information, accepted terms, private messages, delivery references and reconciled transaction records off chain.
2. Push does not request or store wallet private keys or recovery phrases. The relevant participant approves each transaction in their own wallet.
3. Stellar testnet is the source of truth for submitted transaction status and contract state. A button press alone never marks an agreement as funded or paid.
4. Routine release is approved by the client. Push staff do not approve every payment.
5. Disputes remain human decisions. Only an authorised reviewer wallet may sign a contract permitted release, refund or split, and a staff member who is a party to the agreement may not decide it.
6. Private work evidence remains off chain. Public addresses, amounts and contract actions remain visible on Stellar.

## Financial state model

```mermaid
stateDiagram-v2
    [*] --> AwaitingWorkerAcceptance: Client selects worker
    AwaitingWorkerAcceptance --> AwaitingFunding: Worker accepts preserved terms
    AwaitingWorkerAcceptance --> Cancelled: Unfunded agreement cancelled

    AwaitingFunding --> PreparingFunding: Client requests unsigned transaction
    PreparingFunding --> AwaitingFunding: Wallet rejects or preparation expires
    PreparingFunding --> Funded: Signed transaction confirmed on Stellar

    Funded --> Submitted: Worker signs delivery submission
    Submitted --> Funded: Client requests permitted revision
    Submitted --> Released: Client signs routine release

    Funded --> Disputed: Participant raises dispute
    Submitted --> Disputed: Participant raises dispute
    Disputed --> Resolved: Human reviewer signs release, refund or split allocation

    Funded --> Refunded: Authorised expiry refund transaction
    Submitted --> Released: Authorised expiry claim transaction

    Released --> [*]
    Refunded --> [*]
    Resolved --> [*]
    Cancelled --> [*]

    note right of Resolved
      Contract state is Resolved.
      Worker and client amounts record
      the settlement allocation.
    end note
```

## Financial controls

| Control | Current behaviour | Evidence location |
| --- | --- | --- |
| Asset and amount | Agreement pins an exact supported asset and token amount before funding | `core/escrow.py`, contract source and escrow tests |
| Wallet authority | Server prepares transactions; the participant or authorised reviewer signs | `core/escrow_views.py`, `core/escrow_staff.py` and wallet JavaScript tests |
| Confirmation | Application records state only after Stellar confirmation and contract reconciliation | Escrow service code and transaction records |
| Duplicate protection | Preparation reservations and idempotent reconciliation prevent concurrent duplicate actions | `core/test_escrow.py` and `core/test_escrow_staff.py` |
| Disputes | Human reviewer signs only a contract permitted settlement to the original participant wallets | Staff escrow contract and staff permission tests |
| Network fee | Fee is shown separately from escrow value and rejected above the configured safety limit | Escrow preparation tests and testnet deployment record |
| Testnet disclosure | UI and documentation state that test assets have no monetary value | Templates, README and public pilot |

## Deployed pilot

The deployed application is [https://pushearn.xyz](https://pushearn.xyz). On 12 November 2026 its health endpoint returned HTTP 200, `stellar-testnet`, `escrow_enabled: true` and release `a60af23e1bcf`.

The current recorded testnet contract is `CAO6VET6JK73QW4IJOIFCECYACWIZMC7GZK4I3G43ECSFQMCHGEKT3G5`. Its deployment and QA metadata are recorded in `contracts/deployments/testnet-owner-escrow-v4.json`.
