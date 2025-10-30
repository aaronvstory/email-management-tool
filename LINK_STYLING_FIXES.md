# Link Styling Fixes - Stitch Pattern

## 🎯 Goal: Consistent Link Styling Everywhere

Apply the reference link styling from `C:\claude\Stitch\emails-link\emails-link.html` to all navigation menus and link examples.

## 📋 Reference Pattern (Correct Stitch Styling)

### Default Link
```html
<a class="flex items-center gap-3 px-2 py-2 text-sm font-medium text-on-surface hover:bg-surface hover:text-on-surface-strong">
```

**Tailwind with tw- prefix**:
```html
<a class="tw-flex tw-items-center tw-gap-2.5 tw-px-3 tw-py-2 tw-text-[13px] tw-font-medium tw-text-[#a1a1aa] hover:tw-bg-[#27272a] hover:tw-text-[#f4f4f5]">
```

**Behavior**:
- Default: Gray text (#a1a1aa)
- Hover: Gray background (#27272a) + white text (#f4f4f5)

### Active Link
```html
<li class="relative">
  <span class="absolute left-0 top-0 bottom-0 w-1 bg-primary"></span>
  <a class="flex items-center gap-3 px-2 py-2 text-sm font-medium bg-primary/10 text-primary">
</li>
```

**Tailwind with tw- prefix**:
```html
<a class="tw-flex tw-items-center tw-gap-2.5 tw-px-3 tw-py-2 tw-text-[13px] tw-font-medium tw-bg-primary/10 tw-text-[#bef264] tw-border-l-[3px] tw-border-[#bef264]">
```

**Behavior**:
- Background: Lime green at 10% opacity (`bg-primary/10` or `rgba(190, 242, 100, 0.1)`)
- Text: Lime green (#bef264)
- Left border: 3px solid lime green

**Key Difference**: Active links have LIME GREEN TEXT, not white!

## 🔧 Files to Fix

### 1. templates/base.html (Sidebar Navigation)

**Current Problems**:
- ❌ Active links use `tw-bg-[#3f3f46]/70 tw-text-white` (dark gray + white text)
- ❌ Has `tw-rounded-md` (rounded corners - NOT Stitch!)
- ✓ Left border already correct (`tw-border-l-[3px] tw-border-[#bef264]`)

**Fix Required**:
```html
<!-- OLD (WRONG) -->
<a class="... tw-rounded-md tw-text-[#a1a1aa] ... hover:tw-bg-[#3f3f46] hover:tw-text-white {% if active %}tw-bg-[#3f3f46]/70 tw-text-white tw-border-l-[3px] tw-border-[#bef264]{% endif %}">

<!-- NEW (CORRECT) -->
<a class="... tw-text-[#a1a1aa] ... hover:tw-bg-[#27272a] hover:tw-text-[#f4f4f5] {% if active %}tw-bg-[#bef264]/10 tw-text-[#bef264] tw-border-l-[3px] tw-border-[#bef264] tw-pl-[9px]{% endif %}">
```

**Changes**:
1. Remove `tw-rounded-md` (sharp corners!)
2. Change hover background from `#3f3f46` → `#27272a` (lighter gray)
3. Change hover text from `white` → `#f4f4f5` (explicitly white)
4. Change active background from `#3f3f46/70` → `#bef264/10` (lime tint!)
5. Change active text from `white` → `#bef264` (lime green!)
6. Keep left border as-is (already correct)

### 2. templates/stitch/styleguide.html (Link Examples)

**Location**: Lines 230-257 (Navigation Links Section)

**Current Problems**:
- ✓ Default and hover links are correct
- ❌ Active link uses incorrect classes

**Fix Required**:
Update the "Active Link" example to use lime green text + lime green background tint.

## 🎨 Color Reference

- **Primary (Lime Green)**: #bef264
- **Primary 10% Opacity**: rgba(190, 242, 100, 0.1) or `bg-primary/10`
- **Surface (Panel Gray)**: #27272a
- **Border (Medium Gray)**: #3f3f46
- **On-Surface (Muted Text)**: #a1a1aa
- **On-Surface-Strong (White)**: #f4f4f5

## ✅ Implementation Checklist

- [ ] Fix base.html sidebar navigation (all ~10 links)
- [ ] Fix styleguide.html link examples
- [ ] Test hover states work correctly
- [ ] Test active states show lime green tint
- [ ] Verify NO rounded corners on links
- [ ] Test on all pages (dashboard, emails, compose, etc.)

## 📸 Visual Before/After

**Before (Wrong)**:
- Active link: Dark gray background + white text
- Rounded corners on links

**After (Correct)**:
- Active link: Lime green tint background + lime green text + left border
- Sharp corners (no border-radius)
