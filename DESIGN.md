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
  white: "#fff"
  forest-hover: "#0e2d24"
  rail-active: "#242a26"
  rail-border: "#353c37"
  rail-text: "#c7c8c0"
  rail-focus: "#ff9a80"
typography:
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

- **Display:** The home headline has a narrow measure (10ch), balanced wrapping and the display scale above. On mobile it uses clamp(3.4rem, 17vw, 5rem).
- **Headline:** General page headings use a maximum measure (15ch), tight line-height and a bottom margin (1.5rem).
- **Title:** Section headings use the title scale. Smaller headings use 1.04rem with line-height 1.35.
- **Body:** Paragraphs are limited to 70ch with pretty wrapping. Lead text uses clamp(1.05rem, 1.5vw, 1.3rem), line-height 1.5 and a 48ch measure; the introductory lead is 1.2rem.
- **Label:** Field labels use the label role. Compact uppercase rail captions and top-bar metadata add tracking (.08em and .07em respectively). Process labels are .68rem.
- **Numbers:** Budgets and stage numbers use tabular numerals. Detail budgets are 2.8rem, reducing to 2.25rem on mobile.
- **Code:** Inline technical references use ui-monospace, SFMono-Regular, Consolas, monospace at .82em, only where the record needs them.

## Layout

Desktop navigation is a fixed rail (17.25rem) with padding (2.15rem 1.75rem 1.5rem). The content shell offsets by that width. The top bar is 4.5rem tall. Main content is centred at a maximum width (90rem), with responsive vertical and horizontal padding and 7rem bottom clearance.

The home introduction pairs a larger headline column with a smaller copy/action column (1.4fr to .6fr; copy minimum 16rem). Process stages form four ruled columns. Principles use three columns, while product rules use two. These are observed surface compositions, not requirements for every screen.

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

Keyboard focus uses a .1875rem outline with a .25rem offset; the rail substitutes its lighter focus colour. A skip link appears on keyboard focus. Buttons and navigation use short state transitions; records move only on interaction. No looping animation is present. Reduced-motion preference removes transitions and smooth scrolling.

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
