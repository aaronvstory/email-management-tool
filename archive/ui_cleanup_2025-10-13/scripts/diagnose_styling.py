#!/usr/bin/env python3
"""
Diagnostic script to check styling implementation issues
"""

import os
import sys

def check_bootstrap_table_overrides():
    """Check if Bootstrap table overrides are properly implemented"""
    base_html = 'templates/base.html'

    if not os.path.exists(base_html):
        print("❌ templates/base.html not found")
        return False

    with open(base_html, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for table background overrides
    table_bg_override = '--bs-table-bg: #1a1a1a !important;' in content
    table_color_override = '--bs-table-color: #ffffff !important;' in content
    table_cell_bg = 'background-color: #1a1a1a !important;' in content

    print("📊 Bootstrap Table Overrides:")
    print(f"   ✅ Table BG override: {'Yes' if table_bg_override else 'No'}")
    print(f"   ✅ Table color override: {'Yes' if table_color_override else 'No'}")
    print(f"   ✅ Table cell BG override: {'Yes' if table_cell_bg else 'No'}")

    return table_bg_override and table_color_override and table_cell_bg

def check_form_input_overrides():
    """Check if form input dark styling is properly implemented"""
    add_account_html = 'templates/add_account.html'

    if not os.path.exists(add_account_html):
        print("❌ templates/add_account.html not found")
        return False

    with open(add_account_html, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for comprehensive input styling
    form_container_inputs = '.form-container input,' in content
    form_container_select = '.form-container select,' in content
    webkit_autofill = '-webkit-autofill' in content
    important_styles = '!important' in content

    print("📝 Form Input Overrides:")
    print(f"   ✅ Form container inputs: {'Yes' if form_container_inputs else 'No'}")
    print(f"   ✅ Form container selects: {'Yes' if form_container_select else 'No'}")
    print(f"   ✅ Autofill fixes: {'Yes' if webkit_autofill else 'No'}")
    print(f"   ✅ Important declarations: {'Yes' if important_styles else 'No'}")

    return form_container_inputs and form_container_select and webkit_autofill

def check_navigation_icons():
    """Check if navigation icons are properly implemented"""
    base_html = 'templates/base.html'

    if not os.path.exists(base_html):
        print("❌ templates/base.html not found")
        return False

    with open(base_html, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for icons in navigation
    style_guide_icon = 'bi-palette2' in content
    test_suite_icon = 'bi-flask' in content
    diagnostics_icon = 'bi-heart-pulse' in content

    print("🧭 Navigation Icons:")
    print(f"   ✅ Style Guide icon: {'Yes' if style_guide_icon else 'No'}")
    print(f"   ✅ Test Suite icon: {'Yes' if test_suite_icon else 'No'}")
    print(f"   ✅ Diagnostics icon: {'Yes' if diagnostics_icon else 'No'}")

    return style_guide_icon and test_suite_icon and diagnostics_icon

def check_button_sizing():
    """Check if consistent button sizing is implemented"""
    base_html = 'templates/base.html'

    if not os.path.exists(base_html):
        print("❌ templates/base.html not found")
        return False

    with open(base_html, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for button sizing rules
    height_42px = 'height: 42px !important;' in content
    add_account_btn = '.add-account-btn' in content
    btn_group_sizing = '.btn-group' in content

    print("🔘 Button Sizing:")
    print(f"   ✅ 42px height rule: {'Yes' if height_42px else 'No'}")
    print(f"   ✅ Add account btn class: {'Yes' if add_account_btn else 'No'}")
    print(f"   ✅ Button group styling: {'Yes' if btn_group_sizing else 'No'}")

    return height_42px and add_account_btn

def main():
    print("🔍 STYLING IMPLEMENTATION DIAGNOSTIC")
    print("=" * 50)

    # Run all checks
    table_ok = check_bootstrap_table_overrides()
    forms_ok = check_form_input_overrides()
    nav_ok = check_navigation_icons()
    buttons_ok = check_button_sizing()

    print("\n📋 SUMMARY:")
    print(f"   Tables: {'✅ OK' if table_ok else '❌ ISSUES'}")
    print(f"   Forms: {'✅ OK' if forms_ok else '❌ ISSUES'}")
    print(f"   Navigation: {'✅ OK' if nav_ok else '❌ ISSUES'}")
    print(f"   Buttons: {'✅ OK' if buttons_ok else '❌ ISSUES'}")

    if not all([table_ok, forms_ok, nav_ok, buttons_ok]):
        print("\n⚠️  STYLING ISSUES DETECTED")
        print("See detailed findings above for specific problems.")
        return 1
    else:
        print("\n✅ All styling checks passed!")
        return 0

if __name__ == '__main__':
    sys.exit(main())