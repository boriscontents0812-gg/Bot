import os
import re

def update_landing():
    path = os.path.join('templates', 'landing.html')
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. Update font link to Plus Jakarta Sans & IBM Plex Mono
    old_font = '<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Cabinet+Grotesk:wght@400;500;700;800;900&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet"/>'
    new_font = '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:ital,wght@0,400;0,500;0,600;1,400&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet"/>'
    if old_font in html:
        html = html.replace(old_font, new_font)
    else:
        html = re.sub(r'<link[^>]*fonts\.googleapis\.com/css2[^>]*>', new_font, html)

    # 2. Update :root variables to shocka.site
    old_root_match = re.search(r':root\s*\{[^}]+\}', html)
    shocka_root = """:root{
  --black:#181716;
  --green:#201f1e;
  --green-mid:#242220;
  --neon:#ff4088;
  --neon-dim:rgba(255,64,136,0.12);
  --neon-glow:rgba(255,64,136,0.32);
  --white:#f4f4f2;
  --gray:rgba(244,244,242,0.62);
  --border:rgba(244,244,242,0.09);
  --accent-peach:#ff8a5c;
  --accent-emerald:#10b981;
  --font-display:'Plus Jakarta Sans',sans-serif;
  --font-body:'Plus Jakarta Sans',sans-serif;
  --font-mono:'IBM Plex Mono',monospace;
}"""
    if old_root_match:
        html = html[:old_root_match.start()] + shocka_root + html[old_root_match.end():]

    # 3. Add shocka styling refinements to style section
    shocka_custom_css = """
/* ── SHOCKA.SITE ENHANCEMENTS ── */
.ticker{
  background:var(--green);
  color:var(--white);
  border-bottom:1px solid var(--border);
}
.ticker-sep{color:var(--neon);opacity:.9;}
.nav-cta{
  background:linear-gradient(135deg, var(--neon), var(--accent-peach));
  color:#fff;
  border-radius:10px;
  box-shadow:0 0 20px rgba(255,64,136,0.25);
}
.nav-cta:hover{
  background:linear-gradient(135deg, #ff5497, #ff9b73);
  box-shadow:0 0 30px rgba(255,64,136,0.45);
}
.nav-logo{
  font-weight:800;
  letter-spacing:-0.02em;
  color:var(--white);
}
.hero-title .line-green{
  background:linear-gradient(135deg, #ffffff 30%, #ff8a5c 100%);
  -webkit-background-clip:text;
  -webkit-text-fill-color:transparent;
}
.hero-title .line-outline{
  -webkit-text-stroke:1.5px rgba(255,64,136,0.6);
  color:transparent;
}
.btn-primary{
  background:linear-gradient(135deg, var(--neon), var(--accent-peach));
  color:#fff;
  border-radius:12px;
  box-shadow:0 0 32px rgba(255,64,136,0.3);
}
.btn-primary:hover{
  background:linear-gradient(135deg, #ff5497, #ff9b73);
  box-shadow:0 0 44px rgba(255,64,136,0.5);
}
.btn-secondary{
  border:1px solid var(--border);
  background:rgba(36,34,32,0.6);
  border-radius:12px;
}
.btn-secondary:hover{border-color:var(--neon);color:var(--neon);}
.btn-try-free{
  background:linear-gradient(135deg, #ff764d, #ff4088);
  border-color:transparent;
}
.plan-card.popular{
  border-color:rgba(255,64,136,0.45);
  box-shadow:0 0 40px rgba(255,64,136,0.16);
}
.popular-badge{
  background:linear-gradient(135deg, var(--neon), var(--accent-peach));
  color:#fff;
  border-radius:999px;
}
.plan-btn.active{
  background:linear-gradient(135deg, var(--neon), var(--accent-peach));
  color:#fff;
  border:none;
  box-shadow:0 0 24px rgba(255,64,136,0.3);
}
.key-btn{
  background:linear-gradient(135deg, var(--neon), var(--accent-peach));
  color:#fff;
  box-shadow:0 0 24px rgba(255,64,136,0.25);
  border-radius:10px;
}
.key-input-wrap:focus-within{
  border-color:var(--neon);
  box-shadow:0 0 0 3px rgba(255,64,136,0.18);
}
.popup-box{
  background:var(--green-mid);
  border:1px solid rgba(255,64,136,0.3);
  box-shadow:0 0 60px rgba(255,64,136,0.16), 0 24px 64px rgba(0,0,0,0.8);
  border-radius:24px;
}
.popup-btn{
  background:linear-gradient(135deg, var(--neon), var(--accent-peach));
  color:#fff;
  box-shadow:0 0 32px rgba(255,64,136,0.35);
  border-radius:12px;
}
.popup-green{color:var(--neon);}
.phone-glow{
  background:radial-gradient(ellipse,rgba(255,64,136,0.16) 0%,rgba(255,138,92,0.06) 40%,transparent 70%);
}
.hero::after{
  background:radial-gradient(circle,rgba(255,64,136,0.12) 0%,rgba(255,138,92,0.05) 50%,transparent 70%);
}
"""
    html = html.replace('</style>', shocka_custom_css + '\n</style>')

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    # Also write root landing.html
    with open('landing.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Updated templates/landing.html and landing.html with shocka.site theme")

def update_app():
    path = os.path.join('templates', 'app.html')
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. Add Google Font link into <head>
    new_font = '<link rel="preconnect" href="https://fonts.googleapis.com"/><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/><link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:ital,wght@0,400;0,500;0,600;1,400&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet"/>'
    html = html.replace('<head>', '<head>\n' + new_font)

    # 2. Replace root and dark CSS variables
    shocka_app_vars = """
  :root {
    --font-sans: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
    --font-mono: "IBM Plex Mono", ui-monospace, monospace;
    --radius: 0.875rem;
    --background: #181716;
    --foreground: #f4f4f2;
    --surface: #201f1e;
    --card: #242220;
    --primary: #ff4088;
    --primary-fg: #ffffff;
    --secondary: #2a2826;
    --muted: #201f1e;
    --muted-fg: #f4f4f29e;
    --border: #f4f4f217;
    --input: #201f1e;
    --ring: #ff4088;
    --success: #10b981;
    --destructive: #ef4444;
    --warning: #ff8a5c;
    --accent: #ff4088;
    --accent-peach: #ff8a5c;
    --accent-emerald: #10b981;
    --imessage-blue: #007aff;
    --imessage-gray: #242220;
  }

  .dark {
    --background: #181716;
    --foreground: #f4f4f2;
    --surface: #201f1e;
    --card: #242220;
    --primary: #ff4088;
    --primary-fg: #ffffff;
    --secondary: #2a2826;
    --muted: #201f1e;
    --muted-fg: #f4f4f29e;
    --border: #f4f4f217;
    --input: #201f1e;
    --ring: #ff4088;
  }

  /* Shocka.site theme refinements for studio */
  .btn-primary {
    background: linear-gradient(135deg, #ff4088 0%, #ff8a5c 100%) !important;
    color: #fff !important;
    box-shadow: 0 4px 16px rgba(255, 64, 136, 0.3) !important;
    border-radius: 12px !important;
  }
  .btn-primary:hover {
    opacity: .95 !important;
    box-shadow: 0 4px 22px rgba(255, 64, 136, 0.45) !important;
  }
  .segmented {
    background: #201f1e !important;
    border: 1px solid #f4f4f217 !important;
  }
  .segmented button.active {
    background: #242220 !important;
    color: #ff4088 !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.4) !important;
  }
  .tab-btn.active {
    color: #ff4088 !important;
  }
  .tab-btn.active::after {
    background: #ff4088 !important;
  }
  input[type="range"] {
    accent-color: #ff4088 !important;
  }
  .ios-switch.on {
    background: #10b981 !important;
  }
  header {
    background: rgba(24, 23, 22, 0.85) !important;
    backdrop-filter: blur(16px) !important;
    border-bottom: 1px solid #f4f4f217 !important;
  }
"""
    # Replace the existing :root and .dark blocks
    html = re.sub(r':root\s*\{[^}]+\}\s*\.dark\s*\{[^}]+\}', shocka_app_vars, html)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    # Also write root app.html
    with open('app.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Updated templates/app.html and app.html with shocka.site theme")

def update_admin():
    path = os.path.join('templates', 'admin.html')
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()

    new_font = '<link rel="preconnect" href="https://fonts.googleapis.com"/><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/><link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:ital,wght@0,400;0,500;0,600;1,400&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet"/>'
    html = html.replace('<head>', '<head>\n' + new_font)

    shocka_admin_vars = """
  :root {
    --background: #181716;
    --foreground: #f4f4f2;
    --card: #242220;
    --primary: #ff4088;
    --primary-fg: #ffffff;
    --muted-fg: #f4f4f29e;
    --border: #f4f4f217;
    --input: #201f1e;
    --destructive: #ef4444;
    --font-sans: "Plus Jakarta Sans", sans-serif;
  }
  .btn-primary {
    background: linear-gradient(135deg, #ff4088, #ff8a5c) !important;
    box-shadow: 0 4px 16px rgba(255,64,136,0.3) !important;
  }
"""
    html = re.sub(r':root\s*\{[^}]+\}', shocka_admin_vars, html)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    with open('admin.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Updated templates/admin.html and admin.html with shocka.site theme")

if __name__ == '__main__':
    update_landing()
    update_app()
    update_admin()
