# Taskmaster Stitch UI Polish & Completion

**Estimated Duration**: 60-90 minutes  
**Branch**: feat/styleguide-refresh  
**Primary Tools**: Serena MCP (enabled), Taskmaster (this), GitHub/Chrome MCP (disabled by default)

## Mission Statement

Complete the Stitch UI migration by adopting reusable macros, fixing broken functionality, and ensuring visual consistency across all templates. The goal is a polished, production-ready interface that follows the established design system.

## Context & Prerequisites

### What's Already Done
- ✅ Stitch design system established with lime (#bef264) accent and dark theme
- ✅ Five core Stitch templates created: emails-unified, compose, rules, accounts, watchers
- ✅ Reusable macros created in `templates/stitch/_macros.html`
- ✅ Comprehensive styleguide at `templates/stitch/styleguide.html`
- ✅ CSS helpers in `static/css/stitch.components.css`

### Current Issues to Resolve
- ❌ Ad-hoc buttons and badges inconsistently styled across templates
- ❌ Missing email detail view in Stitch styling
- ❌ Attachments API returns HTTP 500 instead of graceful empty state
- ❌ Some navigation links may be broken or missing
- ❌ Sidebar active states need verification across all Stitch routes

## Task Breakdown

### Task 1: Macro Integration (Priority: High)
**Estimated Time**: 20 minutes

**Objective**: Import and use macros consistently across all Stitch templates

**Scope**:
- Update `templates/stitch/emails-unified.html`
- Update `templates/stitch/rules.html`
- Update `templates/stitch/accounts.html`
- Update `templates/stitch/watchers.html`

**Actions**:
1. Add `{% from 'stitch/_macros.html' import badge, icon_btn, toolbar %}` to each template
2. Replace inline status badges with `{{ badge('STATUS') }}` calls
3. Replace ad-hoc action buttons with `{{ icon_btn('Label', 'icon', 'variant') }}` calls
4. Replace toolbar headers with `{{ toolbar('Title', actions_array) }}` where appropriate

**Success Criteria**:
- All status badges (HELD, FETCHED, RELEASED, REJECTED) use consistent styling
- All action buttons have uniform appearance and hover states
- No template contains duplicate button/badge styling code
- Templates render without Jinja errors

**Deliverable**: Commit with message `feat(stitch): adopt macros for consistent UI components`

### Task 2: Email Detail View (Priority: High)
**Estimated Time**: 25 minutes

**Objective**: Create Stitch-styled email detail page with working attachments

**Scope**:
- Create `templates/stitch/email-detail.html` (new file)
- Add route `/email/<id>/stitch` if missing
- Fix attachments API to return safe empty state instead of 500 errors

**Actions**:
1. Use Serena to find existing email detail template and route
2. Create Stitch version with proper header, action toolbar, and attachments panel
3. Ensure attachments API handles missing files gracefully
4. Add safe error handling for email not found scenarios

**Success Criteria**:
- Email detail page renders with Stitch styling and layout
- Attachments load without errors or show "No attachments" message
- Edit/Release/Discard actions work correctly
- Back navigation returns to emails list

**Deliverable**: Commit with message `feat(stitch): email detail view with safe attachments handling`

### Task 3: Navigation & Route Verification (Priority: Medium)
**Estimated Time**: 15 minutes

**Objective**: Ensure all navigation links work and sidebar active states are correct

**Scope**:
- Verify sidebar active state logic in `templates/base.html`
- Check "Add Account" and "Import Accounts" links on accounts page
- Verify "Back to Emails" links on compose and other pages

**Actions**:
1. Test each Stitch route and verify sidebar highlights correctly
2. Fix any broken navigation links
3. Ensure Add Account button links to working route
4. Add missing routes if any are referenced but don't exist

**Success Criteria**:
- Sidebar shows lime highlight on correct menu item for each Stitch page
- All primary action buttons (Add Account, Compose, etc.) navigate correctly
- No broken links or 404 errors in navigation

**Deliverable**: Commit with message `fix(stitch): navigation links and sidebar active states`

### Task 4: Visual Polish & Spacing (Priority: Low)
**Estimated Time**: 10 minutes

**Objective**: Ensure consistent spacing and remove any visual inconsistencies

**Scope**:
- Verify all Stitch pages use consistent spacing (tw-p-4, tw-gap-4, tw-mb-4)
- Remove any remaining white button backgrounds
- Ensure hover states work on all interactive elements

**Actions**:
1. Audit all Stitch templates for spacing consistency
2. Replace any `tw-p-6` or `tw-p-8` with `tw-p-4` unless content requires more space
3. Verify no buttons have white backgrounds
4. Test hover states on links and buttons

**Success Criteria**:
- Consistent spacing throughout all Stitch pages
- No white button backgrounds anywhere
- All interactive elements have appropriate hover feedback
- Visual hierarchy is clear and consistent

**Deliverable**: Commit with message `chore(stitch): normalize spacing and polish visual details`

### Task 5: Quality Assurance (Priority: High)
**Estimated Time**: 10 minutes

**Objective**: Verify everything works and meets acceptance criteria

**Scope**:
- Manual testing of all Stitch routes
- Verify styleguide accuracy
- Run any available tests

**Actions**:
1. Visit each Stitch route: `/emails-unified/stitch`, `/compose/stitch`, `/rules/stitch`, `/accounts/stitch`, `/watchers/stitch`, `/styleguide/stitch`
2. Test key functionality: compose email, view email detail, manage accounts
3. Verify styleguide shows all components correctly
4. Run `pytest` if tests are available

**Success Criteria**:
- All pages load without errors
- Key user flows work end-to-end
- Visual consistency matches styleguide
- No console errors or broken functionality

**Deliverable**: Summary report of testing results and any remaining issues

## Technical Constraints

### Design System Rules (Non-Negotiable)
- **Colors**: Lime (#bef264) accent only, no Bootstrap blues, dark theme required
- **Corners**: Square edges (border-radius: 0px) unless component specifically needs rounding
- **Utilities**: Tailwind with `tw-` prefix, preflight disabled
- **Components**: Use macros from `_macros.html`, avoid inline component definitions

### Code Quality Standards
- All CSS changes go in `static/css/stitch.*.css` files only
- No modifications to backend logic or database schema
- Templates must import macros and use them consistently
- Commit messages follow conventional format: `type(scope): description`

### Performance Requirements
- Keep context usage minimal by using Serena for code navigation
- Summarize changes in commit messages, avoid verbose explanations
- Make small, atomic commits that can be easily reviewed

## Success Metrics

### Visual Consistency Score
- [ ] All status badges use macro-generated styling (HELD=amber, FETCHED=zinc, RELEASED=green)
- [ ] All action buttons follow icon-btn pattern with consistent spacing
- [ ] No white button backgrounds exist anywhere in Stitch templates
- [ ] Hover states provide appropriate visual feedback
- [ ] Spacing follows 4px grid system (tw-p-4, tw-gap-4, tw-mb-4)

### Functionality Score
- [ ] All Stitch routes load without errors
- [ ] Sidebar active state works for emails/compose/rules/accounts/watchers
- [ ] Email attachments load or show appropriate empty state
- [ ] Navigation links go to correct destinations
- [ ] Add Account button is visible and functional

### Code Quality Score
- [ ] All templates import and use macros consistently
- [ ] No duplicate component styling code exists
- [ ] CSS changes contained in appropriate stitch.*.css files
- [ ] Templates render without Jinja template errors
- [ ] Commits are atomic and have clear messages

## Emergency Stops

**Stop immediately if**:
- Any existing tests start failing
- Database errors or data corruption occurs
- Templates throw Jinja rendering errors that can't be quickly fixed
- More than 90 minutes elapsed

**On emergency stop**:
1. Document current state and any blocking issues
2. Commit any working changes with clear messages
3. Provide summary of completed vs. remaining tasks
4. Recommend next steps for continuation

## Handoff Requirements

### At Completion
1. **Status Summary**: Complete/Partial/Blocked for each task
2. **Testing Report**: Which routes tested, any issues found
3. **Commit List**: All commits made with brief description
4. **Remaining Work**: Any identified issues not addressed
5. **Recommendations**: Suggested next priorities or improvements

### Files to Review
- All `templates/stitch/*.html` files for macro adoption
- `static/css/stitch.components.css` for any additions
- Route files in `app/routes/` if any routes were added/modified
- `templates/base.html` if sidebar logic was updated

This task plan provides Claude with clear boundaries, measurable outcomes, and stopping conditions while ensuring the Stitch UI migration is completed professionally and maintainably.
