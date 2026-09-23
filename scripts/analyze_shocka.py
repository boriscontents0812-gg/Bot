import re

with open('shocka_0.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Search for :root or color variables
root_vars = re.findall(r'(--[\w-]+)\s*:\s*([^;]+);', css)
print("CSS Variables count:", len(root_vars))
for var, val in root_vars[:50]:
    print(f"  {var}: {val}")

# Search for font-family
fonts = re.findall(r'font-family\s*:\s*([^;]+);', css)
print("\nUnique fonts:", list(set(fonts))[:10])

# Search for background colors / colors in shocka.html
with open('shocka.html', 'r', encoding='utf-8') as f:
    html = f.read()

classes = set(re.findall(r'class="([^"]+)"', html))
print("\nSample Tailwind classes in shocka.html:")
sample_classes = []
for c in classes:
    sample_classes.extend(c.split())
print("Unique class tokens:", len(set(sample_classes)))

# Check colors used in tailwind (bg-*, text-*, border-*)
bg_classes = set(c for c in sample_classes if c.startswith('bg-'))
text_classes = set(c for c in sample_classes if c.startswith('text-'))
border_classes = set(c for c in sample_classes if c.startswith('border-'))

print("\nBackground classes:", sorted(list(bg_classes))[:30])
print("\nText classes:", sorted(list(text_classes))[:30])
print("\nBorder classes:", sorted(list(border_classes))[:30])
