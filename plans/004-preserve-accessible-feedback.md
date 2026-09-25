# 004 — Preserve accessible interaction feedback

- **Status**: DONE
- **Commit**: unavailable — this folder is not currently a Git repository
- **Severity**: MEDIUM
- **Category**: Accessibility and input behaviour
- **Estimated scope**: 2 files, medium change

## Problem

The public reduced-motion rule removes every transition from every element, including useful colour, border and opacity feedback. Several hover translations also run without checking whether the device has a real hover pointer, which can cause sticky hover states on touch screens.

```css
/* static/workspace.css:21 — current */
@media(prefers-reduced-motion:reduce){*{transition:none!important;scroll-behavior:auto!important}.orbit,.coin{animation:none!important}}
```

```css
/* static/app.css:5, 8, 12, 13 — current pattern */
.app-mode .sidebar nav a:hover{...transform:translateX(.15rem)}
.wallet-actions a:hover{transform:translateY(-.15rem);...}
a.app-list-row:hover{...transform:translateX(.2rem)}
.wallet-command a:hover{...transform:translateY(-.15rem)}
```

## Target

- Under `prefers-reduced-motion: reduce`, stop continuous and positional movement, but retain colour, border-colour and opacity feedback at `160ms ease`.
- Place hover-only transforms inside `@media (hover: hover) and (pointer: fine)`.
- Keep `:active { transform: scale(.97) }` press feedback where it is already present; it is brief feedback rather than continuous motion.
- Preserve instant scrolling under reduced motion.

## Repo conventions to follow

- The project already names transition properties explicitly; do not introduce `transition: all`.
- Use existing duration values: 140–160ms for press, colour and border feedback.

## Steps

1. In `static/workspace.css`, replace the universal transition removal with focused rules that disable orbit/positional animations and smooth scrolling while allowing colour, border and opacity transitions.
2. In `static/app.css`, wrap transform-producing hover rules for the sidebar, wallet actions, work rows and wallet commands in `@media (hover: hover) and (pointer: fine)`.
3. Keep non-transform hover colour changes available on all devices where they do not produce sticky or misleading states.
4. Verify keyboard focus styling is unchanged.

## Boundaries

- Do NOT remove focus outlines.
- Do NOT disable all animation globally.
- Do NOT add hover motion to any new element.
- Do NOT change layout or colour tokens in this plan.

## Verification

- **Mechanical**: run `python manage.py check` and the Django test suite; both must pass.
- **Feel check**: emulate reduced motion and verify that controls still communicate hover/focus/pressed states without travelling across the screen. Emulate a touch device and confirm no translation remains stuck after a tap.
- **Done when**: reduced-motion users retain useful feedback, and touch devices receive no hover-driven movement.

