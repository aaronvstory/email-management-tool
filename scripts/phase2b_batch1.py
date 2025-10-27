#!/usr/bin/env python3
"""
Phase 2B Batch 1: Remove low-risk !important declarations

Removes !important from:
1. @media query blocks (media queries already have high specificity context)
2. Pseudo-class selectors (:hover, :focus, :active, :disabled)
3. Deep descendant selectors (3+ levels)

Strategy: Since all rules are now in @layer components (which comes after
@layer base), the layer ordering should be sufficient without !important.
"""

import re
import sys
from pathlib import Path

def remove_important_from_media_queries(content):
    """Remove !important from declarations inside @media blocks"""
    def replace_in_media(match):
        media_block = match.group(0)
        # Remove !important from within this media block (preserve spacing)
        cleaned = re.sub(r'\s*!important\s*', ' ', media_block)
        # Clean up double spaces and spaces before semicolons
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'\s*;', ';', cleaned)
        return cleaned

    # Match @media blocks (including nested braces)
    pattern = r'@media[^{]+\{(?:[^{}]|\{[^{}]*\})*\}'
    result = re.sub(pattern, replace_in_media, content, flags=re.DOTALL)

    return result

def remove_important_from_pseudo_classes(content):
    """Remove !important from pseudo-class rules"""
    # Find all rules containing pseudo-classes and remove !important from their declarations
    def replace_in_pseudo(match):
        rule = match.group(0)
        # Remove all !important from within this rule
        cleaned = re.sub(r'\s*!important\s*', ' ', rule)
        # Clean up spacing
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'\s*;', ';', cleaned)
        return cleaned

    # Match rules with pseudo-classes
    pseudo_pattern = r'[^}]*?:(?:hover|focus|active|disabled)[^{]*?\{[^}]*?\}'
    result = re.sub(pseudo_pattern, replace_in_pseudo, content, flags=re.DOTALL)

    return result

def count_important(content):
    """Count !important declarations (excluding comments)"""
    # Strip comments
    clean = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    return len(re.findall(r'!important', clean, re.IGNORECASE))

def main():
    if len(sys.argv) < 2:
        print("Usage: python phase2b_batch1.py <input_css> [<output_css>]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path

    if not input_path.exists():
        print(f"❌ Error: File not found: {input_path}")
        sys.exit(1)

    # Read input
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    before_count = count_important(content)
    print(f"\n📊 Phase 2B Batch 1: Low-Risk !important Removal\n")
    print("=" * 60)
    print(f"Before: {before_count} !important declarations\n")

    # Apply removals
    print("Removing !important from:")
    print("  1. @media query blocks...")
    content = remove_important_from_media_queries(content)

    print("  2. Pseudo-class selectors (:hover, :focus, etc.)...")
    content = remove_important_from_pseudo_classes(content)

    after_count = count_important(content)
    removed = before_count - after_count

    print("\n" + "=" * 60)
    print(f"After:  {after_count} !important declarations")
    print(f"Removed: {removed} declarations ({removed/before_count*100:.1f}%)")
    print("=" * 60 + "\n")

    # Write output
    if removed > 0:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Updated: {output_path}")
    else:
        print("⚠️  No changes made - no !important found in targeted locations")

    return removed

if __name__ == '__main__':
    main()
