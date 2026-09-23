const fs = require('fs');

const cookie = 'imsg_session=6C6W-K6LD-JRVV-QGTM';

async function probe() {
  const endpoints = [
    '/me',
    '/api/voice_settings',
    '/api/eleven_quota',
    '/api/eleven_profiles',
    '/api/assets/music',
    '/api/assets/gameplay',
    '/api/projects',
    '/api/contact_photos',
    '/api/audio_progress',
    '/api/video_progress',
    '/api/last_video',
    '/api/nonexistent_test_route_12345'
  ];

  for (const ep of endpoints) {
    try {
      const res = await fetch('https://botyk.app' + ep, {
        headers: { 'Cookie': cookie }
      });
      const ct = res.headers.get('content-type') || '';
      let body;
      if (ct.includes('json')) {
        body = await res.json();
      } else {
        body = (await res.text()).slice(0, 200);
      }
      console.log(`=== ${ep} [${res.status}] ===`);
      console.log('Content-Type:', ct);
      console.log('Body:', JSON.stringify(body, null, 2));
    } catch (e) {
      console.log(`=== ${ep} ERROR ===`, e.message);
    }
  }
}

probe();
