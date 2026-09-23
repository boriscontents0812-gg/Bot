const fs = require('fs');

const appHtml = fs.readFileSync('app.html', 'utf8');

// Find all fetch/endpoints
const fetches = [...appHtml.matchAll(/fetch\s*\(\s*['"`]([^'"`]+)['"`]/g)].map(m => m[1]);
console.log('API endpoints fetched in app.html:');
console.log([...new Set(fetches)]);

// Find all src attributes
const srcs = [...appHtml.matchAll(/src\s*=\s*['"`]([^'"`]+)['"`]/g)].map(m => m[1]);
console.log('\nAll src attributes:');
console.log([...new Set(srcs)]);

// Find all href attributes
const hrefs = [...appHtml.matchAll(/href\s*=\s*['"`]([^'"`]+)['"`]/g)].map(m => m[1]);
console.log('\nAll href attributes:');
console.log([...new Set(hrefs)]);

// Check if there are external scripts
const scriptTags = [...appHtml.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)];
console.log('\nScript count:', scriptTags.length);
scriptTags.forEach((s, i) => {
  console.log(`Script ${i} attrs: "${s[1].trim()}" code length: ${s[2].length}`);
});

// Also check landing.html
const landingHtml = fs.readFileSync('landing.html', 'utf8');
const landingFetches = [...landingHtml.matchAll(/fetch\s*\(\s*['"`]([^'"`]+)['"`]/g)].map(m => m[1]);
console.log('\nLanding fetches:', [...new Set(landingFetches)]);

const landingSrcs = [...landingHtml.matchAll(/src\s*=\s*['"`]([^'"`]+)['"`]/g)].map(m => m[1]);
console.log('\nLanding srcs:', [...new Set(landingSrcs)]);
