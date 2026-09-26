import os
import subprocess
import time
import uuid
import json
import math
import shutil
import wave
import struct

from renderer import render_chat_frame, parse_script

if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    VIDEOS_DIR = "/tmp/data/videos"
    DATA_DIR = "/tmp/data"
else:
    VIDEOS_DIR = os.path.join(os.path.dirname(__file__), 'data', 'videos')
    DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

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

def prepare_mixed_audio(speech_audio_path, clips, temp_dir, notif_sound=True):
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

    sfx_path = os.path.join(os.path.dirname(__file__), 'data', 'sfx', 'pop.wav')
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

        total_duration_ms = sum(c.get('duration_ms', 1000) for c in clips[:len(messages)])
        total_duration_s = max(2.0, total_duration_ms / 1000.0)

        # 1. Render Progressive Video Frames
        set_job_progress(key_code, True, pct=20, msg="Rendering high-fidelity chat frames...")
        
        width, height = 1080, 1920
        badge_count = int(payload.get('badge_count', settings.get('badge_count', 0)))
        corner_rad = int(payload.get('corner_radius', settings.get('corner_radius', 35)))
        container_scale = float(payload.get('container_scale', settings.get('container_scale', 1.0)))
        notif_sound = bool(payload.get('notif_sound', settings.get('notif_sound', True)))

        concat_lines = []
        for i in range(len(messages)):
            frame_filename = f'frame_{i:04d}.png'
            frame_path = os.path.join(temp_dir, frame_filename)
            
            frame_img = render_chat_frame(
                messages,
                visible_count=i + 1,
                contact_name=contact_name,
                badge_count=badge_count,
                style=style,
                theme=theme,
                width=width,
                height=height,
                chat_y_pct=None,
                container_scale=container_scale,
                corner_radius_val=corner_rad
            )
            frame_img.save(frame_path)

            dur_s = clips[i].get('duration_ms', 1000) / 1000.0
            concat_lines.append(f"file '{frame_filename}'\nduration {dur_s:.3f}")

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
        user_audio_dir = os.path.join(DATA_DIR, 'audio', key_code)
        
        # Locate or synthesize speech track
        actual_audio = None
        if audio_full_path and os.path.exists(audio_full_path):
            actual_audio = audio_full_path
        else:
            cand = os.path.join(user_audio_dir, 'audio_full.wav')
            if os.path.exists(cand):
                actual_audio = cand

        mixed_audio_path = None
        if actual_audio and os.path.exists(actual_audio):
            mixed_audio_path = prepare_mixed_audio(actual_audio, clips, temp_dir, notif_sound=notif_sound)

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
            f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}[bg];"
            f"[bg][1:v]overlay=0:0[vout]"
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
