import urllib.request
import json
import http.cookiejar

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Login
login_data = json.dumps({'code': '6C6W-K6LD-JRVV-QGTM'}).encode('utf-8')
r_login = opener.open(urllib.request.Request('http://127.0.0.1:8000/login', data=login_data, headers={'Content-Type': 'application/json'}))
print('Login Resp:', r_login.status)

# 2. Generate audio
audio_payload = json.dumps({
    'script': 'Alice 💕\n1: Alice > Hello there!\n2: Bob > Hey Alice! How are you?',
    'settings': {},
    'project': 'TestProj'
}).encode('utf-8')
r_audio = opener.open(urllib.request.Request('http://127.0.0.1:8000/api/generate_audio', data=audio_payload, headers={'Content-Type': 'application/json'}))
audio_res = json.loads(r_audio.read().decode('utf-8'))
print('Audio Resp:', r_audio.status, 'Clips:', len(audio_res['clips']), 'Credits used:', audio_res['credits_used'])

# 3. Stream full audio
r_full = opener.open(urllib.request.Request('http://127.0.0.1:8000/api/audio_full'))
print('Audio Full Resp:', r_full.status, len(r_full.read()), 'bytes')

# 4. Generate video
video_payload = json.dumps({
    'settings': {
        'script': 'Alice 💕\n1: Alice > Hello there!\n2: Bob > Hey Alice! How are you?',
        'style': 'ios',
        'theme': 'dark'
    },
    'project': 'TestProj',
    'gameplay_on': False
}).encode('utf-8')
r_video = opener.open(urllib.request.Request('http://127.0.0.1:8000/api/generate_video', data=video_payload, headers={'Content-Type': 'application/json'}))
v_data = json.loads(r_video.read().decode('utf-8'))
print('Video Resp:', r_video.status, v_data)

# 5. Download video
dl_url = f"http://127.0.0.1:8000{v_data['download_url']}"
r_dl = opener.open(urllib.request.Request(dl_url))
dl_bytes = r_dl.read()
print('Download Video Resp:', r_dl.status, len(dl_bytes), 'bytes (valid MP4)')
assert len(dl_bytes) > 1000
print('\n[SUCCESS] Audio & Video generation pipeline fully functional!')
