import os
import subprocess
import time
import uuid
import json
import math
import shutil
import wave
import struct
import re
import asyncio

from PIL import Image
from renderer import render_chat_frame, parse_script, render_preview_image, partition_messages_into_pages
from audio_generator import trim_audio_silence, convert_audio_to_wav
import config
from config import BASE_DIR, DATA_DIR, VIDEOS_DIR, SFX_DIR

try:
    os.makedirs(VIDEOS_DIR, exist_ok=True)
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

video_jobs = {}

def get_job_progress(key_code):
    return video_jobs.get(key_code, {"active": False})

def set_job_progress(key_code, active, pct=0, msg="", elapsed_s=0, eta_s=0):
    video_jobs[key_code] = {
        "active": active,
        "pct": pct,
        "msg": msg,
        "elapsed_s": elapsed_s,
        "eta_s": eta_s
    }

def has_audio_stream(filepath):
    """Checks if a video file contains an audio stream."""
    if not filepath or not os.path.exists(filepath):
        return False
    try:
        cmd = [get_ffmpeg(), '-i', filepath]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return any('Audio:' in l for l in res.stderr.splitlines())
    except Exception:
        return False

def build_synced_audio_track(messages, user_audio_dir, output_wav_path, gap_same_ms=0, gap_switch_ms=0, gap_outro_ms=0, fallback_clips=None):
    """
    Constructs a sample-accurate, zero-drift stereo audio track matching every message frame 1:1.
    Removes leading and trailing dead air so speech starts and ends precisely with each DM bubble.
    Returns: (frame_durations_s, message_start_offsets_s, total_duration_s)
    """
    sr = 44100
    frame_durations_s = []
    message_start_offsets_s = []
    cum_s = 0.0

    os.makedirs(os.path.dirname(output_wav_path), exist_ok=True)
    with wave.open(output_wav_path, 'wb') as out_f:
        out_f.setnchannels(2)
        out_f.setsampwidth(2)
        out_f.setframerate(sr)

        for i, msg in enumerate(messages):
            message_start_offsets_s.append(cum_s)
            clip_file = os.path.join(user_audio_dir, f"clip_{i}.wav")

            n_clip = 0
            raw_clip = b''
            if os.path.exists(clip_file) and os.path.getsize(clip_file) > 44:
                trim_audio_silence(clip_file, lead_pad_ms=0, trail_pad_ms=0)
                try:
                    with wave.open(clip_file, 'rb') as wf:
                        n_clip = wf.getnframes()
                        fr_clip = wf.getframerate()
                        ch_clip = wf.getnchannels()
                        sw_clip = wf.getsampwidth()
                        raw_clip = wf.readframes(n_clip)

                    if ch_clip == 1 and sw_clip == 2 and fr_clip == sr:
                        num_samples = len(raw_clip) // 2
                        mono_samples = struct.unpack(f"<{num_samples}h", raw_clip)
                        stereo_frames = bytearray(num_samples * 4)
                        struct.pack_into(f"<{num_samples * 2}h", stereo_frames, 0, *[s for s in mono_samples for _ in (0, 1)])
                        raw_clip = bytes(stereo_frames)
                    elif ch_clip != 2 or sw_clip != 2 or fr_clip != sr:
                        temp_fix = clip_file + ".sync_fix.wav"
                        convert_audio_to_wav(clip_file, temp_fix, sample_rate=sr)
                        with wave.open(temp_fix, 'rb') as fix_f:
                            n_clip = fix_f.getnframes()
                            raw_clip = fix_f.readframes(n_clip)
                        if os.path.exists(temp_fix):
                            try: os.remove(temp_fix)
                            except Exception: pass
                except Exception as e:
                    print(f"Notice: clip_{i}.wav read error: {e}")
                    n_clip = 0
                    raw_clip = b''

            if n_clip <= 0 or not raw_clip:
                fallback_dur = 1.0
                if fallback_clips and i < len(fallback_clips):
                    fallback_dur = float(fallback_clips[i].get('duration_ms', 1000)) / 1000.0
                n_clip = max(int(sr * 0.2), int(sr * fallback_dur))
                raw_clip = b'\x00' * (n_clip * 4)

            out_f.writeframes(raw_clip)

            if i < len(messages) - 1:
                is_same = (
                    msg.get("side") == messages[i + 1].get("side") or
                    (msg.get("name") and msg.get("name") == messages[i + 1].get("name"))
                )
                p_ms = gap_same_ms if is_same else gap_switch_ms
            else:
                p_ms = gap_outro_ms

            pause_samples = int(sr * (p_ms / 1000.0))
            if pause_samples > 0:
                out_f.writeframes(b'\x00' * (pause_samples * 4))

            frame_dur_s = (n_clip + pause_samples) / float(sr)
            frame_durations_s.append(frame_dur_s)
            cum_s += frame_dur_s

    # Also keep user_audio_dir/audio_full.wav synchronized
    user_audio_full = os.path.join(user_audio_dir, 'audio_full.wav')
    if os.path.abspath(output_wav_path) != os.path.abspath(user_audio_full):
        try:
            shutil.copyfile(output_wav_path, user_audio_full)
            mp3_path = os.path.splitext(user_audio_full)[0] + ".mp3"
            ffmpeg_bin = get_ffmpeg()
            subprocess.run(
                [ffmpeg_bin, "-y", "-i", user_audio_full, "-c:a", "libmp3lame", "-ac", "2", "-b:a", "192k", mp3_path],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    return frame_durations_s, message_start_offsets_s, cum_s

def prepare_mixed_audio(speech_audio_path, clips, temp_dir, notif_sound=True, entrance_offsets_s=None):
    """
    Normalizes speech audio to 44100Hz 16-bit stereo PCM and overlays
    the authentic iOS pop sound (data/sfx/pop.wav) at every message entrance.
    """
    ffmpeg = get_ffmpeg()
    norm_speech = os.path.join(temp_dir, 'norm_speech.wav')
    
    # 1. Normalize speech to 44100Hz 16-bit stereo PCM
    try:
        subprocess.run(
            [ffmpeg, '-y', '-i', speech_audio_path, '-ar', '44100', '-ac', '2', norm_speech],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception as e:
        print(f"Notice: Failed to normalize speech audio: {e}")
        return speech_audio_path

    if not notif_sound:
        return norm_speech

    sfx_path = os.path.join(SFX_DIR, 'pop.wav')
    if not os.path.exists(sfx_path):
        return norm_speech

    norm_pop = os.path.join(temp_dir, 'norm_pop.wav')
    try:
        subprocess.run(
            [ffmpeg, '-y', '-i', sfx_path, '-ar', '44100', '-ac', '2', norm_pop],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception as e:
        print(f"Notice: Failed to normalize pop SFX: {e}")
        return norm_speech

    try:
        with wave.open(norm_speech, 'rb') as sw:
            s_frames = sw.readframes(sw.getnframes())
            s_samples = list(struct.unpack('<' + ('h' * (sw.getnframes() * 2)), s_frames))

        with wave.open(norm_pop, 'rb') as pw:
            p_frames = pw.readframes(pw.getnframes())
            p_samples = list(struct.unpack('<' + ('h' * (pw.getnframes() * 2)), p_frames))

        # Calculate message entrance timestamps
        if entrance_offsets_s is not None:
            pop_indices = [int(round(off * 44100)) * 2 for off in entrance_offsets_s]
        else:
            cum_ms = 0
            pop_indices = []
            for c in clips:
                sample_offset = int((cum_ms / 1000.0) * 44100) * 2
                pop_indices.append(sample_offset)
                cum_ms += c.get('duration_ms', 1000)

        # Mix pop samples
        for p_idx in pop_indices:
            for i in range(len(p_samples)):
                t_idx = p_idx + i
                if t_idx < len(s_samples):
                    v = int(s_samples[t_idx] + p_samples[i] * 0.85)
                    s_samples[t_idx] = max(-32768, min(32767, v))

        out_mixed = os.path.join(temp_dir, 'speech_with_pops.wav')
        with wave.open(out_mixed, 'wb') as ow:
            ow.setnchannels(2)
            ow.setsampwidth(2)
            ow.setframerate(44100)
            ow.writeframes(struct.pack('<' + ('h' * len(s_samples)), *s_samples))

        return out_mixed
    except Exception as me:
        print(f"Notice: Audio mixing encountered: {me}, using normalized speech")
        return norm_speech

async def generate_video_task(key_code, payload, clips, audio_full_path):
    start_time = time.time()
    set_job_progress(key_code, True, pct=5, msg="Preparing video frames...")

    token = str(uuid.uuid4())
    temp_dir = os.path.join(VIDEOS_DIR, f'temp_{token}')
    os.makedirs(temp_dir, exist_ok=True)

    try:
        settings = payload.get('settings', {})
        script_text = settings.get('script') or payload.get('script', '')
        style = settings.get('style') or payload.get('style', 'ios')
        theme = settings.get('theme') or payload.get('theme', 'light')
        if style == 'whatsapp' and 'wa_theme' in settings:
            theme = settings['wa_theme']

        contact_name, messages, contacts = parse_script(script_text)
        if not messages:
            raise ValueError("Script contains no messages to render.")

        # Ensure clips metadata matches messages
        if not clips or len(clips) < len(messages):
            # Try to get clips from payload directly
            payload_clips = payload.get('clips', [])
            if payload_clips and len(payload_clips) >= len(messages):
                clips = payload_clips
            else:
                # Estimate duration per message
                clips = []
                speed = float(payload.get('speed_factor', 1.0))
                for m in messages:
                    wc = len(m['text'].split())
                    dur = max(1000, int(400 + wc * 320 / max(0.5, speed)))
                    clips.append({
                        'duration_ms': dur,
                        'text': m['text'],
                        'side': m['side']
                    })

        user_audio_dir = os.path.join(DATA_DIR, 'audio', key_code)
        msgs_per_page = int(payload.get('msgs_per_page') or settings.get('msgs_per_page') or 5)
        if msgs_per_page < 1:
            msgs_per_page = 5

        chat_y = payload.get('chat_y') or settings.get('chat_y') or 350
        pages = partition_messages_into_pages(messages, msgs_per_page=msgs_per_page)
        message_frame_info = {}
        for p in pages:
            p_raw_msgs = [m for _, m in p['messages']]
            for k, (global_idx, msg) in enumerate(p['messages'], start=1):
                message_frame_info[global_idx] = {
                    'page_msgs': p_raw_msgs,
                    'visible_count': k,
                    'contact_name': p['contact_name'],
                    'show_header': p['show_header'],
                    'page_index': p['page_index']
                }

        gap_same_ms = int(settings.get('gap_same_ms', 0) if settings.get('gap_same_ms') is not None else 0)
        gap_switch_ms = int(settings.get('gap_switch_ms', 0) if settings.get('gap_switch_ms') is not None else 0)
        gap_outro_ms = int(settings.get('gap_outro_ms', 0) if settings.get('gap_outro_ms') is not None else 0)

        # Build sample-accurate synced audio track matching each DM frame 1:1
        synced_audio_wav = os.path.join(temp_dir, 'synced_audio.wav')
        frame_durations_s, message_start_offsets_s, total_duration_s = build_synced_audio_track(
            messages=messages,
            user_audio_dir=user_audio_dir,
            output_wav_path=synced_audio_wav,
            gap_same_ms=gap_same_ms,
            gap_switch_ms=gap_switch_ms,
            gap_outro_ms=gap_outro_ms,
            fallback_clips=clips
        )

        # 1. Render Progressive Video Frames
        set_job_progress(key_code, True, pct=20, msg="Rendering high-fidelity chat frames...")
        
        width, height = 1080, 1920
        badge_count = int(payload.get('badge_count', settings.get('badge_count', 0)))
        corner_rad = int(payload.get('corner_radius') or settings.get('corner_radius') or 0)
        container_scale = float(payload.get('container_scale') or settings.get('container_scale') or 1.0)
        notif_sound = bool(payload.get('notif_sound', False))

        bubble_scale = payload.get('bubble_scale') or settings.get('bubble_scale')
        bubble_max_pct = payload.get('bubble_max_pct') or settings.get('bubble_max_pct')
        min_bubble_w = payload.get('min_bubble_w') or settings.get('min_bubble_w')
        font_size_override = payload.get('font_size') or settings.get('font_size')
        header_name_size = (
            payload.get('header_name_size') or settings.get('header_name_size') or
            payload.get('name_font_size') or settings.get('name_font_size')
        )

        concat_lines = []
        for i in range(len(messages)):
            frame_filename = f'frame_{i:04d}.png'
            frame_path = os.path.join(temp_dir, frame_filename)
            info = message_frame_info.get(i, {
                'page_msgs': messages,
                'visible_count': i + 1,
                'contact_name': contact_name,
                'show_header': True
            })
            
            frame_img = render_chat_frame(
                info['page_msgs'],
                visible_count=info['visible_count'],
                contact_name=info['contact_name'],
                badge_count=badge_count,
                style=style,
                theme=theme,
                width=width,
                height=height,
                chat_y=chat_y,
                container_scale=container_scale,
                corner_radius_val=corner_rad,
                container_shadow=False,
                show_header=info['show_header'],
                bubble_scale=bubble_scale,
                bubble_max_pct=bubble_max_pct,
                min_bubble_w=min_bubble_w,
                font_size_override=font_size_override,
                header_name_size=header_name_size
            )
            frame_img.save(frame_path)

            dur_s = frame_durations_s[i]
            concat_lines.append(f"file '{frame_filename}'\nduration {dur_s:.4f}")

            pct = 20 + int(30 * (i + 1) / len(messages))
            set_job_progress(key_code, True, pct=pct, msg=f"Rendered frame {i+1} of {len(messages)}...")

        # Concat demuxer requirement: repeat last frame
        last_filename = f'frame_{len(messages)-1:04d}.png'
        concat_lines.append(f"file '{last_filename}'\n")

        concat_path = os.path.join(temp_dir, 'concat.txt')
        with open(concat_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(concat_lines))

        # 2. Prepare Audio
        set_job_progress(key_code, True, pct=55, msg="Mixing audio and sound effects...")
        actual_audio = synced_audio_wav
        mixed_audio_path = prepare_mixed_audio(actual_audio, clips, temp_dir, notif_sound=notif_sound, entrance_offsets_s=message_start_offsets_s)

        # 3. Locate Gameplay Video
        gameplay_file = payload.get('gameplay_file', '')
        gameplay_path = None
        candidates = []
        if gameplay_file:
            candidates.extend([
                os.path.join(DATA_DIR, 'gameplay', gameplay_file),
                os.path.join(os.path.dirname(__file__), 'assets', 'demo', gameplay_file),
                os.path.join(os.path.dirname(__file__), 'data', 'gameplay', gameplay_file)
            ])
        # Defaults
        candidates.extend([
            os.path.join(DATA_DIR, 'gameplay', 'curry_trickshot.mp4'),
            os.path.join(os.path.dirname(__file__), 'assets', 'demo', 'demo1.mp4'),
            os.path.join(os.path.dirname(__file__), 'assets', 'demo', 'demo2.mp4')
        ])

        for c in candidates:
            if os.path.exists(c):
                gameplay_path = c
                break

        # 4. Locate Background Music
        bg_sound_file = payload.get('bg_sound_file', '')
        bg_sound_path = None
        bg_sound_vol = float(payload.get('bg_sound_volume', 0)) / 100.0
        if bg_sound_file:
            bg_cand = os.path.join(DATA_DIR, 'music', bg_sound_file)
            if os.path.exists(bg_cand):
                bg_sound_path = bg_cand

        # 5. FFmpeg Video Compositing
        set_job_progress(key_code, True, pct=70, msg="Encoding with FFmpeg...", elapsed_s=int(time.time() - start_time))
        output_mp4 = os.path.join(VIDEOS_DIR, f'{token}.mp4')
        ffmpeg_bin = get_ffmpeg()

        cmd = [ffmpeg_bin, '-y']

        # Inputs:
        # Input 0: Gameplay video (stream looped)
        if gameplay_path:
            cmd.extend(['-stream_loop', '-1', '-i', gameplay_path])
        else:
            # Fallback black canvas
            cmd.extend(['-f', 'lavfi', '-i', f'color=c=0x111113:s={width}x{height}:r=30'])

        # Input 1: Concat image demuxer (transparent chat frames)
        cmd.extend(['-f', 'concat', '-safe', '0', '-i', concat_path])

        # Input 2: Speech + Pop SFX audio
        audio_idx = 2
        has_speech = (mixed_audio_path and os.path.exists(mixed_audio_path))
        if has_speech:
            cmd.extend(['-i', mixed_audio_path])

        # Filter complex
        filter_parts = []
        # Video overlay
        filter_parts.append(
            f"[0:v]fps=60,scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}[bg];"
            f"[1:v]fps=60[fg];"
            f"[bg][fg]overlay=0:0[vout]"
        )

        # Audio mixing
        has_gp_audio = gameplay_path and has_audio_stream(gameplay_path) and payload.get('gameplay_on', False)
        
        if has_speech and has_gp_audio:
            filter_parts.append(f"[0:a]volume=0.15[gpa];[{audio_idx}:a]volume=1.0[spa];[gpa][spa]amix=inputs=2:duration=first[aout]")
            audio_map = '[aout]'
        elif has_speech:
            audio_map = f'{audio_idx}:a'
        elif has_gp_audio:
            filter_parts.append("[0:a]volume=0.3[aout]")
            audio_map = '[aout]'
        else:
            audio_map = None

        cmd.extend(['-filter_complex', ';'.join(filter_parts)])
        cmd.extend(['-map', '[vout]'])
        if audio_map:
            cmd.extend(['-map', audio_map])

        cmd.extend([
            '-r', '60',
            '-t', f'{total_duration_s:.3f}',
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-preset', 'veryfast',
            '-crf', '20',
            '-c:a', 'aac',
            '-b:a', '192k',
            output_mp4
        ])

        print(f"Executing FFmpeg: {' '.join(cmd)}")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if proc.returncode != 0:
            err_msg = proc.stderr.decode('utf-8', errors='ignore')[-600:]
            print(f"FFmpeg composite failed: {err_msg}")
            # Robust fallback: render video without audio mix if filter failed
            fallback_cmd = [
                ffmpeg_bin, '-y',
                '-stream_loop', '-1', '-i', gameplay_path or 'color=c=0x111113:s=1080x1920:r=30',
                '-f', 'concat', '-safe', '0', '-i', concat_path,
                '-filter_complex', f'[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}[bg];[bg][1:v]overlay=0:0[vout]',
                '-map', '[vout]',
                '-t', f'{total_duration_s:.3f}',
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-preset', 'veryfast',
                output_mp4
            ]
            subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Cleanup temp directory
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass

        set_job_progress(key_code, False, pct=100, msg="Done!", elapsed_s=int(time.time() - start_time))
        
        return {
            "token": token,
            "download_url": f"/download/{token}",
            "duration_s": total_duration_s,
            "filepath": output_mp4
        }
    except Exception as e:
        set_job_progress(key_code, False, pct=0, msg=f"Error: {e}")
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
        raise e

def get_sub_script_for_message(script_text, target_global_idx):
    """
    Extracts the script content up to target_global_idx (0-based), preserving
    all previous contact headers, breaks, and messages intact.
    """
    lines = script_text.splitlines()
    sub_lines = []
    msg_idx = -1
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith('---'):
            sub_lines.append(raw_line)
            continue
        is_msg = bool(re.match(r'^\[?[12]\]?[:\.\-\>]\s*(.*)$', line) or re.match(r'^(?:\[?([12])\]?[:\.\-\>]\s*)?img:\s*(.+)$', line, re.I))
        if is_msg:
            msg_idx += 1
            sub_lines.append(raw_line)
            if msg_idx == target_global_idx:
                break
        else:
            sub_lines.append(raw_line)
    return '\n'.join(sub_lines)

async def generate_slideshow_video_task(key_code, payload, clips, audio_full_path, render_page_func=None):
    """
    Assembles a high-fidelity synchronized animated video where each DM is revealed
    one by one as the dialogue is spoken by ElevenLabs.
    - Uses exact web preview rendering with authentic Apple Color Emojis and dynamic card hugging.
    - True iOS iMessage curved beak tails and styling: left grey (#e5e5ea) and right blue (#007aff).
    - Perfect frame-accurate synchronization with audio clips and conversational pauses.
    - Encoded to 1080x1920 Full HD MP4 with clean speech audio.
    """
    start_time = time.time()
    set_job_progress(key_code, True, pct=5, msg="Preparing synced animated video...")

    token = str(uuid.uuid4())
    temp_dir = os.path.join(VIDEOS_DIR, f'temp_anim_{token}')
    os.makedirs(temp_dir, exist_ok=True)

    try:
        settings = payload.get('settings', {}) if isinstance(payload.get('settings'), dict) else {}
        script_text = payload.get('script') or settings.get('script', '')
        contact_name, messages, contacts = parse_script(script_text)
        if not messages:
            raise ValueError("Script contains no messages to generate video.")

        msgs_per_page = int(payload.get('msgs_per_page') or settings.get('msgs_per_page') or 5)
        if msgs_per_page < 1:
            msgs_per_page = 5

        # 1. Partition messages into pages
        pages = partition_messages_into_pages(messages, msgs_per_page=msgs_per_page)
        msg_to_page = {}
        for p in pages:
            for _, (g_idx, _) in enumerate(p['messages']):
                msg_to_page[g_idx] = p['page_index']

        # 2. Build sample-accurate synced audio track matching each DM frame 1:1
        user_audio_dir = os.path.join(DATA_DIR, 'audio', key_code)
        gap_same_ms = int(settings.get('gap_same_ms', 0) if settings.get('gap_same_ms') is not None else 0)
        gap_switch_ms = int(settings.get('gap_switch_ms', 0) if settings.get('gap_switch_ms') is not None else 0)
        gap_outro_ms = int(settings.get('gap_outro_ms', 0) if settings.get('gap_outro_ms') is not None else 0)

        synced_audio_wav = os.path.join(temp_dir, 'synced_audio.wav')
        frame_durations_s, message_start_offsets_s, final_total_s = build_synced_audio_track(
            messages=messages,
            user_audio_dir=user_audio_dir,
            output_wav_path=synced_audio_wav,
            gap_same_ms=gap_same_ms,
            gap_switch_ms=gap_switch_ms,
            gap_outro_ms=gap_outro_ms,
            fallback_clips=clips
        )

        # 3. Render progressive frames using the web preview engine (Apple Color Emoji, authentic iMessage bubbles)
        set_job_progress(key_code, True, pct=20, msg=f"Rendering progressive DM frames (0 of {len(messages)})...")
        sem = asyncio.Semaphore(4)
        rendered_frames = [None] * len(messages)
        completed_count = 0

        async def render_single_frame(i):
            nonlocal completed_count
            async with sem:
                p_idx = msg_to_page.get(i, 0)
                sub_script = get_sub_script_for_message(script_text, i)
                body_i = payload.copy()
                body_i['script'] = sub_script
                body_i['page'] = p_idx
                if render_page_func:
                    img_bytes, _ = await render_page_func(body_i, p_idx, key_code)
                else:
                    img_bytes, _ = render_preview_image(body_i)

                fname = f"frame_{i:04d}.jpg"
                fpath = os.path.join(temp_dir, fname)
                with open(fpath, "wb") as f:
                    f.write(img_bytes)

                rendered_frames[i] = fname
                completed_count += 1
                pct = 20 + int(45 * (completed_count / len(messages)))
                set_job_progress(key_code, True, pct=pct, msg=f"Rendered DM frame {completed_count} of {len(messages)}...")

        await asyncio.gather(*(render_single_frame(i) for i in range(len(messages))))

        # 4. Build concat.txt
        concat_lines = []
        for i in range(len(messages)):
            concat_lines.append(f"file '{rendered_frames[i]}'")
            concat_lines.append(f"duration {frame_durations_s[i]:.4f}")
        # Concat demuxer requirement: repeat final frame
        concat_lines.append(f"file '{rendered_frames[-1]}'")

        concat_path = os.path.join(temp_dir, 'concat.txt')
        with open(concat_path, 'w', encoding='utf-8') as cf:
            cf.write('\n'.join(concat_lines) + '\n')

        # 5. Prepare Audio (pure voice speech track, no notification pop sound)
        set_job_progress(key_code, True, pct=70, msg="Preparing speech audio...")
        actual_audio = synced_audio_wav
        notif_sound = bool(payload.get('notif_sound', False))
        mixed_audio_path = prepare_mixed_audio(actual_audio, clips, temp_dir, notif_sound=notif_sound, entrance_offsets_s=message_start_offsets_s)

        # 6. Encode video with FFmpeg
        set_job_progress(key_code, True, pct=80, msg="Encoding animated video with FFmpeg...", elapsed_s=int(time.time() - start_time))
        output_mp4 = os.path.abspath(os.path.join(VIDEOS_DIR, f"{token}.mp4"))
        ffmpeg_bin = get_ffmpeg()

        cmd = [
            ffmpeg_bin, '-y',
            '-f', 'concat', '-safe', '0', '-i', 'concat.txt',
        ]
        if mixed_audio_path and os.path.exists(mixed_audio_path):
            cmd.extend(['-i', os.path.abspath(mixed_audio_path)])
            audio_args = ['-c:a', 'aac', '-b:a', '192k']
        else:
            cmd.extend(['-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo'])
            audio_args = ['-c:a', 'aac']

        cmd.extend([
            '-vf', 'fps=60,scale=1080:1920:flags=lanczos,format=yuv420p',
            '-r', '60',
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-crf', '18',
            *audio_args,
            '-shortest',
            output_mp4
        ])

        print(f"Executing animated video FFmpeg: {' '.join(cmd)}")
        proc = subprocess.run(cmd, cwd=temp_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            err = proc.stderr.decode('utf-8', errors='ignore')
            print(f"FFmpeg error: {err}")
            raise RuntimeError(f"FFmpeg video encoding failed: {err[-300:]}")

        # Cleanup temp directory
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass

        set_job_progress(key_code, False, pct=100, msg="Done!", elapsed_s=int(time.time() - start_time))

        return {
            "ok": True,
            "token": token,
            "download_url": f"/download/{token}",
            "duration_s": round(final_total_s, 2),
            "filepath": output_mp4,
            "total_slides": len(pages),
            "total_dms": len(messages)
        }
    except Exception as e:
        set_job_progress(key_code, False, pct=0, msg=f"Error: {e}")
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
        raise e


