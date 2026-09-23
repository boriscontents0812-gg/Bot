const fs = require('fs');

const api = JSON.parse(fs.readFileSync('openapi.json', 'utf8'));

const summary = {};

for (const [path, methods] of Object.entries(api.paths)) {
  summary[path] = {};
  for (const [method, op] of Object.entries(methods)) {
    summary[path][method] = {
      operationId: op.operationId,
      summary: op.summary,
      parameters: op.parameters?.map(p => ({ name: p.name, in: p.in, required: p.required, type: p.schema?.type })),
      requestBody: op.requestBody?.content ? Object.keys(op.requestBody.content) : undefined,
      responses: Object.keys(op.responses)
    };
  }
}

fs.writeFileSync('api_summary.json', JSON.stringify(summary, null, 2));
if (api.components && api.components.schemas) {
  fs.writeFileSync('api_schemas.json', JSON.stringify(api.components.schemas, null, 2));
}

console.log('Schemas count:', Object.keys(api.components?.schemas || {}).length);
console.log('Schemas:', Object.keys(api.components?.schemas || {}));
