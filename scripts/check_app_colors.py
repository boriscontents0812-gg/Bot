with open('templates/app.html', 'r', encoding='utf-8') as f:
    content = f.read()

import re
oklch_matches = re.findall(r'oklch\([^)]+\)', content)
print("oklch occurrences in templates/app.html:", len(oklch_matches))
print("Sample oklch:", list(set(oklch_matches))[:10])

# Also check for hardcoded hex colors
hex_matches = re.findall(r'#[0-9a-fA-F]{3,8}', content)
print("Unique hex colors in app.html:", set(hex_matches))
