const fs = require('fs');
const html = fs.readFileSync('app.html', 'utf8');

const matches = [...html.matchAll(/<select[^>]*id=['"]([^'"]*voice[^'"]*)['"][^>]*>([\s\S]*?)<\/select>/gi)];
console.log('Voice selects count:', matches.length);
matches.forEach(m => {
  console.log('Select ID:', m[1]);
  console.log('Options:', [...m[2].matchAll(/<option[^>]*value=['"]([^'"]*)['"][^>]*>([^<]*)<\/option>/gi)].map(o => `${o[1]} -> ${o[2]}`));
});

// Also search for voice lists or dictionaries in scripts
const jsMatches = [...html.matchAll(/(voices|VOICES|voice_list|VOICE_LIST|ELEVEN_VOICES)\s*[:=]\s*(\[[^\]]+\]|\{[^\}]+\})/gi)];
jsMatches.forEach(m => console.log('JS voice match:', m[0].slice(0, 300)));

// Also search for mentions of Harry, Natasha, etc.
const harryMatches = [...html.matchAll(/Harry/gi)];
console.log('Harry count:', harryMatches.length);
if (harryMatches.length) {
  const idx = html.indexOf('Harry');
  console.log('Context around Harry:\n', html.slice(Math.max(0, idx - 150), idx + 250));
}
