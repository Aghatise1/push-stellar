# Frontend verification

Local verification on 9 October 2026 for the charcoal, ivory and coral photographic public home.

## Current home checks

- Browser checks at widths of 320, 390 and 1440 pixels found no horizontal page overflow or missing landing images.
- The desktop gallery produced an actual horizontal translation of -2126px during scroll inspection. This confirms movement in the tested viewport; it is not a fixed implementation distance.
- Phone layouts showed all three gallery scenes in a vertical sequence. Pausing motion also restored the vertical gallery.
- With reduced motion enabled, the orbit had no animation, the gallery used a vertical layout and the motion button was hidden.
- No browser console errors were observed during these local checks.
- Django system checks passed.

These checks cover the home composition and its motion states. The workroom preview was replaced with a 1200 × 900 capture of a current testnet fixture awaiting agreement. It has no cookie banner or historical migration prompt and does not represent a funded payment. The separate visual reviewer inspected the replacement and marked the sole presentation fix resolved, with final disposition accepted.

## Final interaction checks

The final ticker advanced at 320, 390 and 1440 pixels and paused using the motion control. The text orbit uses IDEA and WORK. All homepage internal application links returned HTTP 200 in an isolated Django client check; the video fallback resolved to its local static asset. No real account submissions were made.

## Earlier supporting checks

The earlier cinematic pass checked native FAQ opening by click and keyboard. The preserved original film played to 2.605 seconds, reached readyState 4 and reported no media error. Its browser-compatible derivative played to 2.737825 seconds with paused false, readyState 4 and no media error. The current player retains that derivative and native controls. These are supporting playback samples, not new full-duration tests of this editorial pass.

Before the cinematic replacement, product, documentation and work-rules pages were checked at 320 pixels without horizontal overflow. The full automated suite passed 182 tests with one skipped before final presentation refinements of that earlier pass. Those historical results do not mean the complete suite was rerun against the current home.

## Limits

Verification used a local Django build and demonstration fixtures. It does not establish compatibility with every browser, device or network condition. The six-rule layout, three-scene gallery, orbit and closing lettering are presentation features, not evidence that wallet or settlement acceptance is complete. The no-JavaScript layout is supported by the implementation; the recorded motion-state checks should not be treated as a separate full no-JavaScript browser audit.

Deployment verification is pending for this release. No live wallet was connected or signed, and no on-chain payment flow was accepted as part of this frontend check. Freighter and escrow acceptance, independent security review and any production-readiness decision remain separate work. The product remains a voluntary Stellar testnet pilot with no real money. No 30-day roadmap is presented on this home.

## Silent loop follow up

The film now uses a video only H.264 derivative with no audio stream. Browser checks at 1280 and 390 pixels confirmed automatic muted playback, loop enabled, no native controls, no horizontal overflow and a full section width video. The page motion control paused playback. Desktop uses a centred 16:9 crop; mobile keeps the complete 4:3 frame. The original source remains preserved. The earlier native player observations above describe the previous release.

## Customer application verification

Local verification on 27 October 2026 covered the signed in customer application redesign on the working tree based on commit `401b8ed`.

The browser matrix covered Home, My work, Find work, a job detail, a workroom, Messages, Wallet, Payments, Account settings and Support at widths of 320, 390, 768, 1024 and 1440 pixels. All 50 route and viewport combinations loaded the customer application shell without an error page or horizontal overflow. The corrected Account settings page exposed all eight customer shortcuts. The mobile checks also confirmed a visible top bar and a five item bottom navigation at the 721 and 760 pixel boundaries.

Keyboard navigation produced a visible three pixel focus outline on the skip link. The final browser pass reported no console errors. Screenshots from the verified customer Home are saved as `docs/screenshots/customer-home-mobile-390.png` and `docs/screenshots/customer-home-desktop-1440.png`.

The complete Django `core` suite passed 283 tests with one skipped and no system check issues. The wallet JavaScript suite passed 10 tests. Syntax checks passed for both `static/app-motion.js` and `static/customer-motion.js`. Automated isolation checks confirmed that customer motion is not loaded on public or staff pages.

These checks used disposable local data and did not connect Freighter, sign a transaction, alter an escrow agreement or prove a live deployment. Reduced motion is covered by the stylesheet and script contract plus automated source checks, not by a separate browser emulation run. Real device testing and deployed environment acceptance remain separate work.
