const fs = require('fs');

const cookie = 'imsg_session=6C6W-K6LD-JRVV-QGTM';

async function loadAllProjects() {
  const list = ['23', 'w', 'Promo', 'Goated', '1'];
  for (const name of list) {
    const res = await fetch(`https://botyk.app/api/projects/${encodeURIComponent(name)}/load`, {
      headers: { 'Cookie': cookie }
    });
    if (res.ok) {
      const data = await res.json();
      fs.writeFileSync(`project_${name}.json`, JSON.stringify(data, null, 2));
      console.log(`Saved project_${name}.json`);
    } else {
      console.log(`Failed ${name}: ${res.status}`);
    }
  }
}
loadAllProjects();
