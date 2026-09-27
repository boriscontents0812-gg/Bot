import os
import sys
import json
import asyncio
import wave

# Ensure site-packages
base_dir = os.path.dirname(os.path.abspath(__file__))
venv_site = os.path.join(base_dir, ".venv", "Lib", "site-packages")
if os.path.exists(venv_site) and venv_site not in sys.path:
    sys.path.insert(0, venv_site)

import config
import audio_generator
from server import app
from fastapi.testclient import TestClient

client = TestClient(app)

def run_tests():
    print("--- 1. Testing GET /api/eleven_voices ---")
    # Login first
    login_resp = client.post("/login", json={"code": config.DEFAULT_ACCESS_KEY})
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    cookie = login_resp.cookies.get(config.SESSION_COOKIE_NAME)

    res = client.get("/api/eleven_voices", cookies={config.SESSION_COOKIE_NAME: cookie})
    assert res.status_code == 200, f"eleven_voices failed: {res.text}"
    voices = res.json().get("voices", [])
    print(f"Total voices returned: {len(voices)}")
    assert len(voices) >= 10, "Voices list too small"
    v_names = [v["name"] for v in voices]
    print(f"Sample voices: {v_names[:5]}")

    print("\n--- 2. Testing POST /api/generate_audio with mystique headers and breaks ---")
    script = (
        "mystique\n"
        "1: Natasha > Hey Adam! Did you see the new update?\n"
        "2: Adam: Yeah Natasha, it looks amazing!\n"
        "mystique\n"
        "1: Natasha > Did you hear about that?\n"
        "2: Adam > Yes == Absolutely, it generates the full transcript in stereo!\n"
        "mystique"
    )
    voice_map = {
        "Natasha": "EXAVITQu4vr4xnSDxMaL", # Sarah / Natasha
        "Adam": "pNInz6obpgDQGcFmaJgB"     # Adam
    }

    payload = {
        "script": script,
        "voice_map": voice_map,
        "settings": {
            "voice_model": "eleven_multilingual_v2",
            "voice_stability": 0.35,
            "voice_similarity": 0.75,
            "voice_audio_speed": 1.05
        }
    }

    res_audio = client.post("/api/generate_audio", json=payload, cookies={config.SESSION_COOKIE_NAME: cookie})
    assert res_audio.status_code == 200, f"generate_audio failed: {res_audio.text}"
    audio_data = res_audio.json()
    print("Generate audio response status:", res_audio.status_code)
    clips = audio_data.get("clips", [])
    total_ms = audio_data.get("total_ms", 0)
    print(f"Generated {len(clips)} clips with total duration: {total_ms / 1000.0:.2f}s")
    assert len(clips) == 4, f"Expected exactly 4 conversation clips (mystique must be ignored), got {len(clips)}"
    assert not any("mystique" in c["text"].lower() for c in clips), "mystique was erroneously included in audio clips!"
    assert total_ms > 5000, f"Expected full duration > 5s, got {total_ms}ms"

    for i, c in enumerate(clips):
        print(f" - Clip {i+1} ({c['voice']}): {c['duration_ms']}ms -> {c['text'][:40]}... (audio: {c.get('audio_text', '')[:30]})")

    print("\n--- 3. Verifying audio_full.wav stereo file integrity ---")
    user_audio_dir = os.path.join(config.DATA_DIR, "audio", config.DEFAULT_ACCESS_KEY)
    full_wav = os.path.join(user_audio_dir, "audio_full.wav")
    assert os.path.exists(full_wav), "audio_full.wav does not exist!"
    with wave.open(full_wav, "rb") as wf:
        nframes = wf.getnframes()
        framerate = wf.getframerate()
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        wav_dur = nframes / framerate
        print(f"audio_full.wav: {wav_dur:.2f}s, {channels}ch (STEREO), {framerate}Hz, {sampwidth*8}-bit PCM")
        assert channels == 2, f"Expected 2 channels (Stereo), got {channels}"
        assert wav_dur > 8.0, f"audio_full.wav duration too short: {wav_dur}s"

    print("\n--- 4. Testing GET /api/audio_full endpoint ---")
    full_resp = client.get("/api/audio_full", cookies={config.SESSION_COOKIE_NAME: cookie})
    assert full_resp.status_code == 200, f"GET /api/audio_full failed: {full_resp.status_code}"
    print(f"GET /api/audio_full returned: {len(full_resp.content)} bytes, Content-Type: {full_resp.headers.get('content-type')}")
    assert len(full_resp.content) > 50000, "audio_full content too small"

    print("\nALL STEREO AUDIO & VOICE SCRIPT TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
