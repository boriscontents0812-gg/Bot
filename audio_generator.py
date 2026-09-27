import os
import wave
import struct
import math
import httpx
import re
import subprocess
import shutil
import time

import config
from config import AUDIO_DIR, ELEVEN_API_KEY

try:
    os.makedirs(AUDIO_DIR, exist_ok=True)
except Exception:
    pass

FFMPEG_EXE = None

def get_ffmpeg():
    global FFMPEG_EXE
    if FFMPEG_EXE:
        return FFMPEG_EXE
    try:
        import imageio_ffmpeg
        FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        FFMPEG_EXE = shutil.which("ffmpeg") or "ffmpeg"
    return FFMPEG_EXE

VOICE_MAP = {
    "adam": "pNInz6obpgDQGcFmaJgB",
    "sarah": "EXAVITQu4vr4xnSDxMaL",
    "natasha": "EXAVITQu4vr4xnSDxMaL",
    "roger": "CwhRBWXzGAHq8TQ4Fs17",
    "alex": "CwhRBWXzGAHq8TQ4Fs17",
    "charlie": "IKne3meq5aSn9XLyUdCD",
    "george": "JBFqnCBsd6RMkjVDRZzb",
    "callum": "N2lVS1w4EtoT3dr4eOWO",
    "river": "SAz9YHcvj6GT2YYXdXww",
    "harry": "SOYHLrjzK2X1ezoPC6cr",
    "liam": "TX3LPaxmHKxFdv7VOQHJ",
    "alice": "Xb7hH8MSUJpSbSDYk0k2",
    "matilda": "XrExE9yKIg1WjnnlVkGX",
    "will": "bIHbv24MWmeRgasZH58o",
    "jessica": "cgSgspJ2msm6clMCkdW9",
    "eric": "cjVigY5qzO86Huf0OWal",
    "bella": "hpp4J3VqNfWAUOO0d1Us",
    "chris": "iP95p4xoKVk53GoZ742B",
    "brian": "nPczCjzI2devNBz1zQrb",
    "daniel": "onwK4e9ZLuTAKqWW03F9",
    "lily": "pFZP5JQG7iQjIQuC4Bku",
    "nicole": "piTKgcLEGmPE4e6mEKli",
    "bill": "pqHfZKP75CvOlQylNhV4",
    "rachel": "21m00Tcm4TlvDq8ikWAM",
    "laura": "FGY2WhTYpPnrIDTdsKH5",
}

DEFAULT_VOICES_LIST = [
    {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "gender": "male", "category": "premade", "description": "Deep, confident, narrative"},
    {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Sarah (Natasha)", "gender": "female", "category": "premade", "description": "Mature, confident, reassuring"},
    {"id": "CwhRBWXzGAHq8TQ4Fs17", "name": "Roger", "gender": "male", "category": "premade", "description": "Laid-back, casual, resonant"},
    {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "gender": "female", "category": "premade", "description": "Calm, friendly, pleasant"},
    {"id": "IKne3meq5aSn9XLyUdCD", "name": "Charlie", "gender": "male", "category": "premade", "description": "Deep, confident, energetic"},
    {"id": "JBFqnCBsd6RMkjVDRZzb", "name": "George", "gender": "male", "category": "premade", "description": "Warm, captivating storyteller"},
    {"id": "N2lVS1w4EtoT3dr4eOWO", "name": "Callum", "gender": "male", "category": "premade", "description": "Husky, intense, character"},
    {"id": "SAz9YHcvj6GT2YYXdXww", "name": "River", "gender": "non-binary", "category": "premade", "description": "Relaxed, neutral, informative"},
    {"id": "SOYHLrjzK2X1ezoPC6cr", "name": "Harry", "gender": "male", "category": "premade", "description": "Fierce, energetic, assertive"},
    {"id": "TX3LPaxmHKxFdv7VOQHJ", "name": "Liam", "gender": "male", "category": "premade", "description": "Energetic, youthful, creator"},
    {"id": "Xb7hH8MSUJpSbSDYk0k2", "name": "Alice", "gender": "female", "category": "premade", "description": "Clear, engaging, educator"},
    {"id": "XrExE9yKIg1WjnnlVkGX", "name": "Matilda", "gender": "female", "category": "premade", "description": "Knowledgeable, professional"},
    {"id": "bIHbv24MWmeRgasZH58o", "name": "Will", "gender": "male", "category": "premade", "description": "Relaxed, friendly optimist"},
    {"id": "cgSgspJ2msm6clMCkdW9", "name": "Jessica", "gender": "female", "category": "premade", "description": "Playful, bright, warm"},
    {"id": "cjVigY5qzO86Huf0OWal", "name": "Eric", "gender": "male", "category": "premade", "description": "Smooth, trustworthy, announcer"},
    {"id": "hpp4J3VqNfWAUOO0d1Us", "name": "Bella", "gender": "female", "category": "premade", "description": "Professional, bright, warm"},
    {"id": "iP95p4xoKVk53GoZ742B", "name": "Chris", "gender": "male", "category": "premade", "description": "Casual, conversational, real"},
    {"id": "nPczCjzI2devNBz1zQrb", "name": "Brian", "gender": "male", "category": "premade", "description": "Deep, mature, rich"},
    {"id": "onwK4e9ZLuTAKqWW03F9", "name": "Daniel", "gender": "male", "category": "premade", "description": "Steady, authoritative, broadcast"},
    {"id": "pFZP5JQG7iQjIQuC4Bku", "name": "Lily", "gender": "female", "category": "premade", "description": "Warm, gentle, youthful"},
    {"id": "piTKgcLEGmPE4e6mEKli", "name": "Nicole", "gender": "female", "category": "premade", "description": "Whisper, gentle, intimate"},
    {"id": "pqHfZKP75CvOlQylNhV4", "name": "Bill", "gender": "male", "category": "premade", "description": "Trustworthy, mature, authoritative"},
    {"id": "FGY2WhTYpPnrIDTdsKH5", "name": "Laura", "gender": "female", "category": "premade", "description": "Enthusiast, quirky attitude"}
]

_VOICES_CACHE = None
_VOICES_CACHE_TIME = 0

async def get_available_voices(eleven_key: str = None) -> list[dict]:
    global _VOICES_CACHE, _VOICES_CACHE_TIME
    now = time.time()
    if _VOICES_CACHE and (now - _VOICES_CACHE_TIME < 3600):
        return _VOICES_CACHE

    key = (eleven_key or "").strip() or ELEVEN_API_KEY or os.environ.get("ELEVEN_API_KEY", "")
    if key and len(key) > 10:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": key})
                if resp.status_code == 200:
                    raw_voices = resp.json().get("voices", [])
                    res = []
                    for v in raw_voices:
                        labels = v.get("labels") or {}
                        res.append({
                            "id": v.get("voice_id"),
                            "name": v.get("name"),
                            "category": v.get("category", "premade"),
                            "gender": labels.get("gender", ""),
                            "accent": labels.get("accent", ""),
                            "description": labels.get("description", "") or v.get("description", "")
                        })
                    if res:
                        _VOICES_CACHE = res
                        _VOICES_CACHE_TIME = now
                        for v in res:
                            v_name = v["name"].strip().lower()
                            VOICE_MAP[v_name] = v["id"]
                        return res
        except Exception as e:
            print("Notice: could not fetch live ElevenLabs voices:", e)

    _VOICES_CACHE = DEFAULT_VOICES_LIST
    _VOICES_CACHE_TIME = now
    return DEFAULT_VOICES_LIST

def generate_beep_wav(filepath, duration_ms, freq=440.0, sample_rate=44100):
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    with wave.open(filepath, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
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

def convert_audio_to_wav(input_bytes_or_path, output_wav_path, sample_rate=44100) -> int:
    """
    Converts any audio (MP3, AAC, PCM, WAV) to standard 16-bit mono 44.1kHz PCM WAV
    using FFmpeg. Returns duration in milliseconds.
    """
    ffmpeg_bin = get_ffmpeg()
    temp_input = None

    if isinstance(input_bytes_or_path, (bytes, bytearray)):
        temp_input = output_wav_path + ".temp_in.mp3"
        with open(temp_input, "wb") as f:
            f.write(input_bytes_or_path)
        src = temp_input
    else:
        src = str(input_bytes_or_path)

    cmd = [
        ffmpeg_bin, "-y",
        "-i", src,
        "-ar", str(sample_rate),
        "-ac", "1",
        "-c:a", "pcm_s16le",
        output_wav_path
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        if temp_input and os.path.exists(temp_input):
            try:
                os.remove(temp_input)
            except Exception:
                pass

    dur_ms = 0
    if os.path.exists(output_wav_path):
        try:
            with wave.open(output_wav_path, "rb") as wf:
                dur_ms = int(round(wf.getnframes() * 1000.0 / wf.getframerate()))
        except Exception:
            pass

    return max(dur_ms, 300)

def concat_wav_files(wav_list, output_filepath, pause_ms=250) -> int:
    """
    Combines a list of standard WAV clips into a single WAV file with a natural
    pause between clips. Also creates an accompanying MP3 file for streaming.
    Returns total duration in milliseconds.
    """
    if not wav_list:
        return 0

    valid_wavs = [w for w in wav_list if os.path.exists(w) and os.path.getsize(w) > 44]
    if not valid_wavs:
        return 0

    sr = 44100
    with wave.open(output_filepath, "wb") as out_f:
        out_f.setnchannels(1)
        out_f.setsampwidth(2)
        out_f.setframerate(sr)

        for i, w in enumerate(valid_wavs):
            try:
                with wave.open(w, "rb") as in_f:
                    frames = in_f.readframes(in_f.getnframes())
                    out_f.writeframes(frames)
            except Exception as e:
                print(f"Notice: skipped corrupted wav {w}: {e}")
                continue

            if i < len(valid_wavs) - 1 and pause_ms > 0:
                silence_samples = int(sr * (pause_ms / 1000.0))
                out_f.writeframes(b'\x00' * (silence_samples * 2))

    total_ms = 0
    if os.path.exists(output_filepath):
        try:
            with wave.open(output_filepath, "rb") as check:
                total_ms = int(round(check.getnframes() * 1000.0 / check.getframerate()))
        except Exception:
            pass

        try:
            mp3_path = os.path.splitext(output_filepath)[0] + ".mp3"
            ffmpeg_bin = get_ffmpeg()
            subprocess.run(
                [ffmpeg_bin, "-y", "-i", output_filepath, "-c:a", "libmp3lame", "-q:a", "2", mp3_path],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    return total_ms

def resolve_voice_id(voice_id_or_name: str, side: int = 1) -> str:
    """
    Resolves a voice ID or character name into a valid ElevenLabs voice ID.
    """
    val = str(voice_id_or_name or "").strip()
    if not val:
        return "EXAVITQu4vr4xnSDxMaL" if side == 1 else "pNInz6obpgDQGcFmaJgB"

    # Already a 20-character ElevenLabs Voice ID
    if len(val) >= 18 and re.match(r'^[a-zA-Z0-9_\-]+$', val):
        return val

    v_lower = val.lower()
    if v_lower in VOICE_MAP:
        return VOICE_MAP[v_lower]

    for k, vid in VOICE_MAP.items():
        if k in v_lower:
            return vid

    return "EXAVITQu4vr4xnSDxMaL" if side == 1 else "pNInz6obpgDQGcFmaJgB"

async def synthesize_clip(
    text: str,
    voice_id_or_name: str,
    eleven_key: str = None,
    model_id: str = "eleven_multilingual_v2",
    stability: float = 0.25,
    similarity: float = 0.70,
    speed: float = 1.0,
    side: int = 1,
    output_wav_path: str = None
) -> tuple[bytes, bool, int]:
    """
    Synthesizes a single line of text with ElevenLabs TTS, converts output to standard WAV,
    and returns (wav_bytes, is_real, duration_ms).
    """
    eleven_key = (eleven_key or "").strip() or ELEVEN_API_KEY or os.environ.get("ELEVEN_API_KEY", "")
    voice_id = resolve_voice_id(voice_id_or_name, side=side)

    # 1. Real ElevenLabs TTS API
    if eleven_key and len(eleven_key) > 10:
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
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
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200 and len(resp.content) > 200:
                    target_path = output_wav_path or os.path.join(AUDIO_DIR, f"temp_{abs(hash(text))}.wav")
                    dur_ms = convert_audio_to_wav(resp.content, target_path)
                    with open(target_path, "rb") as wf:
                        wav_bytes = wf.read()
                    if not output_wav_path and os.path.exists(target_path):
                        os.remove(target_path)
                    return wav_bytes, True, dur_ms
                else:
                    print(f"Notice: ElevenLabs TTS returned status {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"Notice: ElevenLabs TTS request failed: {e}")

    # 2. Offline fallback synthetic audio
    word_count = len(text.split())
    dur_ms = max(600, int(400 + word_count * 320 / max(0.5, speed)))
    freq = 220 + (abs(hash(voice_id_or_name)) % 300)

    target_path = output_wav_path or os.path.join(AUDIO_DIR, f"temp_synth_{abs(hash(text))}.wav")
    generate_beep_wav(target_path, dur_ms, freq=freq)
    with open(target_path, "rb") as wf:
        wav_bytes = wf.read()
    if not output_wav_path and os.path.exists(target_path):
        os.remove(target_path)

    return wav_bytes, False, dur_ms
