# Original Push migration record

Source reviewed: `C:\Users\USER\Desktop\push-protocol-landing`

The working Django application is the canonical version; the original folder remains an untouched archive.

| Original material | Decision | Where it now lives |
| --- | --- | --- |
| “Built on trust, not gatekeepers” | Retained | Product page |
| Fragmented discovery, missing trust, scattered credentials, gatekeeping | Retained and clarified | Product page: problem section |
| Community, growth, design, operations, legal/finance and engineering | Retained | Product page and brief categories |
| Six-step lifecycle | Revised into enforceable state rules | How it works, `PRODUCT-RULES.md`, `SYSTEM-DESIGN.md` |
| Sample job preview | Upgraded from static cards to a working board | `/jobs/` |
| Employer/worker split | Revised to one account that can perform either role | Accounts, workspace and rules |
| Wallet-first identity | Retired | Email account plus optional public profile and payment destination |
| Solana-only positioning | Retired | Provider-neutral routes; Stellar testnet is the current verified route |
| USDC/USDT escrow claim | Retired pending custody, legal and security work | Testnet/simulated flows are labelled |
| On-chain badges | Revised | Future evidence-based reputation without a token requirement |
| Fixed 12.5% fee | Preserved as a candidate, not a promise | Product FAQ and system design |
| Comparison, roadmap and FAQ | Retained and updated to current facts | Product page |
| Founder name, Aghatise | Retained without inventing biography | Product FAQ |
| Investor material | Consolidated into the product boundary and launch gates | Product page and system design |
| Waitlist | Replaced by registration for the private working preview | `/register/` |
| Web3Forms and localStorage collection | Not migrated | Server-side accounts replace the standalone form |
| Black-hole video, liquid glass and cinematic motion | Retired by explicit direction | Architectural dossier design system |
| Metallic abstract imagery | Archived, not currently used | Original `assets` folder |

## Sensitive configuration finding

The reviewed working files do not contain a Supabase client integration. They contained a Web3Forms access key directly in `app.js` and duplicated build/archive files. The key was removed from six files on 24 September 2026, but one Git commit still contains its historical value. The key must therefore be revoked or rotated in Web3Forms; deleting source text does not invalidate it. No credential from the original has been copied into the canonical application.

## Control rule

New product decisions must be written into `PRODUCT-RULES.md` and, when they affect architecture or states, `SYSTEM-DESIGN.md`. Marketing copy may explain those decisions but must not create rules by itself.
