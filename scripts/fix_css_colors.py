#!/usr/bin/env python3
"""
CSS Color Fix Script
Replaces all forbidden bright red colors with dark red as per STYLEGUIDE.md
"""

import re

def fix_css_file(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Track what we're fixing
    fixes = {
        'bright_red_hex': 0,
        'bright_red_rgba': 0,
        'bright_red_rgba_spaced': 0,
        'ef4444': 0,
        'translateY_1px': 0
    }

    # 1. Replace #dc2626 with #7f1d1d
    original = content
    content = re.sub(r'#dc2626', '#7f1d1d', content, flags=re.IGNORECASE)
    fixes['bright_red_hex'] = len(re.findall(r'#dc2626', original, flags=re.IGNORECASE))

    # 2. Replace rgba(220,38,38, with rgba(127,29,29,
    original = content
    content = re.sub(r'rgba\(220,38,38,', 'rgba(127,29,29,', content, flags=re.IGNORECASE)
    fixes['bright_red_rgba'] = len(re.findall(r'rgba\(220,38,38,', original, flags=re.IGNORECASE))

    # 3. Replace rgba(220, 38, 38, with rgba(127, 29, 29,
    original = content
    content = re.sub(r'rgba\(220,\s*38,\s*38,', 'rgba(127, 29, 29,', content, flags=re.IGNORECASE)
    fixes['bright_red_rgba_spaced'] = len(re.findall(r'rgba\(220,\s*38,\s*38,', original, flags=re.IGNORECASE))

    # 4. Replace #ef4444 with #7f1d1d
    original = content
    content = re.sub(r'#ef4444', '#7f1d1d', content, flags=re.IGNORECASE)
    fixes['ef4444'] = len(re.findall(r'#ef4444', original, flags=re.IGNORECASE))

    # 5. Fix translateY(-1px) to translateY(-2px)
    original = content
    content = re.sub(r'translateY\(-1px\)', 'translateY(-2px)', content, flags=re.IGNORECASE)
    fixes['translateY_1px'] = len(re.findall(r'translateY\(-1px\)', original, flags=re.IGNORECASE))

    # Write the fixed content
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return fixes

if __name__ == '__main__':
    input_file = r'C:\claude\Email-Management-Tool\static\css\main.css'
    output_file = r'C:\claude\Email-Management-Tool\static\css\main.css'

    print("Fixing CSS colors...")
    fixes = fix_css_file(input_file, output_file)

    print("\nFixes applied:")
    print(f"  - Bright red hex (#dc2626): {fixes['bright_red_hex']} instances")
    print(f"  - Bright red rgba (no spaces): {fixes['bright_red_rgba']} instances")
    print(f"  - Bright red rgba (with spaces): {fixes['bright_red_rgba_spaced']} instances")
    print(f"  - #ef4444: {fixes['ef4444']} instances")
    print(f"  - translateY(-1px): {fixes['translateY_1px']} instances")
    print(f"\nTotal fixes: {sum(fixes.values())}")
    print("\n✅ CSS color fixes complete!")
