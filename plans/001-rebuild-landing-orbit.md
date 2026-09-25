# 001 — Rebuild the landing orbit

- **Status**: DONE
- **Commit**: unavailable — this folder is not currently a Git repository
- **Severity**: HIGH
- **Category**: Purpose, physicality and accessibility
- **Estimated scope**: 3 files, small-to-medium change

## Problem

The hero illustration is meant to explain the relationship between completed work and settlement, but the two discs currently float independently while two large rings rotate behind them. This reads as decoration rather than a process, and the text-only USDC disc does not use the supplied USDC artwork.

```html
<!-- templates/home.html:1 — current excerpt -->
<div class="orbit-art" aria-hidden="true"><span class="orbit orbit-a"></span><span class="orbit orbit-b"></span><span class="coin coin-usdc">USDC</span><span class="coin coin-work">WORK</span><i></i></div>
```

```css
/* static/workspace.css:19 — current excerpt */
.orbit{...animation:orbit-turn 18s linear infinite}
.coin-usdc{...animation:coin-float 4s var(--ease-in-out) infinite alternate}
.coin-work{...animation:coin-float 4s var(--ease-in-out) 600ms infinite alternate}
```

## Target

Create one restrained orbital system with two circular objects moving on the same elliptical path, half a cycle apart:

- A disc using `static/images/usdc.png`.
- A circular Push work-record disc using the existing Push mark or the word `WORK` with strong contrast.
- The discs travel with a `14s linear infinite` CSS animation using `transform` only.
- Each disc counter-rotates so its face remains upright.
- Keep the existing vermilion centre marker static.
- Increase the space between the headline, orbit and supporting copy at desktop and mobile widths.
- Under `prefers-reduced-motion: reduce`, place both discs at fixed opposing points and remove positional motion.

The animation purpose is **explanation**: work and USDC are separate records connected by a visible settlement path. It is a rare marketing interaction, so continuous restrained motion is acceptable.

## Repo conventions to follow

- Motion tokens already live in `static/workspace.css` under `:root`, including `--ease-in-out`.
- The supplied USDC image already appears in `templates/wallet.html` as `{% static 'images/usdc.png' %}`.
- The landing page uses paper neutrals and forest/vermilion signals; do not introduce a second palette.

## Steps

1. In `templates/home.html`, load Django static files and replace the text-only USDC disc with an `<img>` using `images/usdc.png` and an empty alt because the whole illustration is decorative.
2. Wrap each disc in an orbiting carrier so the carrier rotates and the visible face counter-rotates. Keep the two carriers 180 degrees out of phase.
3. In `static/workspace.css`, replace the independent `coin-float` animations with a transform-only orbit lasting exactly `14s` and using `linear` easing.
4. Keep the visible coin faces at a stable readable orientation. Do not flip them in 3D or allow an edge-on blank frame.
5. Adjust `.intro`, `.intro h1`, `.orbit-art`, and `.intro-copy` spacing so the illustration has a distinct band and cannot collide with text from 320px through wide desktop sizes.
6. Add a reduced-motion rule that removes the orbit transforms and displays the discs at static opposing positions while preserving colour and hierarchy.

## Boundaries

- Do NOT add a video background to the hero.
- Do NOT add a token, price, yield, trading, or investment claim.
- Do NOT change the landing-page colour identity.
- Do NOT animate layout properties such as `left`, `top`, width, margin, or padding.
- Do NOT make the animation interactive or cursor-following.

## Verification

- **Mechanical**: run `python manage.py check` and the Django test suite; both must complete successfully.
- **Feel check**: preview at 1440px, 1024px, 760px, 390px, and 320px. Confirm that the two discs never collide with the heading or supporting copy, remain legible throughout the orbit, and do not visually stutter at the loop boundary.
- In browser developer tools, enable reduced motion and confirm both discs become static without disappearing.
- **Done when**: the hero explains the work-to-payment relationship at a glance and no text overlaps the illustration.

