# Push grant readiness

Updated 11 November 2026 from Tellus feedback, the Builders Circle discussion described by the founder, the current repository and public primary sources. This is an internal preparation document. It is not an award application, legal opinion or proof of completion.

## What reviewers asked us to correct

| Requirement | Current position | Required action | Evidence for the next application |
| --- | --- | --- | --- |
| Correct chapter | Stellar Chile declined the November application mainly because the applicant listed Stellar Nigeria | Apply through Stellar Nigeria or obtain written cross-chapter eligibility before submission | Link or message showing the eligible round and chapter |
| Open-source licence | MIT licence added locally with Aghatise Ehioghae as the copyright holder | Commit and push `LICENSE` and the README licence notice to the public repository | GitHub licence detection, exact commit and repository link |
| Budget with hours and rate | The previous budget used broad allocations | Price each engineering deliverable as hours multiplied by an honest hourly rate. Add infrastructure only when it has a real cost and purpose | Table whose hours, rates and costs sum exactly to the request |
| Stellar-specific scope | Previous reliability work could apply to many web applications | Centre the application on contract state, wallet signatures, transaction reconciliation, asset handling, ledger evidence and mainnet gates | Contract tests, transaction links, deployment record and demo |
| Why testnet and mainnet path | The pilot is testnet only and no dated transition was supplied | Explain that testnet protects users while contract roles, failure recovery and end-to-end signing are validated. Give evidence gates for mainnet rather than a decorative date | Completed gate checklist and links to each result |
| Prior art and differentiation | Competitors were not discussed | Cite Trustless Work and Eascrow accurately. Explain Push at the application and work-coordination layer | Sourced comparison and a concrete user workflow |
| Proof of work | Previous evidence risked being abstract | Every deliverable must end in a reviewer-verifiable artefact | Public commit, reproducible test, deployed address, explorer transaction, demo or operating document |
| Form quality | Deliverable 1 was duplicated | Use one source document, run a final duplication and link check, then compare the review page against it | Final application PDF or screenshots and a checked source copy |
| No promotion inside the build plan | Builders Circle guidance excludes marketing and promotional content | Keep application deliverables technical and operational. Do not budget for campaigns, promotional videos, user acquisition or general marketing | Deliverables map only to code, tests, deployment and technical documentation |
| No generic onramp or offramp scope | Builders Circle guidance says this category is overrepresented | Exclude onramp and offramp integrations from this application | Explicit out-of-scope statement |

## What Push is

Push is a work-coordination application for clients and independent workers. It keeps the job brief, application, accepted scope, private project communication, delivery evidence, revisions, disputes and payment state in one workroom. A client can hire on one job and work for another client on the next.

Push uses Stellar for the part that should be independently verifiable: agreement-bound token escrow and authorised settlement. The application keeps private work context off-chain. The contract holds test assets, records permitted state transitions and restricts release, refund and dispute settlement to the appropriate signers.

## Why Stellar

Push needs more than a payment button. It needs a client to lock an exact asset and amount for a specific accepted agreement, a worker to signal delivery, a client to release routine payment, and an authorised human to sign a constrained settlement if a dispute occurs. Stellar Smart Contracts provide programmable token custody and role-based transitions, while wallets let each participant approve their own action without Push storing secret keys.

Stellar also provides public transaction and contract evidence that a reviewer can inspect independently of the Push interface. Push uses test XLM and test USDC to test distinct asset behaviour. It does not require a proprietary token. Private messages and delivery material stay in the application because public ledgers are unsuitable for confidential work evidence.

Public Stellar material describes smart contracts as infrastructure for financial applications and wallet integration. Trustless Work demonstrates that Stellar supports reusable single-release and milestone escrow patterns. Push therefore should not claim that escrow on Stellar is unique. Its case must explain the application workflow and target user problem around the contract.

## Why testnet now

The product is on testnet because contract authority, wallet-session separation, uncertain transaction recovery, asset configuration, fee behaviour, dispute signing and operational recovery still need controlled validation. Test assets prevent development failures from placing real customer funds at risk.

Mainnet should be described as a gated transition, not a promised date. The minimum gates are:

1. Complete separate-account browser evidence for funding, delivery, release, refund and human-signed disputes for both supported assets.
2. Run real PostgreSQL concurrency tests and repair any failure.
3. Resolve the preparation-reservation expiry race identified during independent review.
4. Verify deployed proxy identity configuration, monitoring, backups and a restore exercise.
5. Complete an independent smart-contract security review and address material findings.
6. Document contract owner and reviewer key recovery, rotation and incident response.
7. Complete legal and operational review for the launch jurisdictions and payment model.
8. Rehearse a mainnet release and rollback procedure before enabling assets with monetary value.

## Stack and architecture

| Layer | Current technology | Responsibility |
| --- | --- | --- |
| Web application | Python, Django, Django templates, JavaScript and CSS | Accounts, jobs, applications, workrooms, permissions, evidence and prepared transaction flows |
| Application hosting | Render with Waitress | Runs the Django service; live settings must be verified separately |
| Persistent application data | Supabase PostgreSQL through Django ORM | Accounts, agreements, messages, events and reconciled transaction records |
| Wallet approval | Stellar wallet integration, currently Freighter-oriented | Participant signatures without Push receiving secret keys |
| Smart contracts | Rust and Stellar Smart Contracts SDK | Escrowed token custody, agreement state and authorised transitions |
| Chain access | Stellar RPC and Horizon through the Stellar SDK | Contract simulation, submission, confirmation, account and balance queries |
| Email | Brevo HTTPS delivery from the hosted application | Verification and recovery messages |
| Testing | Django tests, Rust contract tests and JavaScript tests | Permission, state, validation and wallet-session behaviour |

## Prior art

### Trustless Work

Observed from its official documentation on 11 November 2026: Trustless Work provides an API for creating and managing Stellar escrow contracts, with single-release and multi-release patterns. It supports roles, milestones, funding, approval, disputes, resolution and release on testnet and mainnet.

Source: https://docs.trustlesswork.com/trustless-work/api-rest/introduction

### Eascrow

Observed from its Stellar Community Fund submission and Stellar ecosystem listing on 11 November 2026: Eascrow was funded as a Soroban escrow application for goods and freelancers, described as secure and cost-efficient escrow for fraud-resistant payments. Public material checked for this review does not provide enough current product detail to claim more.

Sources:

- https://communityfund.stellar.org/submissions/rec5SQUCL0doQ1r5M
- https://stellar.org/ecosystem?page=10&partner=formal-verso

### Push differentiator

Push's defensible distinction is the complete freelance work record around escrow. It connects discovery and applications to preserved terms, private communication, delivery evidence, revision history and human-reviewed dispute context. The contract is part of that workflow rather than a standalone escrow API.

Push also separates application staff approval from on-chain wallet authority. Routine payments do not require staff review. Dispute reviewers can only sign permitted settlements to the original participant wallets, and staff who are parties to the agreement cannot decide it. These are current design claims that must continue to be backed by code and tests.

This differentiator is a product hypothesis until real user research demonstrates that clients and workers value the combined workflow. Do not present it as validated market advantage without evidence.

## Proof-of-work standard

Every proposed deliverable must name its artefact before submission.

| Weight | Acceptable proof | Example for Push |
| --- | --- | --- |
| Strongest | Deployed contract or transaction that a reviewer can inspect | Contract ID, network, transaction hash and explorer link with the expected state change |
| Strong | Reproducible automated verification | Exact command, pinned commit, passing output and test covering the promised behaviour |
| Strong | Running technical deployment | Public URL, deployed commit, health evidence and a reviewer path using disposable accounts |
| Medium | Code and reviewed change | Public pull request or commit with issue, diff, tests and independent review notes |
| Medium | Recorded end-to-end evidence | Short demo that shows the actors, wallets, network, action and confirmed result |
| Supporting | Technical documentation | Architecture, threat model, operating procedure or acceptance matrix tied to code and evidence |
| Weak alone | Statement of intention | Roadmap prose without code, transaction, test or deployed result |

Do not use screenshots alone when a transaction, test or public source can prove the claim. Do not call mocked network tests live Stellar evidence.

## Roadmap rules

The next application roadmap should contain only work that can be completed and demonstrated during its stated period. Eligible categories include contract and backend implementation, frontend flows required to operate that implementation, tests, deployment, monitoring, recovery procedures and technical documentation.

Exclude marketing, promotional media, generic pilot recruitment, user acquisition, onramp and offramp development, and completed work. User research can be reported as product evidence outside a technical build budget if the programme permits it, but it should not displace the promised technical output.

Each roadmap item needs an owner, hours, completion condition and proof link. A proposed 100-hour budget at USD 50 per hour would total USD 5,000, but the founder must approve both figures. The final rate must be truthful and consistent across the application.

## Immediate repository work

1. Commit and publish the MIT licence and README licence notice, then verify GitHub detects the licence correctly.
2. Finish independent review of branch `codex/security-reliability-repairs`; correct the preparation expiry race and execute PostgreSQL concurrency tests before integration.
3. Replace the retired Instaward application draft with a new chapter-specific statement of work based on unfinished work at the next application date.
4. Add a concise architecture diagram and link each financial state transition to its contract and application implementation.
5. Create an application evidence index with commit, test, deployment, contract and transaction links.
6. Run a final application quality check for duplicate deliverables, broken links, unsupported claims, correct chapter and exact budget arithmetic.

## Licence decision note

The MIT licence is OSI-approved and permits use, modification, distribution, sublicensing and sale while requiring preservation of the copyright and licence notice. It includes a broad warranty disclaimer. It does not require modified versions to remain open source and does not contain Apache 2.0's explicit patent grant. The founder should choose it only after confirming ownership of the code and compatibility with incorporated third-party material.

Official text and description: https://opensource.org/license/mit
