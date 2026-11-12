# Push application evidence index

Updated 12 November 2026. This index separates public proof, reproducible engineering evidence and founder supplied evidence. It must not be used to describe testnet activity as revenue, customer volume or mainnet settlement.

## Product and source

| Evidence | Link | What it proves | Limitation |
| --- | --- | --- | --- |
| Public pilot | https://pushearn.xyz | A reviewer can open the deployed application | Invitation or account approval may still limit the full workflow; provide a reliable reviewer path before submission |
| Public repository | https://github.com/Aghatise1/push-stellar | Source, tests, licence and technical history are public | Public code is not an independent security audit |
| MIT licence | https://github.com/Aghatise1/push-stellar/blob/main/LICENSE | Repository has an explicit open source licence | Founder remains responsible for confirming ownership and third party compatibility |
| Architecture and state flows | `docs/architecture-and-financial-flows.md` | Application boundaries, signers and financial transitions | Documentation must remain aligned with code |
| Demo video | https://drive.google.com/file/d/1kuU1SbJthnghDpW5ZiHo9W5kjBGhoepH/view | Recorded product walkthrough; anonymous check displayed the intended title on 12 November 2026 | A recording is not live chain proof and may predate the latest release |
| White paper | https://docs.google.com/document/d/1rtl4VK15nmiBkLZCah9iXeS6-VoHz_eJUXVdigwQ1Zc | Product, architecture and roadmap context; anonymous check displayed the intended title on 12 November 2026 | Recheck sharing immediately before submission |

## Release and review evidence

| Evidence | Link or value | Result |
| --- | --- | --- |
| Reliability and licence pull request | https://github.com/Aghatise1/push-stellar/pull/13 | Reviewed and merged |
| Render client identity pull request | https://github.com/Aghatise1/push-stellar/pull/14 | Reviewed and merged |
| Deployed commit | https://github.com/Aghatise1/push-stellar/commit/a60af23e1bcfe2b6b3ce5e76b447301cd433881b | Render live release recorded on 12 November 2026 |
| Live health evidence | https://pushearn.xyz/healthz/ | HTTP 200; release `a60af23e1bcf`; Stellar testnet; escrow enabled |
| Django suite | `python manage.py test --noinput` | 308 passed; 4 PostgreSQL environment tests skipped in the verified local run |
| Wallet JavaScript suite | `node --test tests/wallet-state.test.cjs` | 10 passed in the verified local run |
| GitHub Actions | Repository Actions run for pull request 14 | Push checks passed before merge |

## Stellar contract and transaction evidence

### Current recorded pilot deployment

| Evidence | Explorer link |
| --- | --- |
| Contract `CAO6VET6JK73QW4IJOIFCECYACWIZMC7GZK4I3G43ECSFQMCHGEKT3G5` | https://stellar.expert/explorer/testnet/contract/CAO6VET6JK73QW4IJOIFCECYACWIZMC7GZK4I3G43ECSFQMCHGEKT3G5 |
| Contract deployment | https://stellar.expert/explorer/testnet/tx/4a26779430772a625300110703ec2136024fb7532f550e62786bd2b47276734b |
| Disposable fee QA funding | https://stellar.expert/explorer/testnet/tx/0462de70def9b39f641b982c456d81a0f4007f961b0c6fce92e0bcb2c0b53722 |

The fee QA record shows a proposed fee of 2,630,897 stroops, a charged fee of 2,284,803 stroops and a refund of 346,094 stroops for its recorded one XLM test. This is engineering evidence, not customer usage.

On 12 November 2026, the deployment and fee QA transaction hashes in this section returned successful records from Stellar testnet Horizon.

### Recorded dual asset lifecycle evidence

| Asset and action | Explorer link |
| --- | --- |
| XLM fund | https://stellar.expert/explorer/testnet/tx/2a94125ebfb6d713a13fcc56367dda874772a1d5d15c0c2070ffa015678625bc |
| XLM submit | https://stellar.expert/explorer/testnet/tx/d03174b157cff48917fff4dab9a3d5536a4939ce010379e210cf7a010a9e34fa |
| XLM release | https://stellar.expert/explorer/testnet/tx/8ba029a0dac5e82e59c371f1259c5004ffb924f69a9ebe9a9bbd4cf285ebd170 |
| USDC fund | https://stellar.expert/explorer/testnet/tx/a6409f4584e80138d7c77b832e4b3b2708ccd633ce5dfce9f8ef81bc2cca11f2 |
| USDC submit | https://stellar.expert/explorer/testnet/tx/1dce3307c2aacf1ca0d6bfb591eceec2721e7e3cefc256f064fbfd1efa9e7bda |
| USDC release | https://stellar.expert/explorer/testnet/tx/4ad6ffd1bf5f0013f68baf232359069bd3d3adb2b1c34311465965304f7eaa26 |

These hashes are recorded engineering QA against the earlier owner controlled deployment in `contracts/deployments/testnet-owner-escrow.json`. They demonstrate testnet lifecycle calls but do not replace fresh end to end evidence against the current contract.

On 12 November 2026, all six lifecycle transaction hashes in this table returned successful records from Stellar testnet Horizon.

### Human dispute evidence

Disposable staff QA includes an authorised USDC dispute and split in `contracts/deployments/testnet-staff-escrow-qa.json`. It uses a disposable QA owner and must not be presented as the current owner wallet completing a live pilot dispute.

**Founder evidence still required:** preserve the successful escrow transaction hashes from the recent manual test, identify the contract used, record the asset and actors, and add explorer links. If the successful test used the current contract, this becomes the preferred reviewer evidence. Never invent or infer these hashes from a screenshot.

## Chapter and eligibility evidence

Tellus Cooperative emailed the founder on 10 November 2026 that the rejected November form was operated by Stellar Chile and recommended applying through the founder's own chapter. Stellar's official September and October 2026 Ambassador Program update identifies Stellar Nigeria, its Builders Circle and October Instaward recipients, but no public open Nigeria application round was located on 12 November 2026.

**Submission gate:** obtain the application link directly from Stellar Nigeria or its Builders Circle and verify that the form names Stellar Nigeria before entering or submitting the application. Do not reuse the Stellar Chile form.

## Submission proof checklist

1. Save the final source copy of every answer.
2. Capture the review page before submission.
3. Verify the chapter, requested amount, wallet, repository, website and supporting links.
4. Submit only after the founder confirms all declarations are accurate.
5. Save the confirmation page, confirmation email, submission timestamp and any application identifier.
6. Store the proof privately when it contains email addresses, wallet details or application identifiers.
