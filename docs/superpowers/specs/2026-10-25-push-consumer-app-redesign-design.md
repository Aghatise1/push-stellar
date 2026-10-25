# Push consumer application redesign

## Intent

Redesign the signed in customer application so it feels simple, friendly and responsive while preserving the trust required for freelance agreements, wallet signing and escrow. The desired character takes inspiration from the clarity of Telegram, the playful confidence of Snapchat and the effortless navigation of Bolt without copying any of their layouts, marks or colour systems.

The current customer application is capable but visually serious. A dark permanent sidebar, large financial dashboard treatments, dense card grids and repeated uppercase metadata make ordinary work actions feel administrative. The redesign should make Push feel like an approachable consumer application that happens to contain rigorous payment controls.

## Selected scope

This phase changes the signed in customer experience only. It covers the customer application shell, overview, work lists, job discovery, job posting, applications, assignments, workrooms, conversations, notifications, wallet, payments, analytics, support, profile and account settings.

The public landing page and every staff operations surface stay visually unchanged in this phase. Customer and staff pages currently share `templates/base.html` and authenticated styles, so the implementation must introduce an explicit customer scope instead of allowing broad selectors to restyle staff pages accidentally.

## Goals

1. Make the application understandable within seconds on desktop and mobile.
2. Reduce visual weight and show one clear next action on workflow pages.
3. Make job discovery, active work and messaging feel social and human through useful avatars, names, short labels and friendly empty states.
4. Keep escrow states, wallet connection and required signatures unambiguous.
5. Make navigation and feedback feel quick through restrained motion and tactile responses.
6. Establish reusable tokens and components so pages become more consistent as the product grows.
7. Preserve accessibility, reduced motion support, keyboard navigation and current responsive behaviour.

## Non goals

1. No change to the landing page or its cinematic presentation.
2. No visual redesign of staff operations, moderation or staff wallet access.
3. No change to job, application, agreement, escrow, wallet or dispute behaviour.
4. No new social feed, reactions, stories, gamification or decorative emoji system.
5. No copying of Bolt, Snapchat or Telegram assets, layouts or trade dress.
6. No new frontend framework or component dependency.
7. No mainnet claims and no attempt to disguise testnet state.

## Anti goals

The redesign fails if it becomes childish, visually noisy, animation heavy, unclear about money, dependent on colour alone, inconsistent between pages or slower on ordinary devices. It also fails if broad CSS changes alter staff operations or the public landing page.

## Approaches considered

### Gentle refinement

Keep the existing page structures and soften colours, cards, typography and motion. This would be fast and low risk, but it would retain the current finance dashboard character and much of the density the redesign is intended to remove.

### Consumer application redesign

Simplify the information hierarchy, introduce a dedicated customer shell, reduce card density, create friendlier work and job patterns and use restrained playful motion. Preserve backend behaviour and staff presentation. This is the selected approach because it creates a meaningful product change while keeping payment and operational risk bounded.

### Complete playful overhaul

Rebuild most navigation and compositions around bold colour, illustration and extensive motion. This could be visually distinctive, but it increases accessibility, trust, testing and delivery risk. It does not fit the pilot stage.

## Design language

### Character

The interface should feel optimistic, direct and calm. It may be playful in transitions, empty states and small moments of acknowledgement. Wallet approvals, escrow funding, disputes and destructive actions remain sober and explicit.

### Design settings

Design variance is 6 out of 10. Motion intensity is 4 out of 10. Visual density is 3 out of 10. These settings produce a clean consumer application with recognisable character and restrained motion.

### Colour

Push green remains the primary brand colour. The customer application uses a pale neutral background, white or lightly tinted surfaces, deep green ink and one bright supporting accent used sparingly. Status colours remain semantic and pass contrast requirements. The interface must not introduce a rainbow of unrelated accents.

Money and escrow status never rely on colour alone. Every status includes a plain text label and, where useful, a simple icon.

### Typography

Continue using the local Outfit and Instrument Sans assets. Headings become smaller and more conversational. Large display numerals are reserved for genuinely important balances. Uppercase, widely tracked metadata is used rarely. Body copy remains readable and concise.

### Shape and depth

Use one documented radius system: controls at 12 pixels, cards at 18 pixels and pill shapes only for compact statuses and segmented controls. Shadows remain soft and tinted, with borders used only when they clarify grouping. Not every section becomes a card.

### Imagery and avatars

Use member profile images where they provide identity. Fall back to initials with a stable, accessible tint. Small purpose built line illustrations may be used for empty states. Decorative stock photography, fake testimonials and emoji clusters are excluded from the signed in application.

## Application shell

### Desktop

Replace the heavy dark customer sidebar with a lighter, calmer navigation rail. Keep the Push mark, the most important customer destinations and the account control visible. Group secondary destinations under a clear More or account menu instead of showing every possible route at equal weight.

The top bar contains the current page name, notifications and wallet connection state. Wallet state remains visible but compact. A saved receiving address must never be presented as an active Freighter signing session.

### Mobile

Keep a five item bottom navigation focused on Home, Work, Find, Messages and Account. Wallet and payments remain reachable from Home and Account. When Messages is unavailable because no project conversation exists, the layout must remain balanced and the destination must not silently change meaning.

Primary actions sit within natural thumb reach. Fixed navigation must respect safe area insets and never cover forms, notices or transaction actions.

### Customer and staff isolation

Add `customer-app-mode` only when the user is authenticated and `staff_portal_active` is false. Load a dedicated customer stylesheet after the existing authenticated styles and keep all new tokens and component selectors under that scope. Existing `.staff-portal-mode` presentation remains unchanged. Shared semantic markup may be improved only where the resulting staff output is verified unchanged.

Desktop secondary destinations use an accessible More menu. Mobile always exposes five stable destinations: Home, Work, Find, Messages and Account. Messages retains its existing empty state when no project conversation exists. Wallet, Payments and Notifications remain available through the top bar, Home and Account rather than competing for permanent mobile navigation space.

## Core product patterns

### Home

Home opens with a short greeting and one current priority rather than a giant financial dashboard. It shows active work, recent messages, the next required action and a compact wallet summary. A client with an unfunded agreement should see funding as the priority. A worker awaiting client funding should see an honest waiting state.

The priority is derived from existing assignment and escrow states. It does not introduce a new workflow state or change server authority.

### Jobs

Jobs use compact, readable opportunity rows or cards containing the title, client identity, budget and asset, timing, short scope and application status. Filters remain simple and horizontally scrollable on small screens. The primary action is consistent across the list and detail page.

### Work

Active assignments lead with progress and the next action. Status language uses human terms such as Agreed, Awaiting funding, Funded, Delivered, Revision requested, Disputed and Paid. Technical chain information remains available in a secondary details area.

### Workroom

The workroom presents a calm progress header, conversation, agreement details, delivery evidence and payment state without making every section equally prominent. Only one principal action appears for the current user and state. Sensitive or irreversible actions include plain consequences immediately beside the control.

### Messages

Messages borrow the clarity of modern chat applications: identifiable participants, readable bubbles, clear timestamps, delivery form at the bottom and strong empty and error states. Project context remains visible so a message cannot be mistaken for a different agreement.

### Wallet and payments

Wallet pages distinguish three concepts in plain language: saved receiving address, live Freighter connection and escrow transaction state. Connection, funding and release actions never blend together. Amount, asset, network fee, signer and recipient appear before approval. Testnet remains visible.

### Account and support

Settings use simple grouped lists rather than a wall of panels. Risky actions are separated from ordinary profile preferences. Support and recovery wording focuses on what happened and what the member can do next.

## Interaction and motion

1. Standard feedback lasts 150 to 250 milliseconds.
2. Buttons compress slightly on press and return without bouncing.
3. Pages and panels use short opacity and vertical movement only when it aids continuity.
4. Lists may animate new or changed items once, never continuously.
5. Success acknowledgement is compact and does not use confetti for wallet or payment events.
6. Loading states use skeletons shaped like the eventual content instead of generic spinners where practical.
7. Motion stops when the document is hidden and respects `prefers-reduced-motion`.
8. Wallet extension prompts and navigation are never delayed for animation.

## Content principles

Use short, conversational labels and explain consequences before technical detail. Prefer `Fund agreement` over `Execute funding transaction`, while retaining exact transaction details nearby. Error messages name the failed step, preserve the current state and give one recovery action. They must not imply that a rejected or pending wallet request succeeded.

## Accessibility and responsiveness

All interactive controls require visible focus, sufficient target size and accessible names. Text and control contrast must meet WCAG AA. Status cannot depend on colour alone. Content must work at 320, 390, 768, 1024 and 1440 pixel widths without horizontal page scrolling. Long Stellar addresses wrap or truncate visually while remaining available to copy. Reduced motion retains every state change without animation.

## Technical constraints

1. Continue using Django templates, native CSS and the existing JavaScript and GSAP assets.
2. Prefer CSS transitions for ordinary controls. Use GSAP only for coordinated sequences that cannot be expressed clearly in CSS.
3. Preserve server owned workflow state and existing wallet and escrow endpoints.
4. Do not rename hooks consumed by wallet, activity, form, escrow or conversation scripts without updating and testing those scripts.
5. Create or consolidate customer design tokens before page specific styling.
6. Avoid broad element selectors outside the customer scope.
7. Keep JavaScript enhancement optional for navigation and core form submission.

## Delivery sequence

1. Introduce customer scoping, tokens and the responsive shell.
2. Redesign Home as the reference page for spacing, type, surfaces and states.
3. Redesign Work, Jobs and their detail pages.
4. Redesign workrooms and conversations.
5. Redesign Wallet, Payments, Notifications, Account and Support.
6. Apply consistency corrections to remaining customer pages.
7. Verify the complete customer flow on desktop and mobile while confirming staff and landing presentation did not change.

Each sequence item should be reviewable independently. Existing uncommitted frontend work must be identified and preserved or intentionally superseded before implementation begins.

Community receives the shared customer tokens, shell and common component treatment during the consistency pass. A larger change to Community structure or behaviour is outside this phase.

## Verification

The redesign is complete when:

1. Customer pages share a coherent token, spacing, type, radius and interaction system.
2. Landing and staff operations screenshots remain materially unchanged.
3. Navigation works with keyboard, touch and narrow screens.
4. Wallet disconnected, saved address, connected, pending, rejected, failed and confirmed states remain distinct.
5. Job, application, agreement, funding, delivery, revision, dispute and release actions retain their existing permissions and server behaviour.
6. Page level smoke tests, existing Django tests and JavaScript checks pass.
7. Focus, contrast, reduced motion, long addresses, empty states, validation errors and loading feedback are inspected at the target widths.
8. No new claim suggests mainnet readiness, custody, guaranteed payment or AI authority over settlement.

## Builder discretion

The builder may choose exact spacing values, icon drawings, minor copy reductions and the composition of noncritical empty state illustrations provided they remain within this design system. Existing wallet, escrow, activity and form data hooks must remain intact. Current uncommitted landing and public reading styles must not be reset or folded into this redesign. Any change to navigation meaning, workflow order, wallet semantics, escrow behaviour, staff presentation or public claims requires a separate decision.
