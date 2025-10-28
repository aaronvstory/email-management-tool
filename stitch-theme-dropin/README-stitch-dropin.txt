
# Stitch Skin Drop-in (dev-first)

Files in this folder:
- stitch.theme.css  → put in **/static/css/** (recommended)
- dev-overrides.css → put in **/static/css/** (or /static/ if you prefer)
- patch.dashboard-emails.css → put in **/static/css/** (emails_unified already links to it)
- base.html.patch.cssdir → example patch that adds the theme link using /static/css/

## Steps
1) Copy the CSS files into `/static/css/` in your app.
2) Edit `templates/base.html` and add the theme below your base CSS:
   ```html
   <link rel="stylesheet" href="{{ url_for('static', filename='css/stitch.theme.css') }}">
   ```
3) Keep your dev flag for overrides at the very end of <head>:
   ```html
   {% if request.args.get('devcss') == '1' %}
   <link rel="stylesheet" href="{{ url_for('static', filename='css/dev-overrides.css') }}">
   {% endif %}
   ```
   (Update the path to `css/dev-overrides.css` if you place it under `static/css/`.)

4) Visit pages with `?devcss=1` to review. As items feel stable, promote rules from
   `dev-overrides.css` into `stitch.theme.css`, then delete them from the override.

Pro tips
- No `!important` spam. If a Tailwind utility wins, prefer a slightly more specific selector under `body.dark-app-shell`.
- Shared bits (stat cards, pills, table headers) live in the theme. Page tricks live temporarily in the overrides file.
