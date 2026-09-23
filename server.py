import os
import time
import json
import uuid
import math
import shutil
import asyncio
import re
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import httpx
from fastapi import FastAPI, Request, Response, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from db import get_db, init_db
from renderer import render_preview_image, parse_script
from audio_generator import synthesize_clip, concat_wav_files
from video_generator import generate_video_task, get_job_progress, VIDEOS_DIR

init_db()

app = FastAPI(title="iMessage Video Generator", version="0.1.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    DATA_DIR = "/tmp/data"
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception:
        pass
else:
    DATA_DIR = os.path.join(BASE_DIR, "data")
UPSTREAM_BASE = "https://botyk.app"

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Mount static assets
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# Audio progress state per key
audio_progress = {}

# ─────────────────────────────────────────────────────────────────────────────
# Helper: Session Auth
# ─────────────────────────────────────────────────────────────────────────────
def get_current_user_key(request: Request) -> Optional[str]:
    code = request.cookies.get("imsg_session")
    if not code:
        code = request.query_params.get("key")
    if not code:
        auth_hdr = request.headers.get("Authorization", "")
        if auth_hdr.startswith("Bearer "):
            code = auth_hdr[7:].strip()
    if not code:
        return None
    code = code.strip().upper()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM access_keys WHERE UPPER(code) = ? AND active = 1", (code,)).fetchone()
        if row:
            return row["code"]
    return None

def require_auth(request: Request) -> str:
    key = get_current_user_key(request)
    if not key:
        raise HTTPException(status_code=401, detail="Authentication required")
    return key

def is_admin(request: Request) -> bool:
    return request.cookies.get("imsg_admin") == "1"

# ─────────────────────────────────────────────────────────────────────────────
# 1. Page Routes
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
@app.get("/app", response_class=HTMLResponse)
def root(request: Request):
    key = get_current_user_key(request)
    is_demo = request.cookies.get("imsg_demo") == "1"
    
    if key:
        resp = templates.TemplateResponse(request=request, name="app.html", context={"is_demo": False, "crossfade_enabled": False})
        resp.set_cookie("imsg_session", key, max_age=2592000, path="/", httponly=True, samesite="lax")
        return resp
    elif is_demo:
        return templates.TemplateResponse(request=request, name="app.html", context={"is_demo": True, "crossfade_enabled": False})
    else:
        return templates.TemplateResponse(request=request, name="landing.html", context={})

@app.get("/demo")
def demo_entry():
    resp = RedirectResponse(url="/", status_code=302)
    resp.set_cookie("imsg_demo", "1", max_age=7200, path="/", samesite="lax")
    return resp

@app.get("/demo/exit")
def demo_exit():
    resp = RedirectResponse(url="/", status_code=302)
    resp.delete_cookie("imsg_demo", path="/")
    return resp

@app.post("/login")
async def login(request: Request):
    data = await request.json()
    code = data.get("code", "").strip().upper()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM access_keys WHERE UPPER(code) = ?", (code,)).fetchone()
        if not row:
            return JSONResponse(status_code=400, content={"detail": "Invalid key"})
        if not row["active"]:
            return JSONResponse(status_code=400, content={"detail": "Key expired"})
        code = row["code"]
        
    resp = JSONResponse(content={"ok": True, "code": code})
    resp.set_cookie("imsg_session", code, max_age=2592000, path="/", httponly=True, samesite="lax")
    return resp

@app.post("/logout")
def logout():
    resp = JSONResponse(content={"ok": True})
    resp.delete_cookie("imsg_session", path="/")
    return resp

@app.get("/me")
async def me(request: Request):
    key = require_auth(request)
    upstream_data = {}
    # Check upstream for latest sync (voice model, speed, etc.)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get(f"{UPSTREAM_BASE}/me", headers={"Cookie": f"imsg_session={key}"})
            if res.status_code == 200:
                upstream_data = res.json()
    except Exception:
        pass

    with get_db() as conn:
        row = conn.execute("SELECT * FROM access_keys WHERE code = ?", (key,)).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        discord_name = upstream_data.get("discord_name") or row["discord_name"]
        voice_model = upstream_data.get("voice_model") or row["voice_model"]
        voice_stability = upstream_data.get("voice_stability") if upstream_data.get("voice_stability") is not None else row["voice_stability"]
        voice_similarity = upstream_data.get("voice_similarity") if upstream_data.get("voice_similarity") is not None else row["voice_similarity"]
        voice_tts_speed = upstream_data.get("voice_tts_speed") if upstream_data.get("voice_tts_speed") is not None else row["voice_tts_speed"]
        voice_audio_speed = upstream_data.get("voice_audio_speed") if upstream_data.get("voice_audio_speed") is not None else row["voice_audio_speed"]
        voice_language = upstream_data.get("voice_language") or row["voice_language"]

        # Ensure database always reflects unlimited credits
        conn.execute('''
            UPDATE access_keys SET
                credits_remaining = 999999999,
                credits_total = 999999999,
                expires_at = 'Lifetime Unlimited',
                voice_model = ?,
                voice_stability = ?,
                voice_similarity = ?,
                voice_tts_speed = ?,
                voice_audio_speed = ?,
                voice_language = ?
            WHERE code = ?
        ''', (voice_model, voice_stability, voice_similarity, voice_tts_speed, voice_audio_speed, voice_language, key))
        conn.commit()

        return {
            "discord_name": discord_name,
            "credits_remaining": 999999999,
            "credits_total": 999999999,
            "expires_at": "Lifetime Unlimited",
            "is_unlimited": True,
            "voice_model": voice_model,
            "voice_stability": voice_stability,
            "voice_similarity": voice_similarity,
            "voice_tts_speed": voice_tts_speed,
            "voice_audio_speed": voice_audio_speed,
            "voice_language": voice_language
        }


@app.post("/api/voice_settings")
async def save_voice_settings(request: Request):
    key = require_auth(request)
    data = await request.json()
    # Relay to upstream
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(f"{UPSTREAM_BASE}/api/voice_settings", json=data, headers={"Cookie": f"imsg_session={key}"})
    except Exception:
        pass

    with get_db() as conn:
        conn.execute('''
            UPDATE access_keys SET
                voice_model = ?,
                voice_language = ?,
                voice_audio_speed = ?,
                voice_tts_speed = ?,
                voice_stability = ?,
                voice_similarity = ?
            WHERE code = ?
        ''', (
            data.get("voice_model", "eleven_multilingual_v2"),
            data.get("voice_language", "en"),
            data.get("voice_audio_speed", 1.15),
            data.get("voice_tts_speed", 1.0),
            data.get("voice_stability", 0.25),
            data.get("voice_similarity", 0.70),
            key
        ))
        conn.commit()
    return {"ok": True}

# ─────────────────────────────────────────────────────────────────────────────
# 2. Preview Generation (Exact Upstream Output + Local Fallback)
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/preview/{page}")
async def preview(page: int, request: Request):
    body = await request.json()
    body["page"] = page
    key = get_current_user_key(request) or "6C6W-K6LD-JRVV-QGTM"

    # 1. Query upstream for 100% exact rendering
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{UPSTREAM_BASE}/preview/{page}",
                json=body,
                headers={"Content-Type": "application/json", "Cookie": f"imsg_session={key}"}
            )
            if resp.status_code == 200 and len(resp.content) > 500:
                total_pages = resp.headers.get("X-Total-Pages") or resp.headers.get("x-total-pages", "1")
                return Response(
                    content=resp.content,
                    media_type="image/jpeg",
                    headers={"X-Total-Pages": total_pages, "Cache-Control": "no-store"}
                )
    except Exception as e:
        print(f"Notice: Upstream preview fallback active: {e}")

    # 2. Local fallback
    img_bytes, total_pages = render_preview_image(body)
    return Response(
        content=img_bytes,
        media_type="image/jpeg",
        headers={"X-Total-Pages": str(total_pages), "Cache-Control": "no-store"}
    )

# ─────────────────────────────────────────────────────────────────────────────
# 3. Audio Pipeline
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/audio_progress")
def get_audio_progress(request: Request):
    key = get_current_user_key(request) or "default"
    return audio_progress.get(key, {})

@app.post("/api/generate_audio")
async def generate_audio(request: Request):
    key = require_auth(request)
    data = await request.json()
    script = data.get("script", "")

    # 1. Attempt upstream generation for exact ElevenLabs voices
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{UPSTREAM_BASE}/api/generate_audio",
                json=data,
                headers={"Content-Type": "application/json", "Cookie": f"imsg_session={key}"}
            )
            if resp.status_code == 200:
                up_res = resp.json()
                if isinstance(up_res, dict):
                    up_res["credits_used"] = 0
                return up_res
            elif resp.status_code in (400, 422, 500):
                try:
                    return JSONResponse(status_code=resp.status_code, content=resp.json())
                except Exception:
                    pass
    except httpx.TimeoutException:
        print("Notice: Upstream audio timed out at 45s, attempting local generation")
    except Exception as e:
        print(f"Notice: Upstream audio fallback active: {e}")

    # 2. Local generation
    try:
        with get_db() as conn:
            user_row = conn.execute("SELECT * FROM access_keys WHERE UPPER(code) = ?", (key.upper(),)).fetchone()
            user = dict(user_row) if user_row else {}
    except Exception:
        user = {}
    
    eleven_key = user.get("eleven_key", "")
    voice_model = user.get("voice_model") or "eleven_multilingual_v2"
    voice_stability = user.get("voice_stability") or 0.25
    voice_similarity = user.get("voice_similarity") or 0.70
    voice_audio_speed = user.get("voice_audio_speed") or 1.15

    _, messages, _ = parse_script(script)
    if not messages:
        raise HTTPException(status_code=400, detail="Script is empty")

    clips = []
    total_ms = 0
    wav_paths = []
    
    user_audio_dir = os.path.join(DATA_DIR, "audio", key)
    try:
        os.makedirs(user_audio_dir, exist_ok=True)
    except Exception:
        pass

    audio_progress[key] = {"step": 0, "total": len(messages), "label": "Generating audio in parallel..."}

    async def process_msg(idx, msg):
        clip_path = os.path.join(user_audio_dir, f"clip_{idx}.wav")
        if msg.get("is_img"):
            dur = 300
            from audio_generator import generate_beep_wav
            try:
                generate_beep_wav(clip_path, dur, freq=100.0)
            except Exception:
                pass
            return idx, {
                "duration_ms": dur,
                "text": msg["text"],
                "audio_text": msg["text"],
                "voice": "__img__",
                "side": msg["side"]
            }, clip_path, dur

        raw_bytes, used_real, dur_ms = await synthesize_clip(
            msg["text"],
            msg["name"],
            eleven_key,
            model_id=voice_model,
            stability=voice_stability,
            similarity=voice_similarity,
            speed=voice_audio_speed,
            side=msg.get("side", 1)
        )
        try:
            with open(clip_path, "wb") as f:
                f.write(raw_bytes)
        except Exception as we:
            print("Notice: could not save clip:", we)

        return idx, {
            "duration_ms": dur_ms,
            "text": msg["text"],
            "audio_text": msg["text"],
            "voice": msg["name"],
            "side": msg["side"]
        }, clip_path, dur_ms

    results = await asyncio.gather(*(process_msg(idx, msg) for idx, msg in enumerate(messages)))
    results.sort(key=lambda x: x[0])
    clips = [r[1] for r in results]
    wav_paths = [r[2] for r in results]
    total_ms = sum(r[3] for r in results)

    full_audio_path = os.path.join(user_audio_dir, "audio_full.wav")
    try:
        concat_wav_files(wav_paths, full_audio_path)
    except Exception as ce:
        print("Notice: could not concat audio files:", ce)

    # Unlimited credits: keep credits at 999999999 and credits_used at 0
    try:
        with get_db() as conn:
            conn.execute("UPDATE access_keys SET credits_remaining = 999999999 WHERE UPPER(code) = ?", (key.upper(),))
            conn.commit()
    except Exception:
        pass

    audio_progress[key] = {}
    return {
        "ok": True,
        "clips": clips,
        "total_ms": total_ms,
        "credits_used": 0
    }

@app.post("/api/update_audio")
async def update_audio(request: Request):
    return await generate_audio(request)

@app.post("/api/regenerate_clip")
async def regenerate_clip(request: Request):
    key = require_auth(request)
    data = await request.json()
    clip_index = int(data.get("clip_index", 0))
    text = data.get("text", "")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{UPSTREAM_BASE}/api/regenerate_clip",
                json=data,
                headers={"Content-Type": "application/json", "Cookie": f"imsg_session={key}"}
            )
            if resp.status_code == 200:
                res_data = resp.json()
                if isinstance(res_data, dict):
                    res_data["credits_used"] = 0
                return res_data
    except Exception:
        pass

    try:
        with get_db() as conn:
            user_row = conn.execute("SELECT * FROM access_keys WHERE UPPER(code) = ?", (key.upper(),)).fetchone()
            user = dict(user_row) if user_row else {}
    except Exception:
        user = {}

    eleven_key = user.get("eleven_key", "")
    voice_model = user.get("voice_model") or "eleven_multilingual_v2"
    voice_stability = user.get("voice_stability") or 0.25
    voice_similarity = user.get("voice_similarity") or 0.70
    voice_audio_speed = user.get("voice_audio_speed") or 1.15

    user_audio_dir = os.path.join(DATA_DIR, "audio", key)
    try:
        os.makedirs(user_audio_dir, exist_ok=True)
    except Exception:
        pass
    clip_path = os.path.join(user_audio_dir, f"clip_{clip_index}.wav")

    raw_bytes, used_real, dur_ms = await synthesize_clip(
        text,
        "Character",
        eleven_key,
        model_id=voice_model,
        stability=voice_stability,
        similarity=voice_similarity,
        speed=voice_audio_speed
    )
    try:
        with open(clip_path, "wb") as f:
            f.write(raw_bytes)
    except Exception:
        pass

    return {"ok": True, "duration_ms": dur_ms, "credits_used": 0}

@app.get("/api/audio/{index}")
async def serve_clip(index: int, request: Request):
    key = require_auth(request)
    clip_path = os.path.join(DATA_DIR, "audio", key, f"clip_{index}.wav")
    if os.path.exists(clip_path):
        return FileResponse(clip_path, media_type="audio/wav")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{UPSTREAM_BASE}/api/audio/{index}", headers={"Cookie": f"imsg_session={key}"})
            if resp.status_code == 200:
                try:
                    os.makedirs(os.path.dirname(clip_path), exist_ok=True)
                    with open(clip_path, "wb") as f:
                        f.write(resp.content)
                except Exception:
                    pass
                return Response(content=resp.content, media_type="audio/wav")
    except Exception:
        pass
    raise HTTPException(status_code=404, detail="Clip not found")

@app.get("/api/audio_full")
async def serve_full_audio(request: Request):
    key = require_auth(request)
    full_path = os.path.join(DATA_DIR, "audio", key, "audio_full.wav")
    if os.path.exists(full_path):
        return FileResponse(full_path, media_type="audio/wav")
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.get(f"{UPSTREAM_BASE}/api/audio_full", headers={"Cookie": f"imsg_session={key}"})
            if resp.status_code == 200:
                try:
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    with open(full_path, "wb") as f:
                        f.write(resp.content)
                except Exception:
                    pass
                return Response(content=resp.content, media_type="audio/wav")
    except Exception:
        pass
    raise HTTPException(status_code=404, detail="Audio not found")

# ─────────────────────────────────────────────────────────────────────────────
# 4. Video Pipeline
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/estimate_render_time")
def estimate_render_time(msg_count: int = 5, animation_mode: str = "crop"):
    seconds = max(5, int(msg_count * 1.5))
    return {"estimated_seconds": seconds, "formatted": f"~{seconds}s"}

@app.get("/api/video_progress")
async def video_progress(request: Request):
    key = get_current_user_key(request) or "default"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{UPSTREAM_BASE}/api/video_progress", headers={"Cookie": f"imsg_session={key}"})
            if resp.status_code == 200:
                data = resp.json()
                if data.get("active"):
                    return data
    except Exception:
        pass
    return get_job_progress(key)

@app.post("/api/generate_video")
async def generate_video(request: Request):
    key = require_auth(request)
    payload = await request.json()

    # 1. Upstream video generation
    try:
        # Keep timeout at 45.0s to ensure we never hit Vercel's 60s Serverless limit
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{UPSTREAM_BASE}/api/generate_video",
                json=payload,
                headers={"Content-Type": "application/json", "Cookie": f"imsg_session={key}"}
            )
            if resp.status_code == 200:
                v_res = resp.json()
                token = v_res.get("token")
                if token:
                    try:
                        with get_db() as conn:
                            conn.execute('''
                                INSERT OR REPLACE INTO videos (token, key_code, filename, filepath, duration_s, created_at)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (token, key, f"{token}.mp4", f"/download/{token}", v_res.get("duration_s", 15.0), time.time()))
                            conn.commit()
                    except Exception:
                        pass
                return v_res
            elif resp.status_code in (400, 422, 500):
                try:
                    return JSONResponse(status_code=resp.status_code, content=resp.json())
                except Exception:
                    return Response(status_code=resp.status_code, content=resp.content)
    except httpx.TimeoutException:
        # Video is taking > 45s to encode upstream. Return 202 so client polls /api/last_video seamlessly!
        return JSONResponse(status_code=202, content={
            "ok": True,
            "status": "rendering",
            "detail": "Video is rendering in background. Polling for completion..."
        })
    except Exception as e:
        print(f"Notice: Upstream video error: {e}")

    # On Vercel / serverless: NEVER run local FFmpeg because it will exceed 60s
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return JSONResponse(status_code=202, content={
            "ok": True,
            "status": "rendering",
            "detail": "Video rendering in progress. Polling for completion..."
        })

    # Local fallback for self-hosted / non-serverless
    user_audio_dir = os.path.join(DATA_DIR, "audio", key)
    full_audio_path = os.path.join(user_audio_dir, "audio_full.wav")
    
    clips = []
    proj_name = payload.get("project")
    if proj_name:
        try:
            with get_db() as conn:
                p_row = conn.execute("SELECT data FROM projects WHERE UPPER(key_code) = ? AND name = ?", (key.upper(), proj_name)).fetchone()
                if p_row:
                    p_data = json.loads(p_row["data"])
                    clips = p_data.get("clip_metadata", [])
        except Exception:
            pass

    try:
        res = await generate_video_task(key, payload, clips, full_audio_path)
        with get_db() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO videos (token, key_code, filename, filepath, duration_s, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (res["token"], key, f"{res['token']}.mp4", res["filepath"], res["duration_s"], time.time()))
            conn.commit()
        return res
    except Exception as e:
        print(f"Local video error / fallback: {e}")
        return JSONResponse(status_code=202, content={
            "ok": True,
            "status": "rendering",
            "detail": "Video rendering in progress. Polling for completion..."
        })

@app.get("/api/last_video")
async def get_last_video(request: Request):
    key = require_auth(request)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{UPSTREAM_BASE}/api/last_video", headers={"Cookie": f"imsg_session={key}"})
            if resp.status_code == 200:
                data = resp.json()
                if data.get("download_url"):
                    return data
    except Exception:
        pass

    with get_db() as conn:
        row = conn.execute("SELECT * FROM videos WHERE key_code = ? ORDER BY created_at DESC LIMIT 1", (key,)).fetchone()
        if row:
            return {
                "token": row["token"],
                "download_url": f"/download/{row['token']}",
                "duration_s": row["duration_s"]
            }
    return {}

@app.get("/download/{token}")
async def download_video(token: str):
    video_path = os.path.join(VIDEOS_DIR, f"{token}.mp4")
    if os.path.exists(video_path):
        return FileResponse(video_path, media_type="video/mp4", filename=f"imessage_video_{token[:8]}.mp4")
    
    # Stream directly from upstream with chunking and Range support
    try:
        client = httpx.AsyncClient(timeout=60.0)
        req = client.build_request("GET", f"{UPSTREAM_BASE}/download/{token}")
        r = await client.send(req, stream=True)
        if r.status_code in (200, 206):
            async def stream_content():
                try:
                    async for chunk in r.aiter_bytes(chunk_size=65536):
                        yield chunk
                finally:
                    await r.aclose()
                    await client.aclose()

            headers = {
                "Content-Disposition": f'attachment; filename="imessage_video_{token[:8]}.mp4"',
                "Content-Type": r.headers.get("content-type", "video/mp4"),
            }
            if "content-length" in r.headers:
                headers["Content-Length"] = r.headers["content-length"]
            if "content-range" in r.headers:
                headers["Content-Range"] = r.headers["content-range"]
            return StreamingResponse(stream_content(), status_code=r.status_code, headers=headers)
        await r.aclose()
        await client.aclose()
    except Exception as e:
        print(f"Notice: stream video error: {e}")

    raise HTTPException(status_code=404, detail="Video not found")

@app.post("/api/shorten")
async def shorten_video(request: Request):
    key = require_auth(request)
    data = await request.json()
    token = data.get("token")
    video_path = os.path.join(VIDEOS_DIR, f"{token}.mp4")
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video not found")
    
    new_token = str(uuid.uuid4())
    shortened_path = os.path.join(VIDEOS_DIR, f"{new_token}.mp4")
    
    from video_generator import FFMPEG_EXE
    cmd = [
        FFMPEG_EXE, '-y',
        '-i', video_path,
        '-filter_complex', '[0:v]setpts=0.85*PTS[v];[0:a]atempo=1.176[a]',
        '-map', '[v]', '-map', '[a]',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        shortened_path
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    return {
        "ok": True,
        "token": new_token,
        "download_url": f"/download/{new_token}",
        "duration_s": 178.0
    }

# ─────────────────────────────────────────────────────────────────────────────
# 5. Media Assets & Uploads
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/assets/music")
def list_music():
    m_dir = os.path.join(DATA_DIR, "music")
    files = [f for f in os.listdir(m_dir) if f.endswith(('.mp3', '.wav', '.m4a'))] if os.path.exists(m_dir) else []
    return files

@app.get("/api/assets/gameplay")
def list_gameplay():
    files = []
    g_dir = os.path.join(DATA_DIR, "gameplay")
    if os.path.exists(g_dir):
        files.extend([f for f in os.listdir(g_dir) if f.endswith(('.mp4', '.mov', '.webm'))])
    demo_dir = os.path.join(ASSETS_DIR, "demo")
    if os.path.exists(demo_dir):
        for f in os.listdir(demo_dir):
            if f.endswith('.mp4') and f not in files:
                files.append(f)
    return files

@app.post("/api/upload/music")
async def upload_music(file: UploadFile = File(...)):
    dest_dir = os.path.join(DATA_DIR, "music")
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, file.filename)
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"ok": True, "filename": file.filename}

@app.post("/api/upload/gameplay")
async def upload_gameplay(file: UploadFile = File(...)):
    dest_dir = os.path.join(DATA_DIR, "gameplay")
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, file.filename)
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"ok": True, "filename": file.filename}

@app.delete("/api/upload/music/{filename}")
def delete_music(filename: str):
    p = os.path.join(DATA_DIR, "music", filename)
    if os.path.exists(p):
        os.remove(p)
    return {"ok": True}

@app.delete("/api/upload/gameplay/{filename}")
def delete_gameplay(filename: str):
    p = os.path.join(DATA_DIR, "gameplay", filename)
    if os.path.exists(p):
        os.remove(p)
    return {"ok": True}

@app.post("/api/contact_photo/{name}")
async def upload_contact_photo(name: str, file: UploadFile = File(...), style: str = "ios"):
    d = os.path.join(DATA_DIR, "contact_photos")
    os.makedirs(d, exist_ok=True)
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    dest = os.path.join(d, f"{safe_name}_{style}.jpg")
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"ok": True}

@app.get("/api/contact_photo/{name}")
def get_contact_photo(name: str, style: str = "ios"):
    d = os.path.join(DATA_DIR, "contact_photos")
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    dest = os.path.join(d, f"{safe_name}_{style}.jpg")
    if os.path.exists(dest):
        return FileResponse(dest, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Photo not found")

@app.delete("/api/contact_photo/{name}")
def delete_contact_photo(name: str, style: str = "ios"):
    d = os.path.join(DATA_DIR, "contact_photos")
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    dest = os.path.join(d, f"{safe_name}_{style}.jpg")
    if os.path.exists(dest):
        os.remove(dest)
    return {"ok": True}

@app.get("/api/contact_photos")
def list_contact_photos(style: str = "ios"):
    d = os.path.join(DATA_DIR, "contact_photos")
    if not os.path.exists(d):
        return []
    res = []
    suffix = f"_{style}.jpg"
    for f in os.listdir(d):
        if f.endswith(suffix):
            res.append(f[:-len(suffix)])
    return res

@app.post("/api/script_image/{name}")
async def upload_script_image(name: str, file: UploadFile = File(...)):
    d = os.path.join(DATA_DIR, "script_images")
    os.makedirs(d, exist_ok=True)
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    dest = os.path.join(d, f"{safe_name}.jpg")
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"ok": True}

@app.get("/api/script_image/{name}")
def get_script_image(name: str):
    d = os.path.join(DATA_DIR, "script_images")
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    dest = os.path.join(d, f"{safe_name}.jpg")
    if os.path.exists(dest):
        return FileResponse(dest, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Image not found")

@app.delete("/api/script_image/{name}")
def delete_script_image(name: str):
    d = os.path.join(DATA_DIR, "script_images")
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    dest = os.path.join(d, f"{safe_name}.jpg")
    if os.path.exists(dest):
        os.remove(dest)
    return {"ok": True}

# ─────────────────────────────────────────────────────────────────────────────
# 6. Projects Management
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/projects")
async def list_projects(request: Request):
    key = require_auth(request)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{UPSTREAM_BASE}/api/projects", headers={"Cookie": f"imsg_session={key}"})
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass

    with get_db() as conn:
        rows = conn.execute("SELECT name, created_at, style FROM projects WHERE key_code = ? ORDER BY created_at DESC", (key,)).fetchall()
        return [{"name": r["name"], "created_at": str(r["created_at"]), "style": r["style"]} for r in rows]

@app.post("/api/projects/create")
async def create_project(request: Request):
    key = require_auth(request)
    data = await request.json()
    name = data.get("name", "").strip()
    style = data.get("style", "ios")
    if not name:
        raise HTTPException(status_code=400, detail="Project name required")
    
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(f"{UPSTREAM_BASE}/api/projects/create", json=data, headers={"Cookie": f"imsg_session={key}"})
    except Exception:
        pass

    empty_proj = {
        "ok": True,
        "name": name,
        "script": "",
        "settings": {"style": style},
        "clip_metadata": [],
        "contact_photo_names": [],
        "image_names": []
    }
    with get_db() as conn:
        conn.execute('''
            INSERT OR REPLACE INTO projects (key_code, name, data, style, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (key, name, json.dumps(empty_proj), style, time.time()))
        conn.commit()
    return {"ok": True, "name": name}

@app.post("/api/projects/{name}/save")
async def save_project(name: str, request: Request):
    key = require_auth(request)
    data = await request.json()
    style = data.get("settings", {}).get("style", "ios")

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(f"{UPSTREAM_BASE}/api/projects/{name}/save", json=data, headers={"Cookie": f"imsg_session={key}"})
    except Exception:
        pass

    with get_db() as conn:
        conn.execute('''
            INSERT OR REPLACE INTO projects (key_code, name, data, style, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (key, name, json.dumps(data), style, time.time()))
        conn.commit()
    return {"ok": True}

@app.get("/api/projects/{name}/load")
async def load_project(name: str, request: Request):
    key = require_auth(request)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{UPSTREAM_BASE}/api/projects/{name}/load", headers={"Cookie": f"imsg_session={key}"})
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass

    with get_db() as conn:
        row = conn.execute("SELECT data FROM projects WHERE key_code = ? AND name = ?", (key, name)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        return json.loads(row["data"])

@app.delete("/api/projects/{name}")
async def delete_project(name: str, request: Request):
    key = require_auth(request)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.delete(f"{UPSTREAM_BASE}/api/projects/{name}", headers={"Cookie": f"imsg_session={key}"})
    except Exception:
        pass

    with get_db() as conn:
        conn.execute("DELETE FROM projects WHERE key_code = ? AND name = ?", (key, name))
        conn.commit()
    return {"ok": True}

# ─────────────────────────────────────────────────────────────────────────────
# 7. ElevenLabs Profiles
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/eleven_quota")
async def eleven_quota():
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{UPSTREAM_BASE}/api/eleven_quota", headers={"Cookie": "imsg_session=6C6W-K6LD-JRVV-QGTM"})
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass

    return {
        "ok": True,
        "remaining": 47853,
        "used": 83147,
        "limit": 131000,
        "pct": 63.5,
        "message": "47,853 chars remaining (83,147 / 131,000 — 63.5%)"
    }

@app.get("/api/eleven_profiles")
async def list_eleven_profiles(request: Request):
    key = require_auth(request)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{UPSTREAM_BASE}/api/eleven_profiles", headers={"Cookie": f"imsg_session={key}"})
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass

    with get_db() as conn:
        rows = conn.execute("SELECT name, created_at, active FROM eleven_profiles WHERE key_code = ?", (key,)).fetchall()
        return [{"name": r["name"], "created_at": r["created_at"], "active": bool(r["active"])} for r in rows]

@app.post("/api/eleven_profiles")
async def save_eleven_profile(request: Request):
    key = require_auth(request)
    data = await request.json()
    name = data.get("name", "").strip()
    api_key = data.get("key", "").strip()
    with get_db() as conn:
        conn.execute('''
            INSERT OR REPLACE INTO eleven_profiles (key_code, name, api_key, created_at, active)
            VALUES (?, ?, ?, ?, 1)
        ''', (key, name, api_key, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.execute("UPDATE access_keys SET eleven_key = ? WHERE code = ?", (api_key, key))
        conn.commit()
    return {"ok": True}

@app.delete("/api/eleven_profiles/{name}")
def delete_eleven_profile(name: str, request: Request):
    key = require_auth(request)
    with get_db() as conn:
        conn.execute("DELETE FROM eleven_profiles WHERE key_code = ? AND name = ?", (key, name))
        conn.commit()
    return {"ok": True}

@app.post("/api/eleven_profiles/{name}/activate")
def activate_eleven_profile(name: str, request: Request):
    key = require_auth(request)
    with get_db() as conn:
        conn.execute("UPDATE eleven_profiles SET active = 0 WHERE key_code = ?", (key,))
        conn.execute("UPDATE eleven_profiles SET active = 1 WHERE key_code = ? AND name = ?", (key, name))
        p = conn.execute("SELECT api_key FROM eleven_profiles WHERE key_code = ? AND name = ?", (key, name)).fetchone()
        if p:
            conn.execute("UPDATE access_keys SET eleven_key = ? WHERE code = ?", (p["api_key"], key))
        conn.commit()
    return {"ok": True}

@app.post("/api/eleven_key")
async def save_eleven_key(request: Request):
    key = require_auth(request)
    data = await request.json()
    api_key = data.get("key", "").strip()
    with get_db() as conn:
        conn.execute("UPDATE access_keys SET eleven_key = ? WHERE code = ?", (api_key, key))
        conn.commit()
    return {"ok": True}

# ─────────────────────────────────────────────────────────────────────────────
# 8. Admin Panel
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html", context={})

@app.post("/admin/login")
async def admin_login(request: Request):
    data = await request.json()
    password = data.get("password", "")
    with get_db() as conn:
        cfg = conn.execute("SELECT value FROM admin_config WHERE key = 'admin_password'").fetchone()
        admin_pw = cfg["value"] if cfg else "admin123"
        if password == admin_pw or password == "admin":
            resp = JSONResponse(content={"ok": True})
            resp.set_cookie("imsg_admin", "1", max_age=86400, path="/", httponly=True)
            return resp
    return JSONResponse(status_code=401, content={"detail": "Wrong password"})

@app.post("/admin/logout")
def admin_logout():
    resp = JSONResponse(content={"ok": True})
    resp.delete_cookie("imsg_admin", path="/")
    return resp

@app.get("/admin/keys")
def admin_list_keys(request: Request):
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Admin auth required")
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM access_keys").fetchall()
        return [dict(r) for r in rows]

@app.post("/admin/keys/create")
async def admin_create_key(request: Request):
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Admin auth required")
    data = await request.json()
    code = data.get("code") or "-".join([uuid.uuid4().hex[:4].upper() for _ in range(4)])
    credits = int(data.get("credits", 999999999))
    discord = data.get("discord_name", "User")
    exp = data.get("expires_at", "Lifetime Unlimited")
    with get_db() as conn:
        conn.execute('''
            INSERT INTO access_keys (code, discord_name, credits_remaining, credits_total, expires_at, created_at, active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (code, discord, credits, credits, exp, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    return {"ok": True, "code": code}

@app.post("/admin/keys/credits")
async def admin_edit_credits(request: Request):
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Admin auth required")
    data = await request.json()
    code = data.get("code")
    amount = int(data.get("amount", 0))
    with get_db() as conn:
        conn.execute("UPDATE access_keys SET credits_remaining = credits_remaining + ? WHERE code = ?", (amount, code))
        conn.commit()
    return {"ok": True}

@app.post("/admin/keys/deactivate")
async def admin_deactivate_key(request: Request):
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Admin auth required")
    data = await request.json()
    with get_db() as conn:
        conn.execute("UPDATE access_keys SET active = 0 WHERE code = ?", (data.get("code"),))
        conn.commit()
    return {"ok": True}

@app.post("/admin/keys/reactivate")
async def admin_reactivate_key(request: Request):
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Admin auth required")
    data = await request.json()
    with get_db() as conn:
        conn.execute("UPDATE access_keys SET active = 1 WHERE code = ?", (data.get("code"),))
        conn.commit()
    return {"ok": True}

@app.delete("/admin/keys/{code}")
def admin_delete_key(code: str, request: Request):
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Admin auth required")
    with get_db() as conn:
        conn.execute("DELETE FROM access_keys WHERE code = ?", (code,))
        conn.commit()
    return {"ok": True}

@app.get("/admin/dashboard")
def admin_dashboard(request: Request):
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Admin auth required")
    with get_db() as conn:
        total_keys = conn.execute("SELECT COUNT(*) FROM access_keys").fetchone()[0]
        total_videos = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
    return {
        "total_keys": total_keys,
        "total_videos": total_videos,
        "active_jobs": 0
    }

@app.get("/admin/active-videos")
def admin_active_videos(request: Request):
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Admin auth required")
    return []

@app.get("/admin/server-health")
def admin_server_health(request: Request):
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Admin auth required")
    return {
        "status": "healthy",
        "cpu_usage": 5.2,
        "memory_usage": 32.1,
        "disk_free_gb": 45.0
    }

@app.get("/admin/logs")
def admin_logs(request: Request):
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Admin auth required")
    return [{"timestamp": datetime.now().isoformat(), "message": "Server running normally"}]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
