import os
import wave
import struct
import math
import httpx
import re

if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    AUDIO_DIR = "/tmp/data/audio"
else:
    AUDIO_DIR = os.path.join(os.path.dirname(__file__), 'data', 'audio')

try:
    os.makedirs(AUDIO_DIR, exist_ok=True)
except Exception:
    pass

def generate_beep_wav(filepath, duration_ms, freq=440.0, sample_rate=24000):
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    with wave.open(filepath, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        # Smooth attack and decay envelope
        for i in range(num_samples):
            t = float(i) / sample_rate
            env = 1.0
            attack = int(sample_rate * 0.05)
            decay = int(sample_rate * 0.05)
            if i < attack:
                env = float(i) / attack
            elif i > num_samples - decay:
                env = float(num_samples - i) / decay
            value = int(math.sin(2.0 * math.pi * freq * t) * 8000 * env)
            data = struct.pack('<h', value)
            wav_file.writeframesraw(data)

def concat_wav_files(wav_list, output_filepath):
    if not wav_list:
        return
    data = []
    params = None
    for w in wav_list:
        if not os.path.exists(w):
            continue
        with wave.open(w, 'rb') as f:
            if params is None:
                params = f.getparams()
            data.append(f.readframes(f.getnframes()))
    
    if params and data:
        with wave.open(output_filepath, 'wb') as f:
            f.setparams(params)
            for d in data:
                f.writeframes(d)

VOICE_MAP = {
    "roger": "CwhRBWXzGAHq8TQ4Fs17",
    "sarah": "EXAVITQu4vr4xnSDxMaL",
    "laura": "FGY2WhTYpPnrIDTdsKH5",
    "charlie": "IKne3meq5aSn9XLyUdCD",
    "george": "JBFqnCBsd6RMkjVDRZzb",
    "callum": "N2lVS1w4EtoT3dr4eOWO",
    "river": "SAz9YHcvj6GT2YYXdXww",
    "harry": "SOYHLrjzK2X1ezoPC6cr",
    "liam": "TX3LPaxmHKxFdv7VOQHJ",
    "alice": "Xb7hH8MSUJpSbSDYk0k2",
    "matilda": "XrExE9yKIg1WjnnlVkGX",
    "will": "bIHbv24MWmeRgasZH58o",
    "jessica": "r1KmysJdVYZjJCm4mL3b",
    "eric": "cjVigY5qzO86Huf0OWal",
    "bella": "hpp4J3VqNfWAUOO0d1Us",
    "chris": "iP95p4xoKVk53GoZ742B",
    "brian": "nPczCjzI2devNBz1zQrb",
    "daniel": "onwK4e9ZLuTAKqWW03F9",
    "lily": "pFZP5JQG7iQjIQuC4Bku",
    "adam": "pNInz6obpgDQGcFmaJgB",
    "bill": "pqHfZKP75CvOlQylNhV4",
    "natasha": "uxKr2vlA4hYgXZR1oPRT",
    "jimbo": "YLbQE9U7P1K6rBNJWNSv",
    "alex": "CwhRBWXzGAHq8TQ4Fs17",
    "nicole": "piTKgcLEGmPE4e6mEKli",
    "rachel": "21m00Tcm4TlvDq8ikWAM",
}

async def synthesize_clip(text, voice_name, eleven_key, model_id='eleven_multilingual_v2', stability=0.25, similarity=0.7, speed=1.0, side=1):
    import io
    if eleven_key and len(eleven_key) > 10:
        # Direct ElevenLabs API call (user's own API key, zero third-party credits)
        try:
            v_lower = str(voice_name or '').strip().lower()
            voice_id = VOICE_MAP.get(v_lower)
            if not voice_id:
                for k, vid in VOICE_MAP.items():
                    if k in v_lower:
                        voice_id = vid
                        break
            if not voice_id:
                # Default side 1 to female (Sarah), side 2 to male (Roger)
                voice_id = "EXAVITQu4vr4xnSDxMaL" if side == 1 else "CwhRBWXzGAHq8TQ4Fs17"

            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=pcm_24000"
            headers = {
                "xi-api-key": eleven_key,
                "Content-Type": "application/json"
            }
            payload = {
                "text": text,
                "model_id": model_id,
                "voice_settings": {
                    "stability": float(stability),
                    "similarity_boost": float(similarity),
                    "speed": float(speed)
                }
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    pcm_data = resp.content
                    dur_ms = max(400, int(len(pcm_data) / 48))
                    wav_buf = io.BytesIO()
                    with wave.open(wav_buf, 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(24000)
                        wf.writeframes(pcm_data)
                    return wav_buf.getvalue(), True, dur_ms
                else:
                    print(f"ElevenLabs TTS returned {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            print(f"ElevenLabs direct TTS notice: {e}, using local synthesis fallback")

    # Offline realistic duration estimation (~320ms per word + base 400ms)
    word_count = len(text.split())
    duration_ms = max(600, int(400 + word_count * 320 / speed))
    
    # Pick frequency based on voice name hash for variety
    freq = 280 + (abs(hash(voice_name)) % 300)
    temp_wav = os.path.join(AUDIO_DIR, f'temp_synth_{abs(hash(text))}.wav')
    generate_beep_wav(temp_wav, duration_ms, freq=freq)
    with open(temp_wav, 'rb') as f:
        content = f.read()
    if os.path.exists(temp_wav):
        os.remove(temp_wav)
    return content, False, duration_ms
