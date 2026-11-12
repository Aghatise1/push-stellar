# Push Instaward Statement of Work draft

Updated 12 November 2026. Intended for the next verified Stellar Nigeria Instaward round. Do not submit it to another chapter. The founder must confirm the start date, availability, hourly rate, wallet address and all form declarations.

## Project

**Project name:** Push: Stellar escrow mainnet readiness sprint

**Duration:** 30 days

**Requested funding:** USD 5,000 equivalent in XLM

**Work basis:** 100 hours at USD 50 per hour

## Problem and objective

Push has a working Stellar testnet freelance escrow pilot, public source code, concurrency protection and recorded XLM and test USDC lifecycle evidence. The current contract has a fixed deployment owner. Existing agreements are pinned to their recorded contract, and there is no tested two step path to transfer authority to a replacement owner without weakening reviewer controls.

The 30 day objective is to implement a two step owner transfer in a new contract version, integrate that version without rewriting existing agreements, add a privacy safe chain evidence and mismatch review tool, and complete current owner wallet acceptance. The sprint will finish on testnet. Mainnet activation remains gated by an independent contract review and legal and operational approval.

## Why Stellar and why testnet

Push uses Stellar Smart Contracts to hold the exact asset and amount attached to an accepted work agreement and to restrict release, refund, expiry and disputed settlement to permitted signers. Stellar wallets let clients, workers and authorised reviewers approve their own actions without Push receiving private keys. Public transactions let a reviewer verify that application state corresponds to on chain state.

Testnet is necessary for this sprint because authority transfer, contract version routing and reviewer signed settlement can affect custody. The work must be exercised with separate wallets and test assets before any value bearing asset is enabled. Mainnet is a later gated release, not a promised outcome of this award.

## Differentiation and prior art

Trustless Work provides reusable Stellar escrow infrastructure, while Eascrow has presented escrow for goods and freelance work. Push does not claim that escrow itself is unique. Push's differentiation is the complete work record around it: job discovery, applications, preserved scope, private project communication, delivery evidence, revisions and human reviewed dispute context connected to agreement specific Stellar settlement.

## Deliverables

### 1. Two step contract owner transfer

Add `propose_owner`, `accept_owner` and `cancel_owner_transfer` operations to a new staff escrow contract version. Only the current owner may propose or cancel a transfer, only the proposed address may accept it, and reviewer and administrator roles must remain unchanged. The transfer must not alter any agreement, participant wallet, asset, amount or settlement state. Document that this supports planned key rotation but does not recover an owner key that was lost before a transfer was proposed.

**Evidence:** public pull request; Rust tests for authorisation, cancellation, acceptance and state preservation; deployed testnet contract ID; owner proposal, acceptance and post transfer role transaction links.

**Hours:** 32

### 2. Versioned application integration and rollback

Integrate the new contract version so it applies only to agreements created after an explicit configuration change. Preserve every existing agreement's recorded contract. Add predeployment checks for owner, supported token contracts and network; record the contract version on new agreements; and document a rollback that stops new v5 agreements without rewriting funded work.

**Evidence:** public pull request; application tests proving old agreements keep their contract and new agreements use v5; deployment record; configuration and rollback rehearsal; public testnet health and release metadata.

**Hours:** 24

### 3. Privacy safe chain evidence and mismatch review

Add a management command that verifies confirmed escrow actions against Stellar RPC and exports a reviewer safe JSON manifest containing contract, network, asset, action, transaction hash and final contract state while excluding identities, messages and delivery evidence. Extend the existing database only pilot reliability queue with verified Stellar contract state and flag records whose application state does not agree with it. The queue must not automatically retry, sign or decide a payment.

**Evidence:** public pull request; tests for redaction, RPC verification, malformed records and access control; sample manifest from disposable agreements; demonstrated mismatch record and documented human recovery procedure.

**Hours:** 26

### 4. Current owner wallet acceptance and release pack

Using separate client, worker, current owner, proposed replacement owner and reviewer wallets, execute owner transfer, reviewer grant and revoke, routine release, an expiry path and a human signed dispute settlement on the new testnet contract. The replacement owner must be distinct from every reviewer used in the matrix. Exercise test XLM and test USDC across the matrix. Repair only defects found in the new contract and integration, then publish the resulting technical release evidence.

**Evidence:** deployed commit and contract; explorer links naming network, contract, asset, signer role, action and final state; complete acceptance matrix; health result; final deployment and rollback checklist.

**Hours:** 18

## Budget

| Deliverable | Hours | Rate | Cost |
| --- | ---: | ---: | ---: |
| Two step contract owner transfer | 32 | USD 50 per hour | USD 1,600 |
| Versioned application integration and rollback | 24 | USD 50 per hour | USD 1,200 |
| Privacy safe chain evidence and mismatch review | 26 | USD 50 per hour | USD 1,300 |
| Current owner wallet acceptance and release pack | 18 | USD 50 per hour | USD 900 |
| **Total** | **100** |  | **USD 5,000** |

The budget is engineering labour only. It does not include marketing, promotional media, general user acquisition, an onramp or offramp integration, or work already completed before the sprint.

## Execution plan

### Week 1

Confirm the current contract and application baseline. Write failing owner transfer tests, implement the two step transfer and prove agreement and staff role state is preserved.

### Week 2

Add versioned application routing, deployment checks and rollback controls. Deploy a disposable v5 testnet candidate and execute owner proposal and acceptance with separate wallets.

### Week 3

Build the redacted evidence exporter and staff only mismatch queue. Test RPC verification, redaction, access control and the prohibition on automated financial actions.

### Week 4

Deploy the release candidate. Execute the current owner wallet acceptance matrix, rehearse rollback and publish the final contract, transaction, test and release evidence.

## Out of scope

1. Mainnet activation or handling assets with monetary value.
2. Marketing, promotional content, user acquisition or paid pilot recruitment.
3. Onramp, offramp, bank or fiat integration.
4. AI decisions about worker selection, disputes or payments.
5. Rebilling security, licence or reliability work already completed before the sprint.
6. A claim of independent security certification. Any external review remains a separate mainnet gate.

## Completion standard

The sprint is complete only when each deliverable has a public commit, a reproducible verification result and reviewer accessible evidence. Testnet transaction links must name the contract, asset, signer role, action and final state. Screenshots and prose alone do not count as proof of a financial transition.
