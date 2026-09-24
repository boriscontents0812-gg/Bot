import os
import subprocess
import time
import uuid
import json
import math
import shutil
from renderer import render_preview_image, parse_script

if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    VIDEOS_DIR = "/tmp/data/videos"
else:
    VIDEOS_DIR = os.path.join(os.path.dirname(__file__), 'data', 'videos')

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

async def generate_video_task(key_code, payload, clips, audio_full_path):
    start_time = time.time()
    set_job_progress(key_code, True, pct=5, msg="Preparing video frames...")

    token = str(uuid.uuid4())
    temp_dir = os.path.join(VIDEOS_DIR, f'temp_{token}')
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Settings and script
        settings = payload.get('settings', {}) if isinstance(payload.get('settings'), dict) else {}
        script = payload.get('script') or settings.get('script') or ''
        style = settings.get('style') or payload.get('style') or 'ios'
        
        preview_body = settings.copy()
        preview_body['script'] = script
        preview_body['style'] = style
        preview_body['page'] = 0

        # Parse messages
        _, messages, _ = parse_script(script)
        msg_count = len(messages) if messages else 1

        # Match clips to message count or estimate
        durations = []
        for i in range(msg_count):
            if clips and i < len(clips):
                d_ms = clips[i].get('duration_ms', 1500)
                durations.append(max(0.6, d_ms / 1000.0))
            else:
                durations.append(2.0)

        # End pause of 1.2s for readability
        end_pause = 1.2
        total_duration_s = sum(durations) + end_pause
        # Max duration: 8 minutes (480 seconds)
        total_duration_s = min(480.0, max(2.5, total_duration_s))

        # Generate animated chat frames
        set_job_progress(key_code, True, pct=20, msg=f"Rendering {msg_count} chat bubble frames...")
        
        concat_lines = ['ffconcat version 1.0']
        for i in range(msg_count):
            img_bytes, _ = render_preview_image(preview_body, visible_count=i + 1)
            frame_path = os.path.join(temp_dir, f'frame_{i}.png')
            with open(frame_path, 'wb') as f:
                f.write(img_bytes)
            
            fpath_posix = frame_path.replace(os.sep, '/')
            frame_dur = durations[i]
            if i == msg_count - 1:
                frame_dur += end_pause

            concat_lines.append(f"file '{fpath_posix}'")
            concat_lines.append(f"duration {frame_dur:.3f}")
        
        # Concat demuxer requirement: repeat last file entry
        last_fpath_posix = os.path.join(temp_dir, f'frame_{msg_count - 1}.png').replace(os.sep, '/')
        concat_lines.append(f"file '{last_fpath_posix}'")

        concat_txt = os.path.join(temp_dir, 'concat.txt')
        with open(concat_txt, 'w', encoding='utf-8') as f:
            f.write('\n'.join(concat_lines))

        # Background video/color
        gameplay_file = payload.get('gameplay_file', '')
        gameplay_path = None
        if gameplay_file:
            candidates = [
                os.path.join(os.path.dirname(__file__), 'data', 'gameplay', gameplay_file),
                os.path.join(os.path.dirname(__file__), 'assets', 'demo', gameplay_file)
            ]
            for c in candidates:
                if os.path.exists(c):
                    gameplay_path = c
                    break

        if not gameplay_path:
            # Fallback to demo1.mp4 in assets/demo if available
            demo_cand = os.path.join(os.path.dirname(__file__), 'assets', 'demo', 'demo1.mp4')
            if os.path.exists(demo_cand):
                gameplay_path = demo_cand

        # Background music
        bg_sound_file = payload.get('bg_sound_file', '')
        bg_sound_path = None
        if bg_sound_file:
            candidates = [
                os.path.join(os.path.dirname(__file__), 'data', 'music', bg_sound_file),
                os.path.join(os.path.dirname(__file__), 'assets', 'music', bg_sound_file)
            ]
            for c in candidates:
                if os.path.exists(c):
                    bg_sound_path = c
                    break

        bg_volume = float(payload.get('bg_sound_volume', 0.15))

        set_job_progress(key_code, True, pct=50, msg="Encoding 1080x1920 video with FFmpeg...", elapsed_s=int(time.time() - start_time))

        output_mp4 = os.path.join(VIDEOS_DIR, f'{token}.mp4')
        ffmpeg_bin = get_ffmpeg()
        cmd = [ffmpeg_bin, '-y']

        # Inputs
        # Input 0: Background video or color generator
        has_bg_video = bool(gameplay_path and os.path.exists(gameplay_path))
        if has_bg_video:
            cmd.extend(['-stream_loop', '-1', '-i', gameplay_path])
        else:
            cmd.extend(['-f', 'lavfi', '-i', 'color=c=0x0f172a:s=1080x1920:r=30'])

        # Input 1: Concat demuxer of chat animation frames
        cmd.extend(['-f', 'concat', '-safe', '0', '-i', concat_txt])

        input_count = 2
        voice_in_idx = None
        has_voice = bool(audio_full_path and os.path.exists(audio_full_path) and os.path.getsize(audio_full_path) > 100)
        if has_voice:
            cmd.extend(['-i', audio_full_path])
            voice_in_idx = input_count
            input_count += 1

        bgm_in_idx = None
        has_bgm = bool(bg_sound_path and os.path.exists(bg_sound_path))
        if has_bgm:
            cmd.extend(['-stream_loop', '-1', '-i', bg_sound_path])
            bgm_in_idx = input_count
            input_count += 1

        # Complex filters
        # Video filter: scale background, colorkey chat frames, overlay
        if has_bg_video:
            filter_v = "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[bg];"
        else:
            filter_v = "[0:v]scale=1080:1920[bg];"

        filter_v += "[1:v]scale=1080:1920,colorkey=0x00FF00:0.3:0.1[fg];[bg][fg]overlay=0:0[vout]"

        # Audio filter
        if has_voice and has_bgm:
            filter_a = f";[{voice_in_idx}:a]volume=1.0[voice];[{bgm_in_idx}:a]volume={bg_volume:.2f}[music];[voice][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            cmd.extend(['-filter_complex', filter_v + filter_a, '-map', '[vout]', '-map', '[aout]'])
        elif has_voice:
            cmd.extend(['-filter_complex', filter_v, '-map', '[vout]', '-map', f'{voice_in_idx}:a'])
        elif has_bgm:
            filter_a = f";[{bgm_in_idx}:a]volume={bg_volume:.2f}[aout]"
            cmd.extend(['-filter_complex', filter_v + filter_a, '-map', '[vout]', '-map', '[aout]'])
        else:
            cmd.extend(['-filter_complex', filter_v, '-map', '[vout]'])

        cmd.extend([
            '-t', f'{total_duration_s:.3f}',
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest',
            output_mp4
        ])

        print(f"Executing FFmpeg: {' '.join(cmd)}")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if proc.returncode != 0:
            err_msg = proc.stderr.decode('utf-8', errors='ignore')[-500:]
            print(f"FFmpeg error: {err_msg}")
            # Fallback simple render with first/last frame if complex pipeline failed
            simple_cmd = [
                ffmpeg_bin, '-y',
                '-f', 'concat', '-safe', '0', '-i', concat_txt,
                '-t', f'{total_duration_s:.3f}',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-pix_fmt', 'yuv420p',
                output_mp4
            ]
            subprocess.run(simple_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        set_job_progress(key_code, False, pct=100, msg="Done!", elapsed_s=int(time.time() - start_time))
        
        # Cleanup temp directory
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass

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
