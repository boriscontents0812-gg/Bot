const fs = require('fs');

const appHtml = fs.readFileSync('app.html', 'utf8');
const landingHtml = fs.readFileSync('landing.html', 'utf8');

function extractUrls(html) {
  const urls = new Set();
  const patterns = [
    /href=["']([^"']+)["']/g,
    /src=["']([^"']+)["']/g,
    /url\(["']?([^"')]+)["']?\)/g,
    /["'](\/assets\/[^"']+)["']/g,
    /["'](\/static\/[^"']+)["']/g,
  ];
  for (const re of patterns) {
    let match;
    while ((match = re.exec(html)) !== null) {
      urls.add(match[1]);
    }
  }
  return [...urls];
}

console.log('App URLs:', extractUrls(appHtml));
console.log('Landing URLs:', extractUrls(landingHtml));
