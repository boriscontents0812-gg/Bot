const fs = require('fs');

const api = JSON.parse(fs.readFileSync('openapi.json', 'utf8'));
const lines = Object.keys(api.paths).map(p => {
  const methods = Object.keys(api.paths[p]).map(m => m.toUpperCase()).join(', ');
  return `${methods.padEnd(10)} ${p}`;
});
fs.writeFileSync('endpoints.txt', lines.join('\n'));
console.log('Saved endpoints.txt, count:', lines.length);
console.log(lines.join('\n'));
