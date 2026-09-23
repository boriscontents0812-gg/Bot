import os
import shutil

os.makedirs('templates', exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('data/music', exist_ok=True)
os.makedirs('data/gameplay', exist_ok=True)
os.makedirs('data/contact_photos', exist_ok=True)
os.makedirs('data/script_images', exist_ok=True)
os.makedirs('data/audio', exist_ok=True)
os.makedirs('data/videos', exist_ok=True)
os.makedirs('data/projects', exist_ok=True)

# Copy landing.html
shutil.copy('landing.html', 'templates/landing.html')
print("Copied templates/landing.html")

# Copy admin.html
shutil.copy('admin.html', 'templates/admin.html')
print("Copied templates/admin.html")

# Create templates/app.html with Jinja2 placeholders
with open('app.html', 'r', encoding='utf-8') as f:
    app_content = f.read()

# Replace IS_DEMO and CROSSFADE_ENABLED with Jinja2 expressions
app_content = app_content.replace(
    'const IS_DEMO = false;',
    'const IS_DEMO = {{ "true" if is_demo else "false" }};'
)
app_content = app_content.replace(
    'const CROSSFADE_ENABLED = false;',
    'const CROSSFADE_ENABLED = {{ "true" if crossfade_enabled else "false" }};'
)

with open('templates/app.html', 'w', encoding='utf-8') as f:
    f.write(app_content)
print("Created templates/app.html with Jinja2 flags")
