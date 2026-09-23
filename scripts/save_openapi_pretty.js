const fs = require('fs');
const api = JSON.parse(fs.readFileSync('openapi.json', 'utf8'));

fs.writeFileSync('openapi_pretty.json', JSON.stringify(api, null, 2));
console.log('Saved openapi_pretty.json');
