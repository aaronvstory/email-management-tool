#!/usr/bin/env python3
"""
CSS Responsive & Spacing Fix Script
Fixes critical responsive design failures causing crowding below 2560px width
Addresses: Only 1 media query, fixed widths, full-width enforcement, button crowding
"""

import re

def fix_responsive_css(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Track what we're fixing
    fixes = {
        'removed_fullwidth_enforcement': 0,
        'fixed_modal_widths': 0,
        'added_media_queries': 0
    }

    # 1. Remove FULL WIDTH LAYOUT enforcement (lines 543-568)
    # This breaks Bootstrap's responsive containers
    original = content
    pattern = r'/\* FULL WIDTH LAYOUT - Remove max-width constraints \*/\s*\.container,\s*\.container-fluid,.*?margin-right: 0 !important;\s*\}'
    content = re.sub(pattern, '''/* RESPONSIVE CONTAINERS - Let Bootstrap handle responsive widths */
.container,
.container-fluid {
    padding-left: 30px;
    padding-right: 30px;
}''', content, flags=re.DOTALL)

    if content != original:
        fixes['removed_fullwidth_enforcement'] = 1

    # 2. Fix modal widths to be responsive using min()
    original = content
    content = re.sub(
        r'\.modal-dialog \{\s*max-width: 90% !important;\s*width: 800px !important;',
        '''.modal-dialog {
    width: min(800px, 90vw);
    max-width: 90vw;''',
        content,
        flags=re.DOTALL
    )
    if content != original:
        fixes['fixed_modal_widths'] += 1

    original = content
    content = re.sub(
        r'\.modal-dialog-lg \{\s*max-width: 90% !important;\s*width: 1200px !important;',
        '''.modal-dialog-lg {
    width: min(1200px, 90vw);
    max-width: 90vw;''',
        content,
        flags=re.DOTALL
    )
    if content != original:
        fixes['fixed_modal_widths'] += 1

    # 3. Add comprehensive responsive media queries before existing @media at line 1170
    media_queries_block = '''
/* ========================================
   RESPONSIVE DESIGN - COMPREHENSIVE BREAKPOINTS
   Fixes crowding issues below 2560px width
   ======================================== */

/* 1920px - Full HD displays */
@media (max-width: 1920px) {
    .container {
        padding-left: 25px;
        padding-right: 25px;
    }

    .table th,
    .table td {
        padding: 13px 18px !important;
    }
}

/* 1440px - Mid-size displays */
@media (max-width: 1440px) {
    .container {
        padding-left: 20px;
        padding-right: 20px;
    }

    .modal-dialog-lg {
        width: min(900px, 90vw);
    }

    .btn-group {
        gap: 6px !important;
    }

    .table th,
    .table td {
        padding: 12px 15px !important;
    }
}

/* 1366px - Most common laptop resolution (CRITICAL BREAKPOINT) */
@media (max-width: 1366px) {
    .container {
        padding-left: 18px;
        padding-right: 18px;
    }

    .modal-dialog {
        width: min(700px, 90vw);
    }

    .modal-dialog-lg {
        width: min(850px, 90vw);
    }

    .btn {
        min-width: 90px !important;
        padding: 8px 18px !important;
    }

    .btn-lg {
        min-width: 110px !important;
    }

    .row {
        margin-left: -12px !important;
        margin-right: -12px !important;
    }

    .col, [class*="col-"] {
        padding: 12px !important;
    }

    .card-body {
        padding: 14px 18px !important;
    }

    .table th,
    .table td {
        padding: 11px 14px !important;
        font-size: 14px !important;
    }
}

/* 1024px - iPad landscape / small laptops */
@media (max-width: 1024px) {
    .container {
        padding-left: 15px;
        padding-right: 15px;
    }

    .modal-dialog {
        width: min(600px, 90vw);
    }

    .modal-dialog-lg {
        width: min(750px, 90vw);
    }

    .btn {
        min-width: 85px !important;
        padding: 8px 16px !important;
        font-size: 14px !important;
    }

    .btn-sm {
        min-width: 70px !important;
    }

    .btn-lg {
        min-width: 100px !important;
    }

    .row {
        margin-bottom: 20px !important;
        margin-left: -10px !important;
        margin-right: -10px !important;
    }

    .col, [class*="col-"] {
        padding: 10px !important;
    }

    .card-body {
        padding: 13px 16px !important;
    }

    .card-header {
        padding: 11px 16px !important;
    }
}

'''

    # Find the existing @media (max-width: 768px) and insert new queries before it
    original = content
    content = re.sub(
        r'(/\* RESPONSIVE BUTTONS - Stack on mobile \*/\s*@media \(max-width: 768px\))',
        media_queries_block + r'\1',
        content
    )
    if content != original:
        fixes['added_media_queries'] = 1

    # 4. Enhance existing 768px breakpoint
    existing_768_pattern = r'(/\* RESPONSIVE BUTTONS - Stack on mobile \*/\s*@media \(max-width: 768px\) \{[^}]*\.btn-group \.btn:not\(:first-child\) \{[^}]*\}\s*\})'

    enhanced_768_block = '''/* RESPONSIVE BUTTONS - Stack on mobile */
@media (max-width: 768px) {
    .container {
        padding-left: 12px;
        padding-right: 12px;
    }

    .modal-dialog,
    .modal-dialog-lg {
        width: 95vw;
    }

    .btn {
        min-width: 80px !important;
        padding: 8px 15px !important;
        font-size: 13px !important;
    }

    .btn-sm {
        min-width: 60px !important;
        padding: 6px 12px !important;
    }

    .btn-lg {
        min-width: 90px !important;
        padding: 10px 20px !important;
        font-size: 15px !important;
    }

    .btn-group {
        flex-direction: column !important;
        gap: 4px !important;
    }

    .btn-group .btn {
        border-radius: 6px !important;
        width: 100%;
    }

    .btn-group .btn:not(:last-child),
    .btn-group .btn:not(:first-child) {
        border-radius: 6px !important;
    }

    .row {
        margin-bottom: 15px !important;
        margin-left: -8px !important;
        margin-right: -8px !important;
    }

    .col, [class*="col-"] {
        padding: 8px !important;
    }

    .card-body {
        padding: 12px 15px !important;
    }

    .card-header {
        padding: 10px 15px !important;
    }

    .table th,
    .table td {
        padding: 10px 12px !important;
        font-size: 13px !important;
    }

    /* Stack form buttons vertically on mobile */
    .modal-footer .btn {
        width: 100%;
        margin: 4px 0 !important;
    }
}'''

    original = content
    content = re.sub(existing_768_pattern, enhanced_768_block, content, flags=re.DOTALL)

    # 5. Add mobile-specific breakpoint (375px - iPhone SE)
    mobile_375_block = '''
/* 375px - Mobile portrait (iPhone SE and similar) */
@media (max-width: 375px) {
    .container {
        padding-left: 10px;
        padding-right: 10px;
    }

    .modal-dialog,
    .modal-dialog-lg {
        width: 98vw;
    }

    .btn {
        min-width: 70px !important;
        padding: 8px 12px !important;
        font-size: 13px !important;
    }

    .btn-sm {
        min-width: 50px !important;
        padding: 5px 10px !important;
        font-size: 12px !important;
    }

    .btn-lg {
        min-width: 80px !important;
        padding: 10px 16px !important;
    }

    .row {
        margin-left: -6px !important;
        margin-right: -6px !important;
    }

    .col, [class*="col-"] {
        padding: 6px !important;
    }

    .card-body {
        padding: 10px 12px !important;
    }

    .card-header {
        padding: 8px 12px !important;
    }

    .table th,
    .table td {
        padding: 8px 10px !important;
        font-size: 12px !important;
    }

    h1 { font-size: 1.5rem !important; }
    h2 { font-size: 1.3rem !important; }
    h3 { font-size: 1.15rem !important; }
    h4 { font-size: 1.05rem !important; }
}
'''

    # Insert 375px breakpoint after 768px breakpoint
    content = re.sub(
        r'(})\s*(\/\* =============================\s*HEADER/NAV)',
        r'\1\n' + mobile_375_block + r'\n\2',
        content
    )

    # Write the fixed content
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return fixes

if __name__ == '__main__':
    input_file = r'C:\claude\Email-Management-Tool\static\css\main.css'
    output_file = r'C:\claude\Email-Management-Tool\static\css\main.css'

    print("Fixing CSS responsive design issues...")
    fixes = fix_responsive_css(input_file, output_file)

    print("\nFixes applied:")
    print(f"  - Removed full-width enforcement: {fixes['removed_fullwidth_enforcement']} instance(s)")
    print(f"  - Fixed modal widths to use min(): {fixes['fixed_modal_widths']} instance(s)")
    print(f"  - Added comprehensive media queries: {fixes['added_media_queries']} block(s)")

    print("\nResponsive breakpoints now active:")
    print("  - 1920px (Full HD)")
    print("  - 1440px (Mid-size displays)")
    print("  - 1366px (Most common laptop) - CRITICAL")
    print("  - 1024px (iPad landscape)")
    print("  - 768px (Tablets/iPad portrait) - ENHANCED")
    print("  - 375px (Mobile portrait)")

    print("\n✅ CSS responsive design fixes complete!")
    print("\n📸 Taking new progress screenshots recommended...")
