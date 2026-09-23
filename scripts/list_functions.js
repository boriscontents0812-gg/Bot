const fs = require('fs');
const code = fs.readFileSync('app_script_0.js', 'utf8');

const lines = code.split('\n');
const functionList = [];
for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  const m = line.match(/^\s*(async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\(([^)]*)\)/);
  if (m) {
    functionList.push({ line: i + 1, name: m[2], params: m[3], async: !!m[1] });
  }
  const m2 = line.match(/^\s*(const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(async\s+)?\(([^)]*)\)\s*=>/);
  if (m2) {
    functionList.push({ line: i + 1, name: m2[2], params: m2[4], async: !!m2[3] });
  }
}

console.log('Total functions found:', functionList.length);
fs.writeFileSync('functions_list.json', JSON.stringify(functionList, null, 2));
console.log(functionList.map(f => `${f.line}: ${f.async ? 'async ' : ''}${f.name}(${f.params})`).join('\n'));
