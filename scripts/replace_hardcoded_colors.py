import re

with open('templates/landing.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace hardcoded color references
replacements = [
    # dark backgrounds
    ('rgba(8,10,6,0.85)', 'rgba(24,23,22,0.85)'),
    ('rgba(8,10,6,', 'rgba(24,23,22,'),
    ('#080a06', '#181716'),
    ('#0d2010', '#201f1e'),
    ('#0f2e15', '#242220'),
    
    # neon greens to shocka rose/pink #ff4088
    ('#22ff5a', '#ff4088'),
    ('rgba(34,255,90,0.14)', 'rgba(244,244,242,0.09)'),
    ('rgba(34,255,90,0.12)', 'rgba(255,64,136,0.12)'),
    ('rgba(34,255,90,0.35)', 'rgba(255,64,136,0.35)'),
    ('rgba(34,255,90,0.22)', 'rgba(255,64,136,0.22)'),
    ('rgba(34,255,90,0.45)', 'rgba(255,64,136,0.45)'),
    ('rgba(34,255,90,0.07)', 'rgba(255,64,136,0.07)'),
    ('rgba(34,255,90,0.10)', 'rgba(255,64,136,0.10)'),
    ('rgba(34,255,90,0.25)', 'rgba(255,64,136,0.25)'),
    ('rgba(34,255,90,0.02)', 'rgba(255,64,136,0.02)'),
    ('rgba(34,255,90,0.3)', 'rgba(255,64,136,0.3)'),
    ('rgba(34,255,90,0.4)', 'rgba(255,64,136,0.4)'),
    ('rgba(34,255,90,0.9)', 'rgba(255,64,136,0.9)'),
    ('rgba(34,255,90,', 'rgba(255,64,136,'),

    # orange/amber to shocka peach #ff8a5c
    ('rgba(255,165,0,0.12)', 'rgba(255,138,92,0.12)'),
    ('rgba(255,165,0,0.3)', 'rgba(255,138,92,0.3)'),
    ('#ffa500', '#ff8a5c'),
    ('#ffb733', '#ff8a5c'),
    ('#ff8c00', '#ff8a5c'),
    ('rgba(255,140,0,', 'rgba(255,138,92,'),
    ('rgba(255,120,30,', 'rgba(255,118,77,'),
    ('#ff781e', '#ff764d'),
    ('#ff9a4d', '#ff8a5c'),
]

for old, new in replacements:
    content = content.replace(old, new)

with open('templates/landing.html', 'w', encoding='utf-8') as f:
    f.write(content)

with open('landing.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Replaced all hardcoded color instances with shocka palette in templates/landing.html and landing.html")
