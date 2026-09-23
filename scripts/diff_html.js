const fs = require('fs');
const app = fs.readFileSync('app.html', 'utf8');
const demo = fs.readFileSync('app_demo.html', 'utf8');

const appLines = app.split('\n');
const demoLines = demo.split('\n');

console.log('App lines:', appLines.length, 'Demo lines:', demoLines.length);

let diffCount = 0;
for (let i = 0; i < Math.max(appLines.length, demoLines.length); i++) {
  if (appLines[i] !== demoLines[i]) {
    diffCount++;
    console.log(`Diff at line ${i+1}:`);
    console.log(`  APP:  ${appLines[i]}`);
    console.log(`  DEMO: ${demoLines[i]}`);
  }
}
console.log('Total diff lines:', diffCount);
