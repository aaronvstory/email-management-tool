# Convert standalone Stitch templates to Flask templates
import re
import sys

# Get template name from command line or use default
template_name = sys.argv[1] if len(sys.argv) > 1 else "styleguide"
input_file = f"templates/new/{template_name}.html"
output_file = f"templates/stitch/{template_name}.html"

with open(input_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract only the main content (skip sidebar)
# Try multiple patterns to find main content start
body_start = content.find('<main class="flex-1')
if body_start == -1:
    body_start = content.find('<div class="max-w-7xl')
if body_start == -1:
    body_start = content.find('<div class="max-w-4xl')

# Find the closing tag
body_end = content.find('</body>')
if body_start == -1:
    print("ERROR: Could not find main content start marker")
    sys.exit(1)

body_content = content[body_start:body_end].strip()

# Add tw- prefix to all Tailwind classes except custom ones
def add_tw_prefix(match):
    classes = match.group(1)
    result_classes = []

    # Custom classes that should NOT get tw- prefix
    custom_classes = {'btn', 'btn-primary-modern', 'btn-secondary', 'btn-danger',
                     'input-modern', 'modal-modern', 'panel', 'panel-header',
                     'panel-body', 'panel-footer', 'stat-card-modern', 'panel-modern',
                     'nav-item-link', 'material-symbols-outlined', 'is-invalid', 'active',
                     'dark'}

    for cls in classes.split():
        # Skip if already has tw- or is a custom class
        if cls.startswith('tw-') or cls in custom_classes:
            result_classes.append(cls)
        # Add tw- to everything else
        else:
            result_classes.append('tw-' + cls)

    return 'class="' + ' '.join(result_classes) + '"'

body_content = re.sub(r'class="([^"]*)"', add_tw_prefix, body_content)

# Create Flask template with dynamic title
title_name = template_name.replace('-', ' ').title()
div_id = template_name.replace('-', '_')
header = '''{% extends "base.html" %}

{% block title %}''' + title_name + ''' - Email Management Tool{% endblock %}

{% block content %}
<div id="''' + div_id + '''">
'''

footer = '''
</div>
{% endblock %}
'''

flask_template = header + body_content + footer

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(flask_template)

print("✓ Converted styleguide saved to: " + output_file)
print("✓ Added tw- prefixes and Flask template structure")
