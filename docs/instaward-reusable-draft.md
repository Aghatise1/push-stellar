# Push Instaward application draft

Prepared 7 November 2026. Retired as an application source on 11 November 2026 after the Stellar Chile review and local implementation of several proposed repairs. Do not reuse its deliverables or budget. Use `docs/grant-readiness.md` to prepare a new chapter-specific application from the current code baseline.

## Supporting material

White paper: https://docs.google.com/document/d/1rtl4VK15nmiBkLZCah9iXeS6-VoHz_eJUXVdigwQ1Zc

Existing hackathon demonstration: https://drive.google.com/file/d/1kuU1SbJthnghDpW5ZiHo9W5kjBGhoepH/view

Website: https://pushearn.xyz

Repository: https://github.com/Aghatise1/push-stellar

Verify reviewer access to the document and video. The white paper is a general project document, without a grant budget or dated sprint commitment.

## Builder

Name: Aghatise Ehioghae

Chapter: Stellar Nigeria, subject to the programme's chapter rules.

Enter the current monitored email and personally verified public Stellar receiving address in the actual form. Never use a secret key. Verify the award network and asset. A prior testnet address is not automatically an appropriate award receiving address.

## Project

Push: Stellar Escrow Reliability and Pilot Validation

Proposed funding: USD 5,000. Start date: choose after confirming availability and the award process. Duration: no more than 30 days, if required by that round.

## Problem and objective

Freelance work often happens across disconnected job boards, messaging applications, file sharing tools and payment services. This makes it difficult for clients and workers to establish what was agreed, whether the work is funded, what was delivered and how disagreements should be resolved.

Push brings these records into one shared workroom and connects the agreement to Stellar Soroban escrow. Clients fund accepted agreements, workers submit delivery evidence, and clients sign routine payment releases. Authorised human reviewers handle disputed settlements.

Push already has a working Stellar testnet MVP supporting test XLM and test USDC. The current blocker is making this workflow consistently reliable and easy to verify across separate client, worker and reviewer accounts. Remaining work includes request limiting behind the hosting proxy, email verification safeguards, transaction handling during slow network responses and clearer operational monitoring.

The objective of this 30 day sprint is to address these reliability issues and validate funding, delivery, release, refund and dispute workflows. Completion evidence will include automated regression tests, documented testnet transactions, an updated demonstration and a clear report of results and remaining limitations. This will prepare Push for a better controlled pilot and provide evidence for future mainnet readiness work.

## Deliverable 1: Application security and transaction reliability

Correct request limiting behind the hosting proxy, close the email verification retry bypass, and shorten database transactions that currently include external Stellar network calls. Add bounded network timeouts and regression tests covering verification abuse, independent user limits and interrupted transaction processing.

Evidence: public GitHub commits or pull requests, automated test results, and a verification report explaining repaired behaviours and remaining limitations. Publishing requires separate authorisation.

## Deliverable 2: Verified Stellar escrow workflows

Validate funding, signed delivery and client release with both test XLM and test USDC using separate client and worker accounts. Exercise refund and disputed settlement paths, including an authorised human reviewer. Confirm that retries do not create duplicate application settlements and that unauthorised accounts cannot perform restricted actions.

Evidence: a test matrix, public testnet transaction links and contract addresses, automated permission and reconciliation tests, and a recorded demonstration of participant and reviewer journeys.

## Deliverable 3: Pilot deployment and operating guide

Deploy verified improvements to the testnet pilot, add application error and health monitoring, and document deployment, recovery and dispute support procedures. Publish reviewer instructions and an updated acceptance checklist identifying passed checks and unresolved issues.

Evidence: deployed pilot URL, release commit, demonstration of health and error reporting without private data, and operating and reviewer documentation.

## Out of scope

Mainnet deployment, real money payments, fiat deposits and withdrawals, onramp and offramp integrations, native mobile applications, a full redesign and broad public launch are excluded. AI will not gain authority over hiring, payment approval or dispute decisions. Human reviewers retain responsibility for disputed settlements.

An independent smart contract audit and legal assessment are outside this budget. Record remaining readiness requirements without claiming that Push is audited or ready for real money use.

## Proposed budget

Total: USD 5,000.

Deliverable 1: USD 2,000 for implementation and regression testing.

Deliverable 2: USD 1,800 for escrow testing, evidence collection and demonstration.

Deliverable 3: USD 900 for deployment engineering, monitoring configuration and documentation.

Infrastructure and tools: USD 300 for sprint hosting, database, monitoring and development tools across all deliverables.

These are planning allocations, not supplier quotations. Engineering allocations compensate the builder for implementation, testing and documentation. Testnet tokens are free; no funds are allocated to buying them. Confirm actual spending intentions before submission. Existing MVP work is not being reimbursed.

## Execution plan

Week 1: Confirm the code and deployment baseline, reproduce issues and define acceptance checks. Repair proxy aware request limiting and verification retry abuse. Add regression tests and an initial verification report.

Week 2: Reduce database lock duration around Stellar calls and add bounded timeouts. Test slow responses, interrupted requests, retries and duplicate submissions. Keep uncertain transactions pending until confirmation.

Week 3: Execute the escrow test matrix with separate participant and reviewer accounts. Validate both assets, refunds, disputes and access controls. Collect transaction evidence and resolve failures.

Week 4: Deploy verified improvements, check hosted workflows, configure monitoring, complete operating and reviewer instructions and record the demonstration. Publish evidence and remaining limitations. Reserve the final two days for regression checks and evidence review.

## After the sprint

Intended selection: Apply to SCF Build Award, subject to eligibility.

Use sprint results to strengthen a future application with the improved testnet MVP, transaction evidence, test results and remaining work. Continue pilot feedback and define security, operational and legal preparation before mainnet.

## Acknowledgements to verify each time

The November form required completion within 30 days, execution focused outcomes, no more than two follow on Instawards, a USD 5,000 award cap and USD 15,000 total Instawards cap. These are a record of that form, not guaranteed future rules. The applicant must read and accept the actual KYC and eligibility requirements and disclose previous awards accurately.
