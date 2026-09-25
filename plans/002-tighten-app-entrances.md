# 002 — Tighten authenticated page entrances

- **Status**: DONE
- **Commit**: unavailable — this folder is not currently a Git repository
- **Severity**: MEDIUM
- **Category**: Easing, duration and frequency
- **Estimated scope**: 1 file, small change

## Problem

Authenticated pages animate primary content for 720–780ms every time a user navigates. These entrances occur repeatedly during ordinary work and make the interface feel slower than the underlying page load.

```javascript
// static/app-motion.js:21-40 — current
gsap.from('.app-reveal', {
  opacity: 0,
  y: 22,
  duration: 0.72,
  stagger: 0.065,
  ease: 'power3.out',
  clearProps: 'transform,opacity'
});

gsap.from(section, {
  scrollTrigger: { trigger: section, start: 'top 88%', once: true },
  opacity: 0,
  y: 28,
  duration: 0.78,
  ease: 'power3.out',
  clearProps: 'transform,opacity'
});
```

## Target

- `.app-reveal`: `opacity: 0`, `y: 12`, `duration: 0.22`, `stagger: 0.04`, `ease: 'power3.out'`.
- `.scroll-reveal`: `opacity: 0`, `y: 16`, `duration: 0.26`, `ease: 'power3.out'`.
- Preserve `clearProps: 'transform,opacity'`.
- Do not animate keyboard-initiated actions or message sending.

The purpose is **preventing a jarring change**. This is frequent product navigation, so the motion must finish within the 150–300ms UI budget.

## Repo conventions to follow

- GSAP is already vendored locally and initialised in `static/app-motion.js`; add no dependency.
- `power3.out` is the existing entrance curve and gives immediate movement comparable to the project's strong ease-out token.

## Steps

1. In `static/app-motion.js`, change the initial page reveal values to the exact target above.
2. Change the scroll reveal values to the exact target above.
3. Leave the early `prefers-reduced-motion` return intact.
4. Do not add reveals to messaging, wallet connection, or other high-frequency state changes.

## Boundaries

- Do NOT alter decorative wallet loops in this plan.
- Do NOT add new selectors or markup.
- Do NOT animate width, height, margins, padding, top, or left.

## Verification

- **Mechanical**: load every authenticated primary route and confirm there are no JavaScript errors.
- **Feel check**: navigate rapidly among Overview, Find work, Messages, Wallet, Payments and Profile. Content should feel immediately available, with motion noticeable only when deliberately watched.
- Use the browser animation inspector at 25% speed and confirm the stagger progresses in document order without blocking interaction.
- **Done when**: repeated navigation feels crisp and no entrance lasts longer than 260ms.

