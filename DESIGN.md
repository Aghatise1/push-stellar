---
name: Push
description: An architectural tender dossier translated into a shared work record.
colors:
  paper: "#f3f0e8"
  paper-deep: "#e8e3d8"
  sheet: "#fbfaf6"
  ink: "#171b18"
  muted: "#656b65"
  line: "#c8c5ba"
  line-strong: "#8e928a"
  signal: "#d95536"
  signal-dark: "#a83520"
  forest: "#173d31"
  forest-soft: "#dfe7df"
  warning: "#f0e7d1"
  danger: "#f2dfd8"
  focus: "#176b54"
  cinema-ink: "#101110"
  cinema-paper: "#f2eee5"
  cinema-accent: "#ff8066"
  cinema-muted: "#c3c3b9"
  cinema-line: "#454640"
  white: "#fff"
  forest-hover: "#0e2d24"
  rail-active: "#242a26"
  rail-border: "#353c37"
  rail-text: "#c7c8c0"
  rail-focus: "#ff9a80"
typography:
  cinema-display:
    fontFamily: "'Instrument Sans', sans-serif"
    fontSize: "clamp(3.4rem, 7vw, 6.5rem)"
    fontWeight: 600
    lineHeight: .99
    letterSpacing: "-.035em"
  cinema-headline:
    fontFamily: "'Instrument Sans', sans-serif"
    fontSize: "clamp(2.6rem, 5.7vw, 5.5rem)"
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: "-.035em"
  display:
    fontFamily: "'Instrument Sans', sans-serif"
    fontSize: "clamp(4rem, 8vw, 6rem)"
    fontWeight: 600
    lineHeight: .96
    letterSpacing: "-.035em"
  headline:
    fontFamily: "'Instrument Sans', sans-serif"
    fontSize: "clamp(2.75rem, 5.2vw, 5.6rem)"
    fontWeight: 600
    lineHeight: .96
    letterSpacing: "-.035em"
  title:
    fontFamily: "'Instrument Sans', sans-serif"
    fontSize: "clamp(1.45rem, 2vw, 2rem)"
    fontWeight: 600
    lineHeight: 1.08
    letterSpacing: "-.025em"
  body:
    fontFamily: "'Instrument Sans', sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "'Instrument Sans', sans-serif"
    fontSize: ".78rem"
    fontWeight: 600
    lineHeight: 1.55
rounded:
  field: ".15rem"
  button: ".2rem"
  avatar: ".25rem"
spacing:
  compact: ".5rem"
  standard: "1rem"
  panel: "1.5rem"
  section: "4rem"
components:
  button-primary:
    backgroundColor: "{colors.forest}"
    textColor: "{colors.white}"
    rounded: "{rounded.button}"
    padding: ".76rem 1.1rem"
  button-primary-hover:
    backgroundColor: "{colors.forest-hover}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.button}"
    padding: ".76rem 1.1rem"
  button-secondary-hover:
    backgroundColor: "{colors.sheet}"
  input:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: ".78rem .85rem"
  tag:
    backgroundColor: "{colors.paper-deep}"
    rounded: "{rounded.field}"
    padding: ".35rem .5rem"
  nav-active:
    backgroundColor: "{colors.rail-active}"
    textColor: "{colors.white}"
    padding: ".82rem .9rem"
---

# Design System: Push

## Overview

**Creative North Star: "The architectural tender dossier"**

This is the application system. The public home page has a separately approved charcoal, ivory and coral cinematic world, documented below; its tokens are prefixed `cinema-`. The home extension does not change workrooms, reporting, forms, staff screens or public reading pages.

An architectural tender dossier translated into software: precise briefs, numbered stages, strong typographic hierarchy and paper-like neutral surfaces. A dark ink rail anchors the workspace; a controlled vermilion signal marks the identity and key structural moments. Forest-green actions remain deliberately functional.

The result is mature, legible and procedural. Fine rules organise evidence and stages; flat surfaces keep the document itself prominent. Glass and black-hole visual effects are excluded. Push is still a working name. This record describes the shipped local build, not a production launch approval.

**Key Characteristics:**

- Paper neutrals, dark ink navigation and controlled vermilion markers.
- Large Instrument Sans headlines paired with compact document metadata.
- Numbered process stages and ruled work records.
- Briefs, current status and evidence remain easy to inspect.

Observed sources: static/workspace.css; templates/base.html, home.html, workspace.html and how_it_works.html; PRODUCT.md and PRODUCT-RULES.md. This authorised refresh replaces the former cream-and-green system description. Frontmatter owns primitives; .impeccable/design.json contains extensions and component previews.

## Colors

### Primary

Vermilion is the signature signal: the wordmark square, introductory rule, authentication rule, timeline points and darker numbered-stage labels. Selection and the input caret also use it. It is not the primary button fill.

### Secondary

Forest supports functional buttons, links and secondary disclosure labels. Pale forest carries successful outcomes. Focus uses a brighter forest; the dark rail uses a peach focus outline for contrast.

### Neutral

Paper is the main canvas; deeper paper groups filters and tags; sheet is the light field and hover surface. Ink is both body text and the solid navigation rail. Quiet grey-green supports metadata. Two line tones provide ordinary dividers and stronger structural boundaries.

### Status

Sand and muted terracotta distinguish notice and error surfaces. Retain explicit status text, including success and error explanations.

**The Signal Rule.** Keep vermilion as a controlled structural signal; preserve forest-green task actions.

## Typography

Locally served Instrument Sans provides regular and semibold faces with font-display swap. The sans-serif fallback remains available. There is no display/body family split.

- **Display:** The original dossier-style introduction has a narrow measure (10ch), balanced wrapping and the display scale above. On mobile it uses clamp(3.4rem, 17vw, 5rem).
- **Headline:** General page headings use a maximum measure (15ch), tight line-height and a bottom margin (1.5rem).
- **Title:** Section headings use the title scale. Smaller headings use 1.04rem with line-height 1.35.
- **Body:** Paragraphs are limited to 70ch with pretty wrapping. Lead text uses clamp(1.05rem, 1.5vw, 1.3rem), line-height 1.5 and a 48ch measure; the introductory lead is 1.2rem.
- **Label:** Field labels use the label role. Compact uppercase rail captions and top-bar metadata add tracking (.08em and .07em respectively). Process labels are .68rem.
- **Numbers:** Budgets and stage numbers use tabular numerals. Detail budgets are 2.8rem, reducing to 2.25rem on mobile.
- **Code:** Inline technical references use ui-monospace, SFMono-Regular, Consolas, monospace at .82em, only where the record needs them.

## Layout

Desktop navigation is a fixed rail (17.25rem) with padding (2.15rem 1.75rem 1.5rem). The content shell offsets by that width. The top bar is 4.5rem tall. Main content is centred at a maximum width (90rem), with responsive vertical and horizontal padding and 7rem bottom clearance.

The dossier-style introduction pairs a larger headline column with a smaller copy/action column (1.4fr to .6fr; copy minimum 16rem). Process stages form four ruled columns. Principles use three columns, while product rules use two. These are observed surface compositions, not requirements for every screen.

Job rows align category, flexible title, budget and action in four columns (7rem, flexible, 10rem, 5rem). Forms and detail screens use a two-to-one grid with a secondary minimum (14rem) and responsive gap. Form content caps at 44rem; authentication at 30rem. Workspace shortcuts use three equal ruled segments.

At 1050px and below, the rail becomes 13rem, content gutters become 2rem, the introduction stacks and process stages become two columns. Job rows lose the separate action column; title links remain.

At 720px and below, navigation becomes a static dark header with horizontally scrolling links. Main padding becomes 2.5rem 1.25rem 4.5rem. Process, principles, workspace links, rules, forms and detail layouts stack. Job categories span both remaining columns; budgets align right. Work rows and lifecycle stages stack. Footer and authentication links stack. Long record text wraps safely.

## Elevation & Depth

Paper-like tonal layers and fine rules do the structural work. There are no resting surface shadows or backdrop blur. A faint vertical drafting grid is drawn behind the page at 4rem intervals, becoming 2rem on mobile. This subtle linear-gradient grid is intentional; it is not a decorative colour wash.

Fields gain a small focus halo (0 0 0 .2rem rgba(23,107,84,.1)). That is interaction feedback, not card elevation.

## Shapes

The system is predominantly rectilinear. Fields, notices and tags use the field radius; buttons use the button radius. Avatars are small rounded squares, not circles. Major sections and record grids have square corners and one-pixel rules. The brand mark is a vermilion square; the introductory marker is a short thick rule.

## Components

### Buttons

Primary buttons are solid forest with white semibold text (.86rem), compact padding and a minimum height (2.9rem). Hover deepens the forest fill; active presses scale to .97. Secondary buttons use an outlined transparent surface with ink text, gaining a sheet fill and ink border on hover. Small buttons use .75rem text and a 2.35rem minimum height. Disabled buttons use opacity .5 and a not-allowed cursor.

### Inputs / Fields

Sheet-filled fields use a strong-line border, minimum height (2.9rem) and the input token padding. Hover darkens the border. Focus changes the border to the focus tone and adds the halo. Textareas start at 7rem and resize vertically. Labels have a .42rem bottom gap; groups have 1.5rem bottom spacing. Help and textual error lists follow the field.

### Navigation

The dark rail uses muted light labels. Hover and current pages use a lighter ink surface; the current page also has a border, a vermilion side marker and aria-current. Active links scale to .98. On mobile, links scroll horizontally and side markers disappear.

### Records and process stages

Open job rows and assignment rows prioritise title, status and evidence. Job-row hover adds sheet fill and a horizontal shift (.35rem desktop, .2rem mobile). Four numbered process stages explain the workflow. The rules grid and lifecycle strip share fine borders and compact labels. Avoid turning these document structures into floating cards.

### Tags and notices

Tags are non-interactive bordered labels on deeper paper. Notices have a compact tonal surface and border; success and error variants retain explanatory text. Completion uses pale forest with a strong forest top rule.

### Focus and motion

Keyboard focus uses a .1875rem outline with a .25rem offset; the rail substitutes its lighter focus colour. A skip link appears on keyboard focus. Buttons and navigation use short state transitions; records move only on interaction. No looping animation is present in these application components. Reduced-motion preference removes transitions and smooth scrolling. The public home has its own motion behaviour below.

## Do's and Don'ts

### Do:

- Do preserve the distinction between vermilion signals and forest-green actions.
- Do use numbered stages, fine rules and aligned metadata to organise work.
- Do retain labelled fields, visible focus and reduced-motion support.
- Do distinguish sample activity, payment simulations and Stellar testnet verification in visible copy.

### Don't:

- Don't add glass surfaces or black-hole visual effects.
- Don't replace open records with layers of decorative cards.
- Don't use colour alone to convey status.
- Don't imply mainnet settlement, custody, invented activity or production readiness.


## Operations reporting (28 September 2026)

The dedicated Insights page uses a compact reporting layout: four count cards, a wide daily
trend chart and a narrow actionable queue, period comparisons, then engagement
and settlement detail. The command centre retains its original action cards and an always-visible owner workspace selector. Reports belong only in Insights.
Keep the existing forest/paper identity; the supplied reference informs density
and hierarchy, not its purple palette. The shared shell uses warm paper #f3f0e8, sheet #fbfaf6 and forest accents. Settings stays in the profile area; member toolbar controls are grouped on the left. Report cards have clear borders;
the primary chart uses forest #172a22, light green #a9cfb6 and a dashed cream
comparison line. Labels and dates must accompany every count. No decorative
verification doughnut, fake revenue, fabricated activity or percentage without
a denominator. Exact daily figures remain available as an accessible table.

Use 7/30/90-day controls, 44px targets, responsive two-column count cards and
single-column phone charts. Motion is limited to a 180ms entrance and button
feedback; respect reduced motion. Reporting must work without JavaScript.

## Public home: photographic editorial world (9 October 2026)

This home-only world implements the approved charcoal, ivory and coral direction, layered photography and scroll-driven scenes. Application guidance above remains authoritative elsewhere. Product, rules and documentation pages continue to use public-reading.css; workrooms, reporting, forms and staff screens retain the dossier system.

### Overview

The sequence is a photographic hero with an orbiting motif, layered purpose photographs, the retained Push film, six operating rules alongside the actual interface, a three-scene gallery, a light payment explanation, FAQ and a coral closing invitation with oversized moving lettering. There is no 30-day roadmap. Illustration supplies atmosphere; the sample interface and explicit product copy supply evidence.

### Colors

The effective home tokens are charcoal ink #101110, warm ivory #f2eee5, coral accent #ff8066, muted text #c3c3b9 and divider #454640. Purpose uses #141513, film #1d1e1a, journey #0f1111 and talent #191a17. Payment uses warm paper #e9e3d6. The close uses coral #dc593f with dark text and a dark primary action. The shared footer retains its subdued existing light-text and divider treatment.

**The Home Boundary Rule.** Apply this direction only to the public home and its scoped shell. Keep the application's forest task actions, reporting palette and paper work records unchanged.

### Typography

Locally served Instrument Sans remains shared. The hero uses clamp(3.4rem, 7vw, 6.5rem), line-height .99 and a 15ch measure. General headings use the cinema-headline role; purpose increases to clamp(3.7rem, 8vw, 7.5rem). The hero wordmark uses clamp(6rem, 16vw, 15rem). Gallery titles use clamp(2.8rem, 5vw, 5rem). Decorative closing lettering uses clamp(5rem, 15vw, 17rem), reducing to 22vw below 851px, and is hidden from assistive technology. Phone headings and safe long-text wrapping remain explicitly sized in the responsive rules.

### Layout and photographic depth

Full-width sections use generous responsive gutters and vertical spacing. The purpose section layers two rotated rectangular photographs behind a large heading and an opaque dark copy panel. Photo shadows and text shadows support this composition; application panels do not acquire these effects. The hero photograph sits behind a dark overlay and uses cover cropping. All decorative overflow remains clipped within the composition.

The journey pairs a sticky sample workroom screenshot with six numbered rules: agree the work, fund the agreement, deliver with evidence, approve settlement, keep your keys and check the record. Alternating rule offsets and small circular photo fragments add rhythm. The screenshot is explicitly labelled as demonstration accounts and sample data. Below 851px, the journey stacks and the screenshot becomes static; below 481px, rule offsets disappear.

The three gallery scenes cover design, collaboration and craft. Above 850px, with motion enabled, a 280svh section holds a sticky viewport beneath the header while ordinary page scrolling translates the three panels horizontally. Phones, paused motion, reduced motion and the no-JavaScript fallback use a vertical sequence of all three scenes. Do not hide content behind the motion enhancement.

The payment explanation retains three ruled steps, a conceptual escrow illustration and explicit testnet limitations. These stack on phones. The coral close combines the invitation and contact links with large decorative lettering.

### Components and motion

Primary home actions use coral with dark text, a 48px minimum height and 2px corners; hover uses #ffa48e. Secondary links and FAQ summaries retain 44px targets. Visible focus outlines use the accent on dark surfaces and dark outlines on light or coral surfaces.

Motion is coordinated by static/landing-cinematic.js. Native scrolling drives hero fading and parallax, gentle offset movement in the purpose photos, desktop gallery translation and scene drift. The closing PUSH FORWARD ticker uses two identical groups for a continuous 32 second right to left loop while visible. Section headers and rule items receive a one-time 550ms reveal on entering view. The decorative hero orbit carries text nodes IDEA and WORK, with counter rotation keeping labels upright. It turns over 30 seconds while the hero is in view; page visibility pauses it. It remains a smaller motif on phones. Film and payment sections use a one time five strip shutter reveal of 650ms with 40ms stagger. Explicit focal points preserve the subjects when images crop for phones. The workroom image links to the operating rules and is labelled as a demonstration image, not live wallet controls.

A fixed Pause motion / Resume motion button controls these enhancements and reports its state with aria-pressed. Pausing resets scroll transforms, stops the orbit and restores the gallery's vertical layout. Reduced-motion preference disables the orbit animation, removes image and lettering transforms, uses the vertical gallery and hides the redundant motion button. Without JavaScript, content remains visible, the gallery stacks and the orbit stays paused. The former single hero entrance is no longer the current motion design.

The film preserves its original source and uses a silent H.264 looping derivative with its audio stream removed. It has no native player controls and starts automatically when visible, with inline playback, a poster and preload none. Reduced motion, the page pause control, hidden tabs and leaving view pause playback. Desktop uses full section width with a centred 16:9 crop; phones retain the complete 4:3 composition. Native details/summary FAQ controls work without JavaScript.

### Do's and Don'ts

- Do retain the layered photographs, six rules, three distinct gallery scenes and oversized closing lettering as one coherent home composition.
- Do preserve illustrative-image and sample-data labels; generated scenes are not customer endorsements or transaction proof.
- Do preserve visitor control of motion and film playback, and a readable vertical fallback.
- Do keep testnet, voluntary testing and no-real-money copy beside relevant invitations and payment explanations.
- Don't extend this palette or decorative motion into the working application without a separate decision.
- Don't imply deployment, live wallet acceptance or mainnet readiness from local visual completion.
