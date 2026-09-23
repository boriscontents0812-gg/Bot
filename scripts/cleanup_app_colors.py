import re

with open('templates/app.html', 'r', encoding='utf-8') as f:
    c = f.read()

replacements = [
    ('.dark .segmented { background: oklch(0.26 0.01 260); }', '.dark .segmented { background: #201f1e; border: 1px solid #f4f4f217; }'),
    ('.dark .segmented button.active { background: oklch(0.32 0.01 260); box-shadow: 0 1px 2px rgba(0,0,0,.3); }', '.dark .segmented button.active { background: #242220; color: #ff4088; box-shadow: 0 1px 2px rgba(0,0,0,.4); }'),
    ('.dark .ios-switch { background: oklch(0.35 0.01 260); }', '.dark .ios-switch { background: #2a2826; }'),
    ('.dark header { background: oklch(0.14 0.01 260 / 85%); }', '.dark header { background: rgba(24, 23, 22, 0.85); border-bottom: 1px solid #f4f4f217; }'),
    ('color-mix(in oklch, var(--ring) 15%, transparent)', 'rgba(255, 64, 136, 0.18)'),
    ('color-mix(in oklch, var(--ring) 8%, transparent)', 'rgba(255, 64, 136, 0.08)'),
    ('color-mix(in oklch, var(--ring) 20%, transparent)', 'rgba(255, 64, 136, 0.2)'),
    ('color-mix(in oklch, var(--primary) 30%, transparent)', 'rgba(255, 64, 136, 0.3)'),
    ('color-mix(in oklch, var(--primary) 18%, transparent)', 'rgba(255, 64, 136, 0.22)'),
    ('color-mix(in oklch, var(--primary) 5%, transparent)', 'rgba(255, 64, 136, 0.08)'),
    ('color-mix(in oklch, var(--warning) 15%, transparent)', 'rgba(255, 138, 92, 0.15)'),
    ('color-mix(in oklch, var(--warning) 30%, transparent)', 'rgba(255, 138, 92, 0.3)'),
    ('color-mix(in oklch, var(--destructive) 20%, transparent)', 'rgba(239, 68, 68, 0.2)'),
    ('color-mix(in oklch, var(--muted) 50%, transparent)', 'rgba(32, 31, 30, 0.5)'),
    ('color-mix(in oklch, var(--muted) 60%, transparent)', 'rgba(32, 31, 30, 0.6)'),
    ('color-mix(in oklch,var(--muted) 60%,transparent)', 'rgba(32, 31, 30, 0.6)'),
    ('color-mix(in oklch, var(--background) 75%, transparent)', 'rgba(24, 23, 22, 0.75)'),
    ('linear-gradient(135deg, var(--primary), oklch(0.55 0.22 268))', 'linear-gradient(135deg, #ff4088, #ff8a5c)'),
    ('stroke="oklch(0.75 0.15 85)"', 'stroke="#ff8a5c"'),
    ('color:oklch(0.6 0.1 140)', 'color:#10b981'),
    ('color:oklch(0.6 0.2 25)', 'color:#ef4444'),
    ("'oklch(0.72 0.17 150)'", "'#10b981'"),
    ("'oklch(0.75 0.18 75)'", "'#ff8a5c'"),
    ("'oklch(0.62 0.22 25)'", "'#ef4444'"),
    ("'oklch(0.6 0.2 25)'", "'#ef4444'"),
    ("'oklch(0.6 0.1 140)'", "'#10b981'"),
]

for old, new in replacements:
    c = c.replace(old, new)

with open('templates/app.html', 'w', encoding='utf-8') as f:
    f.write(c)
with open('app.html', 'w', encoding='utf-8') as f:
    f.write(c)

print("Updated templates/app.html and app.html cleanly")
