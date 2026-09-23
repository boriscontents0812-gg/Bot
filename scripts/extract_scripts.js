const fs = require('fs');

const appHtml = fs.readFileSync('app.html', 'utf8');

const scriptRegex = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
let i = 0;
let match;
while ((match = scriptRegex.exec(appHtml)) !== null) {
  const attrs = match[1];
  const content = match[2];
  fs.writeFileSync(`app_script_${i}.js`, content);
  console.log(`Saved app_script_${i}.js (len: ${content.length})`);
  i++;
}
