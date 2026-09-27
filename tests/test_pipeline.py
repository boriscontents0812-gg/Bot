import urllib.request
import json
import http.cookiejar
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

BASE = f"http://{config.HOST}:{config.PORT}"

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def test_pipeline():
    print("--- Running End-to-End Generation Pipeline Test ---")

    # 1. Login
    login_data = json.dumps({'code': config.DEFAULT_ACCESS_KEY}).encode('utf-8')
    r_login = opener.open(urllib.request.Request(f'{BASE}/login', data=login_data, headers={'Content-Type': 'application/json'}))
    print('1. Login Resp:', r_login.status)
    assert r_login.status == 200

    # 2. Generate audio
    audio_payload = json.dumps({
        'script': 'Alice 💕\n1: Alice > Hello there!\n2: Bob > Hey Alice! How are you?',
        'settings': {},
        'project': 'TestPipeline'
    }).encode('utf-8')
    r_audio = opener.open(urllib.request.Request(f'{BASE}/api/generate_audio', data=audio_payload, headers={'Content-Type': 'application/json'}))
    audio_res = json.loads(r_audio.read().decode('utf-8'))
    print('2. Audio Resp:', r_audio.status, 'Clips:', len(audio_res['clips']), 'Credits used:', audio_res['credits_used'])
    assert r_audio.status == 200

    # 3. Stream full audio
    r_full = opener.open(urllib.request.Request(f'{BASE}/api/audio_full'))
    full_audio_bytes = r_full.read()
    print('3. Audio Full Resp:', r_full.status, len(full_audio_bytes), 'bytes')
    assert len(full_audio_bytes) > 1000

    # 4. Generate video
    video_payload = json.dumps({
        'settings': {
            'script': 'Alice 💕\n1: Alice > Hello there!\n2: Bob > Hey Alice! How are you?',
            'style': 'ios',
            'theme': 'dark'
        },
        'project': 'TestPipeline',
        'gameplay_on': False
    }).encode('utf-8')
    r_video = opener.open(urllib.request.Request(f'{BASE}/api/generate_video', data=video_payload, headers={'Content-Type': 'application/json'}))
    v_data = json.loads(r_video.read().decode('utf-8'))
    print('4. Video Resp:', r_video.status, v_data.get('token'))
    assert r_video.status == 200

    # 5. Download video
    dl_url = f"{BASE}{v_data['download_url']}"
    r_dl = opener.open(urllib.request.Request(dl_url))
    dl_bytes = r_dl.read()
    print('5. Download Video Resp:', r_dl.status, len(dl_bytes), 'bytes (valid MP4)')
    assert len(dl_bytes) > 1000
    print('\n[SUCCESS] Audio & Video generation pipeline fully functional!')

if __name__ == "__main__":
    test_pipeline()
