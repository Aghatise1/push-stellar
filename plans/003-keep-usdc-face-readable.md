# 003 — Keep the wallet USDC face readable

- **Status**: DONE
- **Commit**: unavailable — this folder is not currently a Git repository
- **Severity**: HIGH
- **Category**: Purpose and physicality
- **Estimated scope**: 1 file, small change

## Problem

The wallet's supplied USDC image rotates a full 360 degrees around its Y axis. A flat image has no designed reverse face, so it becomes edge-on and appears blank twice in every cycle. This matches the reported blank visual state.

```javascript
// static/app-motion.js:58 — current
gsap.to('.token-disc', { rotationY: 360, duration: 4.2, repeat: -1, ease: 'none', transformPerspective: 800 });
```

## Target

Replace the 3D coin flip with a slow floating motion that keeps the image readable:

```javascript
gsap.to('.token-disc', {
  y: -8,
  rotation: 3,
  duration: 2.8,
  repeat: -1,
  yoyo: true,
  ease: 'sine.inOut'
});
```

The purpose is **delight** on an occasional wallet illustration. The motion uses transform only, remains calm, and never hides the brand asset.

## Repo conventions to follow

- The two wallet cards already use slow `sine.inOut` yoyo motion in `static/app-motion.js:61-62`; the token should belong to the same physical family.
- Reduced motion is already checked before GSAP timelines are created.

## Steps

1. Replace only the `.token-disc` GSAP call with the exact target animation.
2. Remove `transformPerspective` because the replacement is a 2D transform.
3. Confirm the image remains face-on at every frame.

## Boundaries

- Do NOT replace or recolour `static/images/usdc.png`.
- Do NOT speed up the animation or add bounce.
- Do NOT modify card animation values in this plan.

## Verification

- **Mechanical**: load the wallet page with normal and reduced-motion preferences; confirm there are no JavaScript errors.
- **Feel check**: watch three full cycles and confirm the USDC emblem never narrows, mirrors, disappears, or competes with controls.
- **Done when**: the emblem is continuously recognisable and the motion feels part of the card composition.

