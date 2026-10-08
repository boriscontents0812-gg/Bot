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
        wav_file.setnchannels(2)  # Stereo (2 channels)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            t = float(i) / sample_rate
            attack = int(sample_rate * 0.05)
            decay = int(sample_rate * 0.05)
            if i < attack:
                env = float(i) / max(1, attack)
            elif i > num_samples - decay:
                env = float(num_samples - i) / max(1, decay)
            else:
                env = 1.0
            value = int(math.sin(2.0 * math.pi * freq * t) * 8000 * env)
            data = struct.pack('<hh', value, value)  # Stereo: Left + Right
            wav_file.writeframesraw(data)

def convert_audio_to_wav(input_bytes_or_path, output_wav_path, sample_rate=44100) -> int:
    """
    Converts any audio (MP3, AAC, PCM, WAV) to standard 16-bit STEREO 44.1kHz PCM WAV
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
        "-ac", "2",  # Stereo (2 channels)
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

def trim_audio_silence(
    input_wav_path: str,
    output_wav_path: str = None,
    lead_pad_ms: int = 0,
    trail_pad_ms: int = 0,
    threshold: int = None
) -> int:
    """
    High-precision Voice Activity Detection (VAD) audio trimmer.
    Removes all leading and trailing digital silence, MP3 encoder delay, and dead air
    so that audio speech starts and ends EXACTLY with the corresponding message on screen.
    """
    out_path = output_wav_path or input_wav_path
    if not os.path.exists(input_wav_path) or os.path.getsize(input_wav_path) < 44:
        return 0

    try:
        with wave.open(input_wav_path, "rb") as wf:
            n = wf.getnframes()
            r = wf.getframerate()
            ch = wf.getnchannels()
            sw = wf.getsampwidth()
            raw = wf.readframes(n)
    except Exception:
        return 0

    if n == 0 or sw != 2:
        return 0

    num_samples = n * ch
    samples = struct.unpack(f"<{num_samples}h", raw)

    # 5ms window energy analysis
    w_size = max(1, int(r * 0.005))
    num_w = n // w_size
    if num_w == 0:
        return int(round(n * 1000.0 / r))

    mono = [max(abs(samples[i * ch + c]) for c in range(ch)) for i in range(n)]
    rms_list = []
    peak_list = []
    for w in range(num_w):
        chk = mono[w * w_size : (w + 1) * w_size]
        pk = max(chk) if chk else 0
        rms = math.sqrt(sum(x * x for x in chk) / len(chk)) if chk else 0.0
        rms_list.append(rms)
        peak_list.append(pk)

    # Adaptive noise floor estimation
    sorted_rms = sorted(rms_list)
    noise_floor = sorted_rms[max(0, int(len(sorted_rms) * 0.05))]
    speech_rms_thresh = max(180.0, noise_floor * 3.0)
    speech_peak_thresh = max(450, int(speech_rms_thresh * 2.2))

    onset_frame = None
    for w in range(num_w):
        if rms_list[w] >= speech_rms_thresh or peak_list[w] >= speech_peak_thresh:
            win_start = w * w_size
            win_end = min(n, (w + 1) * w_size)
            for f in range(win_start, win_end):
                if mono[f] >= speech_peak_thresh * 0.4:
                    onset_frame = f
                    break
            if onset_frame is None:
                onset_frame = win_start
            break

    offset_frame = None
    for w in range(num_w - 1, -1, -1):
        if rms_list[w] >= speech_rms_thresh or peak_list[w] >= speech_peak_thresh:
            win_start = w * w_size
            win_end = min(n, (w + 1) * w_size)
            for f in range(win_end - 1, win_start - 1, -1):
                if mono[f] >= speech_peak_thresh * 0.4:
                    offset_frame = f + 1
                    break
            if offset_frame is None:
                offset_frame = win_end
            break

    if onset_frame is None or offset_frame is None:
        first_frame = None
        for i in range(n):
            offset = i * ch
            if any(abs(samples[offset + c]) > 200 for c in range(ch)):
                first_frame = i
                break
        if first_frame is None:
            return int(round(n * 1000.0 / r))
        last_frame = first_frame
        for i in range(n - 1, first_frame - 1, -1):
            offset = i * ch
            if any(abs(samples[offset + c]) > 200 for c in range(ch)):
                last_frame = i
                break
        onset_frame = first_frame
        offset_frame = last_frame

    lead_pad_frames = int(r * (lead_pad_ms / 1000.0))
    trail_pad_frames = int(r * (trail_pad_ms / 1000.0))

    start_frame = max(0, onset_frame - lead_pad_frames)
    end_frame = min(n, offset_frame + trail_pad_frames)

    trimmed_samples = list(samples[start_frame * ch : end_frame * ch])
    trimmed_frames = len(trimmed_samples) // ch
    if trimmed_frames <= 0:
        return int(round(n * 1000.0 / r))

    # Apply smooth micro-fade to start (1.5ms) and end (2ms) to eliminate all clicks/pops without audible delay
    fade_in_frames = min(int(r * 0.0015), trimmed_frames // 2)
    for i in range(fade_in_frames):
        factor = i / float(fade_in_frames)
        for c in range(ch):
            trimmed_samples[i * ch + c] = int(trimmed_samples[i * ch + c] * factor)

    fade_out_frames = min(int(r * 0.002), trimmed_frames // 2)
    for i in range(fade_out_frames):
        factor = i / float(fade_out_frames)
        for c in range(ch):
            end_idx = (trimmed_frames - 1 - i) * ch + c
            trimmed_samples[end_idx] = int(trimmed_samples[end_idx] * factor)

    temp_out = out_path + ".trim_tmp.wav"
    try:
        with wave.open(temp_out, "wb") as out_f:
            out_f.setnchannels(ch)
            out_f.setsampwidth(sw)
            out_f.setframerate(r)
            out_f.writeframes(struct.pack(f"<{len(trimmed_samples)}h", *trimmed_samples))

        if os.path.exists(out_path) and os.path.abspath(out_path) == os.path.abspath(input_wav_path):
            os.replace(temp_out, out_path)
        else:
            shutil.move(temp_out, out_path)
    except Exception:
        if os.path.exists(temp_out):
            try:
                os.remove(temp_out)
            except Exception:
                pass

    return int(round(trimmed_frames * 1000.0 / r))

def concat_wav_files(
    wav_list,
    output_filepath,
    pause_ms=0,
    clips_meta=None,
    same_speaker_pause_ms=0,
    switch_speaker_pause_ms=0,
    outro_pause_ms=0
) -> int:
    """
    Combines a list of standard stereo WAV clips into a single stereo WAV file with tight,
    natural conversational pauses between clips. Also creates an accompanying stereo MP3 file.
    Returns total duration in milliseconds.
    """
    if not wav_list:
        return 0

    valid_wavs = [w for w in wav_list if os.path.exists(w) and os.path.getsize(w) > 44]
    if not valid_wavs:
        return 0

    sr = 44100
    with wave.open(output_filepath, "wb") as out_f:
        out_f.setnchannels(2)      # Stereo (2 channels)
        out_f.setsampwidth(2)      # 16-bit
        out_f.setframerate(sr)     # 44.1kHz

        for i, w in enumerate(valid_wavs):
            try:
                with wave.open(w, "rb") as in_f:
                    nch = in_f.getnchannels()
                    sw = in_f.getsampwidth()
                    fr = in_f.getframerate()
                    frames = in_f.readframes(in_f.getnframes())

                    # If mono 16-bit, duplicate samples into stereo 16-bit
                    if nch == 1 and sw == 2 and fr == sr:
                        num_samples = len(frames) // 2
                        mono_samples = struct.unpack(f"<{num_samples}h", frames)
                        stereo_frames = bytearray(num_samples * 4)
                        struct.pack_into(f"<{num_samples * 2}h", stereo_frames, 0, *[s for s in mono_samples for _ in (0, 1)])
                        frames = bytes(stereo_frames)
                    elif nch != 2 or sw != 2 or fr != sr:
                        temp_fixed = w + ".stereo_fix.wav"
                        convert_audio_to_wav(w, temp_fixed, sample_rate=sr)
                        with wave.open(temp_fixed, "rb") as fix_f:
                            frames = fix_f.readframes(fix_f.getnframes())
                        if os.path.exists(temp_fixed):
                            try:
                                os.remove(temp_fixed)
                            except Exception:
                                pass

                    out_f.writeframes(frames)
            except Exception as e:
                print(f"Notice: skipped corrupted wav {w}: {e}")
                continue

            if i < len(valid_wavs) - 1:
                if clips_meta and i < len(clips_meta) - 1:
                    c_cur = clips_meta[i]
                    c_next = clips_meta[i + 1]
                    is_same = (
                        str(c_cur.get('side', 1)) == str(c_next.get('side', 2)) or
                        (c_cur.get('voice') and c_cur.get('voice') == c_next.get('voice'))
                    )
                    p_ms = same_speaker_pause_ms if is_same else switch_speaker_pause_ms
                else:
                    p_ms = pause_ms

                if p_ms > 0:
                    silence_samples = int(sr * (p_ms / 1000.0))
                    # Stereo 16-bit: 2 channels * 2 bytes = 4 bytes per frame
                    out_f.writeframes(b'\x00' * (silence_samples * 4))
            else:
                if outro_pause_ms > 0:
                    silence_samples = int(sr * (outro_pause_ms / 1000.0))
                    out_f.writeframes(b'\x00' * (silence_samples * 4))

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
                [ffmpeg_bin, "-y", "-i", output_filepath, "-c:a", "libmp3lame", "-ac", "2", "-b:a", "192k", mp3_path],
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
    Synthesizes a single line of text with ElevenLabs TTS, converts output to standard STEREO WAV,
    and returns (wav_bytes, is_real, duration_ms).
    Includes automatic retry on 429 rate limit errors to ensure no lines are dropped.
    """
    import asyncio
    eleven_key = (eleven_key or "").strip() or ELEVEN_API_KEY or os.environ.get("ELEVEN_API_KEY", "")
    voice_id = resolve_voice_id(voice_id_or_name, side=side)

    # Clean text to synthesize (split display == spoken if present)
    clean_text = str(text or "").strip()
    if "==" in clean_text:
        clean_text = clean_text.split("==", 1)[1].strip()

    if not clean_text:
        dur_ms = 350
        target_path = output_wav_path or os.path.join(AUDIO_DIR, f"temp_empty_{int(time.time()*1000)}.wav")
        generate_beep_wav(target_path, dur_ms, freq=100)
        with open(target_path, "rb") as wf:
            wav_bytes = wf.read()
        if not output_wav_path and os.path.exists(target_path):
            os.remove(target_path)
        return wav_bytes, False, dur_ms

    # 1. Real ElevenLabs TTS API with retry on 429 / network glitch
    if eleven_key and len(eleven_key) > 10:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": eleven_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        }
        payload = {
            "text": clean_text,
            "model_id": model_id,
            "voice_settings": {
                "stability": float(stability),
                "similarity_boost": float(similarity),
                "speed": float(speed)
            }
        }

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code == 200 and len(resp.content) > 200:
                        target_path = output_wav_path or os.path.join(AUDIO_DIR, f"temp_{abs(hash(clean_text))}.wav")
                        dur_ms = convert_audio_to_wav(resp.content, target_path)
                        dur_ms = trim_audio_silence(target_path, lead_pad_ms=0, trail_pad_ms=0)
                        with open(target_path, "rb") as wf:
                            wav_bytes = wf.read()
                        if not output_wav_path and os.path.exists(target_path):
                            os.remove(target_path)
                        return wav_bytes, True, dur_ms
                    elif resp.status_code == 429:
                        wait_sec = 1.5 * (attempt + 1)
                        print(f"Notice: ElevenLabs 429 rate limit, waiting {wait_sec}s before retry ({attempt+1}/3)...")
                        await asyncio.sleep(wait_sec)
                        continue
                    elif resp.status_code >= 500:
                        await asyncio.sleep(1.0)
                        continue
                    else:
                        print(f"Notice: ElevenLabs TTS returned status {resp.status_code}: {resp.text[:200]}")
                        break
            except Exception as e:
                print(f"Notice: ElevenLabs TTS attempt {attempt+1} failed: {e}")
                await asyncio.sleep(1.0)

    # 2. Offline fallback synthetic stereo audio
    word_count = len(clean_text.split())
    dur_ms = max(600, int(400 + word_count * 320 / max(0.5, speed)))
    freq = 220 + (abs(hash(voice_id_or_name)) % 300)

    target_path = output_wav_path or os.path.join(AUDIO_DIR, f"temp_synth_{abs(hash(clean_text))}.wav")
    generate_beep_wav(target_path, dur_ms, freq=freq)
    with open(target_path, "rb") as wf:
        wav_bytes = wf.read()
    if not output_wav_path and os.path.exists(target_path):
        os.remove(target_path)

    return wav_bytes, False, dur_ms
