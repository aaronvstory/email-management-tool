#!/usr/bin/env python3
"""
CSS Gradient Removal Script
Removes all forbidden gradients per STYLEGUIDE.md (NO gradients on buttons/components)
Keeps ONLY body background radial-gradient as potentially acceptable
"""

import re

def fix_gradients(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Track what we're fixing
    fixes = {
        'modal_content_gradient': 0,
        'modal_header_gradient': 0,
        'card_gradient': 0,
        'btn_primary_modern_gradient': 0,
        'chart_container_gradient': 0,
        'btn_primary_gradient': 0,
        'btn_primary_hover_gradient': 0,
        'btn_success_gradient': 0,
        'btn_success_hover_gradient': 0,
        'btn_danger_gradient': 0,
        'btn_danger_hover_gradient': 0,
        'btn_warning_gradient': 0,
        'btn_warning_hover_gradient': 0,
        'btn_info_gradient': 0,
        'btn_info_hover_gradient': 0
    }

    # 1. Modal content gradient → flat surface
    original = content
    content = re.sub(
        r'\.modal-content,\s*\.modal \.modal-content,\s*\.modal-dialog \.modal-content \{\s*background: linear-gradient\([^)]+\) !important;',
        '.modal-content,\n.modal .modal-content,\n.modal-dialog .modal-content {\n    background: var(--surface-base) !important;',
        content,
        flags=re.DOTALL
    )
    if content != original:
        fixes['modal_content_gradient'] = 1

    # 2. Modal header gradient → flat red tint
    original = content
    content = re.sub(
        r'\.modal-header \{\s*background: linear-gradient\([^)]+\) !important;',
        '.modal-header {\n    background: rgba(127,29,29,0.12) !important;',
        content,
        flags=re.DOTALL
    )
    if content != original:
        fixes['modal_header_gradient'] = 1

    # 3. Card gradient → flat surface
    original = content
    content = re.sub(
        r'\.card \{\s*background: linear-gradient\([^)]+\) !important;',
        '.card {\n    background: var(--surface-base) !important;',
        content,
        flags=re.DOTALL
    )
    if content != original:
        fixes['card_gradient'] = 1

    # 4. .btn-primary-modern gradient (line 723)
    original = content
    content = re.sub(
        r'\.btn-primary-modern \{\s*background: linear-gradient\([^)]+\);',
        '.btn-primary-modern {\n    background: #667eea;',
        content,
        flags=re.DOTALL
    )
    if content != original:
        fixes['btn_primary_modern_gradient'] = 1

    # 5. Chart container gradient → flat surface
    original = content
    content = re.sub(
        r'\.chart-container \{\s*background: linear-gradient\([^)]+\);',
        '.chart-container {\n    background: var(--surface-base);',
        content,
        flags=re.DOTALL
    )
    if content != original:
        fixes['chart_container_gradient'] = 1

    # 6. .btn-primary, .btn-primary-modern (line 942)
    original = content
    content = re.sub(
        r'(\.btn-primary,\s*\.btn-primary-modern \{\s*)background: linear-gradient\([^)]+\) !important;',
        r'\1background: #667eea !important;',
        content,
        flags=re.DOTALL
    )
    if content != original:
        fixes['btn_primary_gradient'] = 1

    # 7. .btn-primary:hover gradient (line 951)
    original = content
    content = re.sub(
        r'(\.btn-primary:hover,\s*\.btn-primary-modern:hover,\s*\.btn-primary:focus,\s*\.btn-primary-modern:focus \{\s*)background: linear-gradient\([^)]+\) !important;',
        r'\1background: #5a6fd8 !important;',
        content,
        flags=re.DOTALL
    )
    if content != original:
        fixes['btn_primary_hover_gradient'] = 1

    # 8. .btn-success gradient (line 974)
    original = content
    content = re.sub(
        r'(\.btn-success,\s*\.btn-success-modern \{\s*)background: linear-gradient\([^)]+\) !important;',
        r'\1background: var(--success-base) !important;',
        content,
        flags=re.DOTALL
    )
    if content != original:
        fixes['btn_success_gradient'] = 1

    # 9. .btn-success:hover gradient (line 983)
    original = content
    content = re.sub(
        r'(\.btn-success:hover,\s*\.btn-success-modern:hover,\s*\.btn-success:focus,\s*\.btn-success-modern:focus \{\s*)background: linear-gradient\([^)]+\) !important;',
        r'\1background: #059669 !important;',
        content,
        flags=re.DOTALL
    )
    if content != original:
        fixes['btn_success_hover_gradient'] = 1

    # 10. .btn-danger gradient (line 989)
    original = content
    content = re.sub(
        r'(\.btn-danger \{\s*)background: linear-gradient\([^)]+\) !important;',
        r'\1background: var(--danger-base) !important;',
        content,
        flags=re.DOTALL
    )
    if content != original:
        fixes['btn_danger_gradient'] = 1

    # 11. .btn-danger:hover gradient (line 996)
    original = content
    content = re.sub(
        r'(\.btn-danger:hover,\s*\.btn-danger:focus \{\s*)background: linear-gradient\([^)]+\) !important;',
        r'\1background: #991b1b !important;',
        content,
        flags=re.DOTALL
    )
    if content != original:
        fixes['btn_danger_hover_gradient'] = 1

    # 12. .btn-warning gradient (line 1002)
    original = content
    content = re.sub(
        r'(\.btn-warning \{\s*)background: linear-gradient\([^)]+\) !important;',
        r'\1background: #f59e0b !important;',
        content,
        flags=re.DOTALL
    )
    if content != original:
        fixes['btn_warning_gradient'] = 1

    # 13. .btn-warning:hover gradient (line 1009)
    original = content
    content = re.sub(
        r'(\.btn-warning:hover,\s*\.btn-warning:focus \{\s*)background: linear-gradient\([^)]+\) !important;',
        r'\1background: #d97706 !important;',
        content,
        flags=re.DOTALL
    )
    if content != original:
        fixes['btn_warning_hover_gradient'] = 1

    # 14. .btn-info gradient (line 1016)
    original = content
    content = re.sub(
        r'(\.btn-info,\s*\.btn-info-modern \{\s*)background: linear-gradient\([^)]+\) !important;',
        r'\1background: #06b6d4 !important;',
        content,
        flags=re.DOTALL
    )
    if content != original:
        fixes['btn_info_gradient'] = 1

    # 15. .btn-info:hover gradient (line 1025)
    original = content
    content = re.sub(
        r'(\.btn-info:hover,\s*\.btn-info-modern:hover,\s*\.btn-info:focus,\s*\.btn-info-modern:focus \{\s*)background: linear-gradient\([^)]+\) !important;',
        r'\1background: #0891b2 !important;',
        content,
        flags=re.DOTALL
    )
    if content != original:
        fixes['btn_info_hover_gradient'] = 1

    # Write the fixed content
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return fixes

if __name__ == '__main__':
    input_file = r'C:\claude\Email-Management-Tool\static\css\main.css'
    output_file = r'C:\claude\Email-Management-Tool\static\css\main.css'

    print("Removing forbidden CSS gradients...")
    fixes = fix_gradients(input_file, output_file)

    print("\nGradients removed:")
    total = 0
    for key, count in fixes.items():
        if count > 0:
            label = key.replace('_', ' ').title()
            print(f"  - {label}: {count} instance(s)")
            total += count

    print(f"\nTotal gradients removed: {total}")
    print("Note: Body radial-gradient kept (acceptable per STYLEGUIDE.md)")
    print("\n✅ CSS gradient removal complete!")
