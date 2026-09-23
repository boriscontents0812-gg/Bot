const fs = require('fs');
const api = JSON.parse(fs.readFileSync('openapi.json', 'utf8'));

let out = '';
for (const [path, methods] of Object.entries(api.paths)) {
  for (const [method, op] of Object.entries(methods)) {
    out += `\n========================================\n`;
    out += `${method.toUpperCase()} ${path}\n`;
    out += `Summary: ${op.summary || ''}\n`;
    out += `OperationId: ${op.operationId || ''}\n`;
    if (op.parameters && op.parameters.length) {
      out += `Parameters:\n` + JSON.stringify(op.parameters, null, 2) + '\n';
    }
    if (op.requestBody) {
      out += `RequestBody:\n` + JSON.stringify(op.requestBody, null, 2) + '\n';
    }
    out += `Responses:\n` + JSON.stringify(op.responses, null, 2) + '\n';
  }
}
fs.writeFileSync('all_endpoints_details.txt', out);
console.log('Saved all_endpoints_details.txt, length:', out.length);
