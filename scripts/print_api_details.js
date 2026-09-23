const fs = require('fs');
const api = JSON.parse(fs.readFileSync('openapi.json', 'utf8'));

let out = `Total paths: ${Object.keys(api.paths).length}\n`;

for (const [path, methods] of Object.entries(api.paths)) {
  out += `\n=== PATH: ${path} ===\n`;
  for (const [m, op] of Object.entries(methods)) {
    out += `  [${m.toUpperCase()}] ${op.operationId || ''}\n`;
    if (op.parameters) {
      out += `    Params: ` + op.parameters.map(p => `${p.name} (${p.in}, ${p.required ? 'req' : 'opt'})`).join(', ') + '\n';
    }
    if (op.requestBody) {
      const content = op.requestBody.content;
      out += `    RequestBody: ` + Object.keys(content).join(', ') + '\n';
      for (const ct of Object.keys(content)) {
        if (content[ct].schema) {
          out += `      Schema: ` + JSON.stringify(content[ct].schema) + '\n';
        }
      }
    }
    if (op.responses) {
      out += `    Responses: ` + Object.keys(op.responses).join(', ') + '\n';
    }
  }
}

fs.writeFileSync('api_detailed.txt', out, 'utf8');
console.log('Written utf8 api_detailed.txt');
