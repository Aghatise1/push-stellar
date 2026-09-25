# Push motion improvement plans

The audit covers the landing illustration and authenticated product motion. The folder is not currently a Git repository, so the plans cannot include a commit stamp.

| Plan | Title | Severity | Status |
| --- | --- | --- | --- |
| 001 | Rebuild the landing orbit | HIGH | DONE |
| 002 | Tighten authenticated page entrances | MEDIUM | DONE |
| 003 | Keep the wallet USDC face readable | HIGH | DONE |
| 004 | Preserve accessible interaction feedback | MEDIUM | DONE |

## Recommended order

1. **004** establishes safe reduced-motion and pointer behaviour.
2. **003** fixes the reported blank USDC state with minimal risk.
3. **002** makes repeated authenticated navigation feel faster.
4. **001** rebuilds the larger landing-page explanatory animation after the shared behaviour is correct.

Plans 001 and 004 both touch `static/workspace.css`; execute 004 first, then implement 001 against the updated reduced-motion rules. Plans 002 and 003 both touch `static/app-motion.js`; implement 003 first and then 002, keeping each change separately reviewable.
