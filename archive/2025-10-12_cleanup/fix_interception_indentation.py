#!/usr/bin/env python3
"""Fix indentation issue in api_interception_release function"""

import re

# Read the file
with open('app/routes/interception.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the release function
start_pattern = r'@bp_interception\.route\(\'/api/interception/release/<int:msg_id>\', methods=\[\'POST\'\]\)'
func_start = content.find("@bp_interception.route('/api/interception/release/<int:msg_id>', methods=['POST'])")

if func_start != -1:
    # Find where the function ends (next function or end of file)
    next_route = content.find('@bp_interception.route', func_start + 100)
    if next_route == -1:
        next_route = len(content)

    # Extract the function
    func_content = content[func_start:next_route]

    # Fix the indentation issue
    # Lines after "with database_backup" should be indented
    lines = func_content.split('\n')
    fixed_lines = []
    in_backup_context = False
    backup_indent_level = 0

    for i, line in enumerate(lines):
        if 'with database_backup' in line:
            fixed_lines.append(line)
            in_backup_context = True
            backup_indent_level = len(line) - len(line.lstrip()) + 4  # Add 4 spaces for context
        elif in_backup_context and i < len(lines) - 1:
            # Check if this is the line after with statement
            if 'edited_subject' in line and 'payload.get' in line:
                # This should be indented inside the with block
                fixed_lines.append(' ' * backup_indent_level + line.lstrip())
            elif line.strip() and not line.lstrip().startswith('@'):
                # All the rest of the function body should be inside the with block
                if not line.startswith(' ' * backup_indent_level):
                    # Add proper indentation
                    fixed_lines.append(' ' * backup_indent_level + line.lstrip())
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

    # Replace in original content
    fixed_func = '\n'.join(fixed_lines)
    content = content[:func_start] + fixed_func + content[next_route:]

    # Write back
    with open('app/routes/interception.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ Fixed indentation in api_interception_release function")
else:
    print("❌ Could not find api_interception_release function")