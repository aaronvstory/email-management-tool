#!/usr/bin/env python3
"""
Count !important declarations in CSS files (excluding comments)
Used for Phase 2B proof requirements
"""

import re
import sys
from pathlib import Path

def strip_css_comments(content):
    """Remove CSS comments (/* ... */)"""
    return re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

def count_important(css_content):
    """Count !important declarations in CSS content"""
    # Strip comments first
    clean_css = strip_css_comments(css_content)

    # Count !important (case-insensitive)
    matches = re.findall(r'!important', clean_css, re.IGNORECASE)
    return len(matches)

def main():
    if len(sys.argv) < 2:
        print("Usage: python count_important.py <css_file> [<css_file2> ...]")
        sys.exit(1)

    total = 0
    results = []

    for file_path in sys.argv[1:]:
        path = Path(file_path)
        if not path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        count = count_important(content)
        total += count
        results.append((path.name, count))

    # Print results
    print("\n📊 !important Declaration Count (comment-stripped)\n")
    print("=" * 50)

    for filename, count in results:
        print(f"  {filename:30} {count:5} declarations")

    if len(results) > 1:
        print("=" * 50)
        print(f"  {'TOTAL':30} {total:5} declarations")

    print("\n")
    return total

if __name__ == '__main__':
    main()
