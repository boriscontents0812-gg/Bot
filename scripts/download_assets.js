const fs = require('fs');
const path = require('path');

const assetsToDownload = [
  '/assets/favicon.png',
  '/assets/og_preview.png',
  '/assets/phone_preview.png',
  '/assets/phone_preview2.png',
  '/assets/phone_preview3.jpg',
  '/assets/demo/demo1.mp4',
  '/assets/demo/demo2.mp4',
  '/assets/demo/demo3.mp4',
  '/assets/demo/demo4.mp4'
];

async function downloadAll() {
  for (const relPath of assetsToDownload) {
    const url = 'https://botyk.app' + relPath;
    const dest = path.join(__dirname, relPath.replace(/\//g, path.sep));
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    
    console.log(`Downloading ${url} -> ${dest}`);
    try {
      const res = await fetch(url);
      if (!res.ok) {
        console.error(`Failed ${url}: ${res.status}`);
        continue;
      }
      const buffer = Buffer.from(await res.arrayBuffer());
      fs.writeFileSync(dest, buffer);
      console.log(`Saved ${dest} (${buffer.length} bytes)`);
    } catch (e) {
      console.error(`Error downloading ${url}:`, e.message);
    }
  }
}

downloadAll();
