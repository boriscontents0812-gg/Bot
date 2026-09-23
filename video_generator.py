import os
import subprocess
import time
import uuid
import json
import math
import shutil
from PIL import Image
import imageio_ffmpeg
from renderer import render_preview_image

if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    VIDEOS_DIR = "/tmp/data/videos"
else:
    VIDEOS_DIR = os.path.join(os.path.dirname(__file__), 'data', 'videos')

try:
    os.makedirs(VIDEOS_DIR, exist_ok=True)
except Exception:
    pass

try:
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = shutil.which("ffmpeg") or "ffmpeg"

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
        # Calculate total duration from clips
        total_duration_ms = sum(c.get('duration_ms', 1000) for c in clips) if clips else 5000
        total_duration_s = max(3.0, total_duration_ms / 1000.0)

        # Generate chat frame images
        set_job_progress(key_code, True, pct=25, msg="Rendering chat bubbles...")
        
        # Render the final frame
        preview_body = payload.get('settings', {}).copy()
        preview_body['script'] = payload.get('settings', {}).get('script', '')
        preview_body['style'] = payload.get('settings', {}).get('style', 'ios')
        preview_body['page'] = 0
        
        frame_bytes, _ = render_preview_image(preview_body)
        frame_path = os.path.join(temp_dir, 'chat_frame.jpg')
        with open(frame_path, 'wb') as f:
            f.write(frame_bytes)

        # Background video/color
        gameplay_file = payload.get('gameplay_file', '')
        gameplay_path = None
        if gameplay_file:
            # Check data/gameplay or assets/demo
            p1 = os.path.join(os.path.dirname(__file__), 'data', 'gameplay', gameplay_file)
            p2 = os.path.join(os.path.dirname(__file__), 'assets', 'demo', gameplay_file)
            if os.path.exists(p1):
                gameplay_path = p1
            elif os.path.exists(p2):
                gameplay_path = p2

        # Check background music
        bg_sound_file = payload.get('bg_sound_file', '')
        bg_sound_path = None
        if bg_sound_file:
            p1 = os.path.join(os.path.dirname(__file__), 'data', 'music', bg_sound_file)
            if os.path.exists(p1):
                bg_sound_path = p1

        set_job_progress(key_code, True, pct=50, msg="Encoding with FFmpeg...", elapsed_s=int(time.time() - start_time))

        output_mp4 = os.path.join(VIDEOS_DIR, f'{token}.mp4')

        # Build FFmpeg command
        # If gameplay video exists, chroma key the green (#00FF00) frame over gameplay
        # If not, simply render the green frame or solid background
        cmd = [FFMPEG_EXE, '-y']

        if gameplay_path:
            # Input 0: gameplay video (stream loop)
            cmd.extend(['-stream_loop', '-1', '-i', gameplay_path])
            # Input 1: chat frame image (loop)
            cmd.extend(['-loop', '1', '-i', frame_path])
            
            # Complex filter:
            # Scale gameplay to 1080x1920 (fill/crop), chromakey green out of chat frame, overlay chat over gameplay
            filter_complex = (
                "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[bg];"
                "[1:v]scale=1080:1920,colorkey=0x00FF00:0.3:0.1[fg];"
                "[bg][fg]overlay=0:0[vout]"
            )
            cmd.extend(['-filter_complex', filter_complex, '-map', '[vout]'])
        else:
            # Input 0: chat frame image
            cmd.extend(['-loop', '1', '-i', frame_path])
            cmd.extend(['-vf', 'scale=1080:1920'])

        # Audio inputs
        audio_inputs = 0
        if audio_full_path and os.path.exists(audio_full_path):
            cmd.extend(['-i', audio_full_path])
            speech_idx = 2 if gameplay_path else 1
            cmd.extend(['-map', f'{speech_idx}:a'])
            audio_inputs += 1

        cmd.extend([
            '-t', str(total_duration_s),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-shortest',
            output_mp4
        ])

        print(f"Running FFmpeg: {' '.join(cmd)}")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if proc.returncode != 0:
            print("FFmpeg error:", proc.stderr.decode('utf-8', errors='ignore')[-500:])
            # Fallback simple render if complex filter failed
            simple_cmd = [
                FFMPEG_EXE, '-y',
                '-loop', '1', '-i', frame_path,
                '-t', str(total_duration_s),
                '-c:v', 'libx264',
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
        raise e
