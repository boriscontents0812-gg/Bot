with open('shocka_0.css', 'r', encoding='utf-8') as f:
    css = f.read()

import re
matches = re.findall(r'(--(?:page|surface|card|main|muted|faint|accent|border)[a-zA-Z0-9_-]*)\s*:\s*([^;]+);', css)
print("Color tokens found:")
for k, v in matches:
    print(f"  {k}: {v}")

# Also look for theme blocks or color definitions
themes = re.findall(r'(\[data-theme=[^\]]+\]|\.dark|:root)[^{]*\{([^}]+)\}', css)
print(f"\nTheme blocks count: {len(themes)}")
for sel, rules in themes:
    if any(x in rules for x in ['--page', '--surface', '--accent', '--bg', '#', 'rgb', 'hsl']):
        print(f"\nSelector: {sel.strip()}")
        for line in rules.split(';'):
            if any(x in line for x in ['page', 'surface', 'card', 'main', 'muted', 'faint', 'accent', 'border', 'color', 'background']):
                print(f"    {line.strip()}")
