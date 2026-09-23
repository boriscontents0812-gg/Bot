import urllib.request
import re
import json

req = urllib.request.Request('https://shocka.site', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode('utf-8')
    with open('shocka.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print('Saved shocka.html, len:', len(html))

# Extract style blocks and link stylesheets
css_links = re.findall(r'<link[^>]*rel=["\']stylesheet["\'][^>]*href=["\']([^"\']+)["\']', html)
print('CSS links:', css_links)

# Download any external CSS linked
for i, link in enumerate(css_links):
    url = link if link.startswith('http') else f"https://shocka.site{link}"
    try:
        req_css = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_css) as cresp:
            css_content = cresp.read().decode('utf-8')
            with open(f'shocka_{i}.css', 'w', encoding='utf-8') as f:
                f.write(css_content)
            print(f'Saved shocka_{i}.css, len:', len(css_content))
    except Exception as e:
        print(f"Error fetching {url}: {e}")
