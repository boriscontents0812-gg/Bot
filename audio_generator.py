import os
import wave
import struct
import math
import httpx
import re

AUDIO_DIR = os.path.join(os.path.dirname(__file__), 'data', 'audio')
os.makedirs(AUDIO_DIR, exist_ok=True)

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

async def synthesize_clip(text, voice_name, eleven_key, model_id='eleven_multilingual_v2', stability=0.25, similarity=0.7, speed=1.0):
    if eleven_key and len(eleven_key) > 10:
        # Attempt real ElevenLabs API call
        try:
            # Voice ID lookup or use default voice
            voice_id = "21m00Tcm4TlvDq8ikWAM" # Rachel default
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "xi-api-key": eleven_key,
                "Content-Type": "application/json"
            }
            payload = {
                "text": text,
                "model_id": model_id,
                "voice_settings": {
                    "stability": stability,
                    "similarity_boost": similarity,
                    "speed": speed
                }
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    return resp.content, True
        except Exception as e:
            print(f"ElevenLabs TTS failed: {e}, falling back to synthetic audio")

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
