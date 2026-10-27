# Push Consumer Application Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the signed in Push customer experience into a simple, friendly and responsive consumer application without changing staff operations, the public landing page or financial workflow behaviour.

**Architecture:** Add an explicit `customer-app-mode` template scope and a dedicated `static/customer-app.css` layer loaded after existing authenticated styles. Improve customer templates in reviewable groups while preserving every server owned state transition and JavaScript data hook. Use markup contract tests plus existing behavioural tests, JavaScript syntax checks and browser screenshots at the target widths.

**Tech Stack:** Django templates and test client, native CSS, existing JavaScript and GSAP assets, Python unittest through `manage.py test`, Node syntax checks.

**Spec:** `docs/superpowers/specs/2026-10-25-push-consumer-app-redesign-design.md`

## Global Constraints

1. Public landing pages and staff operations must remain visually and behaviourally unchanged.
2. Add no frontend framework, component package or remote asset dependency.
3. Keep every wallet, escrow, activity, form and conversation data hook intact.
4. Keep wallet state, escrow state and testnet status explicit and distinct.
5. Standard interaction feedback lasts 150 to 250 milliseconds and respects `prefers-reduced-motion`.
6. Use controls at 12 pixels, cards at 18 pixels and pills only for compact status or segmented controls.
7. Meet WCAG AA contrast, visible focus and touch target requirements.
8. Support 320, 390, 768, 1024 and 1440 pixel widths without horizontal page scrolling.
9. Do not reset or include the existing unrelated modifications in `static/landing-cinematic.css` or `static/public-reading.css`.
10. Do not alter job, application, agreement, escrow, wallet, dispute or staff permissions.

## Review Focus

1. A staff member must never receive `customer-app-mode` or the customer stylesheet; Task 1 pins both conditions.
2. A customer with no project conversations must still see a functional Messages destination and empty state; Task 1 pins this navigation state.
3. Saved wallet address, active Freighter session and escrow transaction state must remain separate; Task 5 pins all visible states and retains current behavioural coverage.
4. Long names, job titles and Stellar addresses must wrap or truncate without page overflow at 320 pixels; Tasks 3 and 5 add browser assertions.
5. Reduced motion and keyboard focus must retain all content and actions; Task 7 adds browser and stylesheet assertions.

---

### Task 1: Isolate and simplify the customer application shell

**Files:**

1. Create: `static/customer-app.css`
2. Create: `core/test_consumer_ui.py`
3. Modify: `templates/base.html`

**Interfaces:**

1. Consumes: `staff_portal_active`, existing route names, unread counts and wallet template values.
2. Produces: `body.customer-app-mode`, the `customer-app.css` link, stable `.customer-primary-nav`, `.customer-more-menu` and `.customer-mobile-dock` markup for later tasks.

- [ ] **Step 1: Write failing shell contract tests**

Add `ConsumerShellTests` covering a normal verified member and an approved staff member. Assert that normal customer responses contain `customer-app-mode` and `customer-app.css`; staff responses contain neither; landing responses contain neither. Assert that the customer mobile dock always contains exactly Home, Work, Find, Messages and Account even when `has_project_conversations` is false.

- [ ] **Step 2: Run the shell tests and confirm failure**

Run: `python manage.py test core.test_consumer_ui.ConsumerShellTests --noinput`

Expected: FAIL because the customer class, stylesheet and stable navigation do not exist.

- [ ] **Step 3: Add the customer template scope and stable navigation**

In `templates/base.html`, emit `customer-app-mode` and load `customer-app.css` only for authenticated requests where `staff_portal_active` is false. Replace only the customer sidebar and mobile navigation branches. Keep Home, Work, Find and Messages visible, move secondary routes to an accessible desktop More menu and retain notification and wallet controls in the top bar. Do not alter the staff branches or data attributes.

- [ ] **Step 4: Establish customer tokens and shell styles**

In `static/customer-app.css`, define customer scoped colour, type, spacing, radius, shadow and motion tokens. Style the light navigation rail, compact top bar, More menu and five item mobile dock. Add visible `:focus-visible`, pressed state and reduced motion rules. Keep every selector rooted at `.customer-app-mode`.

- [ ] **Step 5: Run shell and staff regression tests**

Run: `python manage.py test core.test_consumer_ui.ConsumerShellTests core.tests --noinput`

Expected: PASS with existing staff access, wallet and navigation behaviour preserved.

- [ ] **Step 6: Commit the shell**

Commit: `feat: add isolated consumer application shell`

### Task 2: Recompose Home around the member's next action

**Files:**

1. Modify: `core/views.py`
2. Modify: `templates/workspace.html`
3. Modify: `static/customer-app.css`
4. Test: `core/test_consumer_ui.py`

**Interfaces:**

1. Consumes: existing assignments, own jobs, applications, earnings and recent messages from `workspace`.
2. Produces: `workspace_priority` as a presentation dictionary containing `kind`, `title`, `body`, `url` and `action_label`; no new database or workflow state.

- [ ] **Step 1: Write failing priority and Home markup tests**

Add tests for client awaiting funding, worker awaiting client funding, worker awaiting acceptance, submitted work awaiting client review and no active work. Assert the selected `workspace_priority.kind`, honest role specific wording and a single priority action. Assert Home still exposes active work, messages and a compact wallet summary without the old giant earnings presentation.

- [ ] **Step 2: Run the Home tests and confirm failure**

Run: `python manage.py test core.test_consumer_ui.ConsumerHomeTests --noinput`

Expected: FAIL because `workspace_priority` and the new markup do not exist.

- [ ] **Step 3: Derive the presentation priority in `workspace`**

Add a private presentation helper near `workspace` with signature `_workspace_priority(user, assignments) -> dict`. Order actionable states before waiting states, return route URLs through `reverse`, and never modify models. Keep current query ownership and privacy rules.

- [ ] **Step 4: Rebuild `workspace.html` using the customer component vocabulary**

Create a short greeting, one priority panel, compact active work list, recent message preview and wallet summary. Retain current links and honest testnet earnings language. Remove decorative payment motion and oversized balance hierarchy from Home only.

- [ ] **Step 5: Add Home component styles and responsive fallbacks**

Add scoped priority, avatar, list, summary and empty state styles. Verify the first meaningful action remains above the fold at 390 and 1440 pixels.

- [ ] **Step 6: Run Home and existing workspace tests**

Run: `python manage.py test core.test_consumer_ui.ConsumerHomeTests core.tests.PushTests.test_workspace_greeting_uses_the_current_weekday --noinput`

Expected: PASS.

- [ ] **Step 7: Commit Home**

Commit: `feat: focus customer home on the next action`

### Task 3: Simplify work management and job discovery

**Files:**

1. Modify: `templates/work.html`
2. Modify: `templates/assigned_work.html`
3. Modify: `templates/jobs.html`
4. Modify: `templates/job_row.html`
5. Modify: `templates/job_detail.html`
6. Modify: `templates/job_form.html`
7. Modify: `templates/application_form.html`
8. Modify: `static/customer-app.css`
9. Test: `core/test_consumer_ui.py`

**Interfaces:**

1. Consumes: existing `selected_view`, job, application and assignment context values.
2. Produces: reusable `.consumer-segmented-nav`, `.consumer-work-card`, `.consumer-job-card`, `.consumer-status` and `.consumer-empty-state` markup.

- [ ] **Step 1: Write failing work and jobs presentation tests**

Assert the four work views retain their existing counts, URLs and permission dependent actions while using the new components. Assert a job card contains title, client identity, budget display, short scope and current application state. Assert forms retain labels, CSRF and current action URLs.

- [ ] **Step 2: Run the work and jobs tests and confirm failure**

Run: `python manage.py test core.test_consumer_ui.ConsumerWorkTests core.test_consumer_ui.ConsumerJobsTests --noinput`

Expected: FAIL because the new component markup is absent.

- [ ] **Step 3: Recompose work navigation and records**

Convert the four work views into a horizontally scrollable segmented control on narrow screens and concise record cards. Keep Needs my action first, preserve all current state divisions and use plain status labels without changing model display values.

- [ ] **Step 4: Recompose job discovery, detail and forms**

Use a compact filter bar and opportunity cards. Place the single primary action consistently on list and detail pages. Preserve owner controls, application privacy, closed state handling, form field names and every existing URL.

- [ ] **Step 5: Add responsive and long content styles**

Allow long names and titles to wrap within cards, keep budget and asset readable, and prevent overflow at 320 pixels. Keep desktop lists scannable without reverting to dense tables.

- [ ] **Step 6: Run work, job and application behaviour tests**

Run: `python manage.py test core.test_consumer_ui.ConsumerWorkTests core.test_consumer_ui.ConsumerJobsTests core.tests.PushTests.test_work_page_separates_worker_and_hiring_views core.tests.PushTests.test_work_page_tabs_keep_applications_and_posted_jobs_separate core.tests.PushTests.test_applications_private_and_duplicate_prevented --noinput`

Expected: PASS.

- [ ] **Step 7: Commit work and jobs**

Commit: `feat: simplify customer work and job discovery`

### Task 4: Clarify workrooms and conversations

**Files:**

1. Modify: `templates/assignment.html`
2. Modify: `templates/escrow_assignment.html`
3. Modify: `templates/messages.html`
4. Modify: `static/customer-app.css`
5. Test: `core/test_consumer_ui.py`

**Interfaces:**

1. Consumes: existing assignment permissions, escrow context, participants, messages and form actions.
2. Produces: `.consumer-workroom`, `.consumer-progress`, `.consumer-primary-action`, `.consumer-chat` and `.consumer-chat-composer` presentation patterns.

- [ ] **Step 1: Write failing workroom and chat contract tests**

Cover awaiting acceptance, awaiting funding, funded, submitted, revision, disputed and paid assignments for the relevant participant. Assert one principal action appears for the current state, status text remains present, destructive consequences remain adjacent and every escrow and wallet data hook survives. Assert participant only message access and read only states remain visible.

- [ ] **Step 2: Run the workroom tests and confirm failure**

Run: `python manage.py test core.test_consumer_ui.ConsumerWorkroomTests --noinput`

Expected: FAIL because the new hierarchy and component classes are absent.

- [ ] **Step 3: Recompose assignment and escrow workrooms**

Add a calm progress header and organise agreement, conversation, delivery and payment details by current relevance. Show exactly one principal action per role and state. Keep technical chain details in an accessible secondary details region. Do not rename forms, actions, endpoints or JavaScript hooks.

- [ ] **Step 4: Recompose Messages**

Keep project context visible in the chat header, improve participant identity and bubble rhythm, keep the composer near the thumb area on mobile and preserve the explicit statement that messages are not end to end encrypted.

- [ ] **Step 5: Add workroom and conversation responsive styles**

At narrow widths, switch the conversation list and active chat into clear sequential views without hiding navigation. Ensure fixed or sticky elements do not cover inputs or notices.

- [ ] **Step 6: Run assignment, escrow and privacy tests**

Run: `python manage.py test core.test_consumer_ui.ConsumerWorkroomTests core.test_escrow core.tests.PushTests.test_assignment_messages_are_participant_only core.tests.PushTests.test_outsider_cannot_read_or_change_assignment --noinput`

Expected: PASS.

- [ ] **Step 7: Commit workrooms and conversations**

Commit: `feat: clarify workrooms and project conversations`

### Task 5: Make wallet and payment states unmistakable

**Files:**

1. Modify: `templates/wallet.html`
2. Modify: `templates/payments.html`
3. Modify: `templates/base.html`
4. Modify: `static/customer-app.css`
5. Test: `core/test_consumer_ui.py`

**Interfaces:**

1. Consumes: existing wallet session values, saved address, testnet balances, payment records and `data-wallet-*` hooks.
2. Produces: explicit receiving address, live connection and escrow transaction state sections without changing wallet endpoints.

- [ ] **Step 1: Write failing wallet state presentation tests**

Cover no saved address, saved but disconnected, connected matching wallet, stale or changed wallet, pending escrow transaction, rejected request, confirmed settlement and unavailable balance. Assert exact state labels, testnet disclosure, amount, asset, fee explanation, signer and recipient are visible where relevant. Assert all existing wallet hooks remain.

- [ ] **Step 2: Run wallet presentation tests and confirm failure**

Run: `python manage.py test core.test_consumer_ui.ConsumerWalletTests --noinput`

Expected: FAIL because state sections and labels are absent.

- [ ] **Step 3: Recompose wallet and payment templates**

Separate receiving identity, current Freighter session and escrow records into distinct sections. Use compact summaries with detailed transaction evidence available on demand. Preserve the server prepared transaction flow and existing controls.

- [ ] **Step 4: Restyle the top wallet menu within customer scope**

Keep connection state readable in the collapsed control and show saved versus connected language inside the panel. Staff wallet markup remains untouched.

- [ ] **Step 5: Add address, transaction and mobile safety styles**

Use safe wrapping and copy friendly address blocks. Keep approval controls visible without covering notices. Ensure warning and failure states do not rely on colour.

- [ ] **Step 6: Run wallet, escrow and JavaScript tests**

Run: `python manage.py test core.test_consumer_ui.ConsumerWalletTests core.test_escrow core.tests.PushTests.test_wallet_disconnect_ends_session_but_keeps_receiving_address core.tests.PushTests.test_wallet_sync_restores_matching_testnet_session --noinput`

Run: `node --test tests/wallet-state.test.cjs`

Expected: PASS for both commands.

- [ ] **Step 7: Commit wallet and payments**

Commit: `feat: clarify wallet and payment states`

### Task 6: Apply the consumer system to remaining customer pages

**Files:**

1. Modify: `templates/notifications.html`
2. Modify: `templates/account_settings.html`
3. Modify: `templates/profile.html`
4. Modify: `templates/analytics.html`
5. Modify: `templates/support.html`
6. Modify: `templates/support_ticket.html`
7. Modify: `templates/community.html`
8. Modify: `templates/community_detail.html`
9. Modify: `templates/community_form.html`
10. Modify: `static/customer-app.css`
11. Test: `core/test_consumer_ui.py`

**Interfaces:**

1. Consumes: shared customer tokens and components from Tasks 1 through 5.
2. Produces: consistent settings groups, notification rows, support states and community surfaces without structural feature changes.

- [ ] **Step 1: Write failing remaining page consistency tests**

Assert each route renders inside the customer scope, retains its primary form or action and uses the shared heading, group, status and empty state classes. Assert account deletion remains separated from ordinary settings and Support retains ticket state and feedback actions.

- [ ] **Step 2: Run the consistency tests and confirm failure**

Run: `python manage.py test core.test_consumer_ui.ConsumerRemainingPagesTests --noinput`

Expected: FAIL because the shared customer component classes are absent.

- [ ] **Step 3: Recompose notifications, account, profile and analytics**

Use grouped lists and concise summaries. Preserve every field, form action, privacy restriction and dangerous action. Analytics remains readable and does not introduce unsupported financial claims.

- [ ] **Step 4: Recompose support and community using the common system**

Improve hierarchy and empty states without changing moderation, visibility, reporting or reply behaviour. Do not expand Community into a new product feature.

- [ ] **Step 5: Run remaining customer and support tests**

Run: `python manage.py test core.test_consumer_ui.ConsumerRemainingPagesTests core.tests --noinput`

Expected: PASS.

- [ ] **Step 6: Commit remaining pages**

Commit: `feat: unify remaining customer pages`

### Task 7: Add restrained motion and complete visual regression verification

**Files:**

1. Create: `static/customer-motion.js`
2. Modify: `templates/base.html`
3. Modify: `static/customer-app.css`
4. Modify: `docs/frontend-verification.md`
5. Test: `core/test_consumer_ui.py`

**Interfaces:**

1. Consumes: customer component classes and the existing GSAP runtime.
2. Produces: customer scoped enhancement only, with CSS as the default and JavaScript used only for coordinated entry or changed item acknowledgement.

- [ ] **Step 1: Write failing enhancement inclusion tests**

Assert `customer-motion.js` loads only for customer pages, staff and public pages exclude it, core navigation and forms remain present without relying on JavaScript and the stylesheet contains reduced motion handling.

- [ ] **Step 2: Run enhancement tests and confirm failure**

Run: `python manage.py test core.test_consumer_ui.ConsumerMotionTests --noinput`

Expected: FAIL because the script and final motion contract are absent.

- [ ] **Step 3: Implement customer scoped motion**

Use CSS for hover, focus, press and simple reveal transitions. In `customer-motion.js`, enhance only explicitly marked customer elements, stop work in hidden documents and exit immediately for reduced motion. Do not delay wallet prompts, route navigation or form submission.

- [ ] **Step 4: Run syntax and automated regression checks**

Run: `node --check static/customer-motion.js`

Run: `python manage.py test core.test_consumer_ui core.tests core.test_escrow core.test_escrow_staff --noinput`

Run: `node --test tests/wallet-state.test.cjs`

Expected: all commands PASS.

- [ ] **Step 5: Perform browser verification**

Inspect Home, Work, Jobs, a job detail, workroom, Messages, Wallet, Payments, Account and Support at 320, 390, 768, 1024 and 1440 pixels. Verify keyboard order, visible focus, reduced motion, empty states, validation errors, long addresses and no horizontal page overflow. Capture comparison screenshots for customer, staff operations and the public landing page.

- [ ] **Step 6: Record verified evidence**

Update `docs/frontend-verification.md` with the exact tested revision, routes, widths, passed behaviours and any remaining limits. Do not claim device or browser coverage that was not exercised.

- [ ] **Step 7: Commit motion and verification**

Commit: `feat: finish consumer application redesign`

## Self Review

1. Spec coverage: all scope, design language, shell, page patterns, motion, accessibility, technical boundaries and verification requirements map to Tasks 1 through 7.
2. Step scan: every step produces one test, implementation, verification or commit result.
3. Interface consistency: `customer-app-mode`, `customer-app.css`, stable navigation and component class names originate in Task 1 and are consumed by later tasks.
4. Review focus: staff isolation, empty Messages navigation, wallet state separation, narrow content and reduced motion each have an owning test task.
5. Proportion: the plan names decisions and proof points without transcribing template or CSS implementations.
