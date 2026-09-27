# Botyk — iMessage & WhatsApp Video Generator

A complete, high-fidelity recreation of [botyk.app](https://botyk.app/) — the viral iMessage and WhatsApp conversation video generator with ElevenLabs TTS, realistic bubble rendering, gameplay backgrounds, and vertical 9:16 export.

---

## ⚡ Quick Start

Run via npm or double-click `run.bat`:

```bash
npm run dev
```

Or run directly via python / uvicorn:

```bash
.venv\Scripts\python.exe run_server.py --reload
```

Then navigate to: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

### 🔐 Environment Configuration (`.env`)
All API keys, secrets, and environment parameters are centralized in `.env` (with a template in `.env.example`).
- **`ELEVEN_API_KEY`**: Your ElevenLabs API key for AI text-to-speech voice generation.
- **`DEFAULT_ACCESS_KEY`**: The default lifetime access key code.
- **`ADMIN_PASSWORD`**: Admin panel password for `/admin`.
- **`UPSTREAM_BASE`**: Upstream server URL.
- **`SESSION_COOKIE_NAME`**: Session cookie name.
- **`HOST` & `PORT`**: Server host and port binding.

---


## 📱 Features

1. **Exact Botyk Landing Page (`/`)**:
   - Floating 3D 3-phone mockup with Apple island notch and realistic shadows.
   - Dynamic live ticker banner (ElevenLabs TTS, Gameplay Backgrounds, 1080p Export, Rizz Mode).
   - Social proof metrics (12K+ videos, 340M+ views, 99% viral rate).
   - Features grid with high-resolution Apple emojis.
   - Pricing cards (Starter, Standard with 15% discount badge, Pro with 20% discount badge).
   - Access Key input (`XXXX-XXXX-XXXX-XXXX`) with instant verification and redirect.
   - Interactive 4-video looping demo carousel (Subway Surfers, GTA, Minecraft gameplay backgrounds).
   - 10-second limited offer modal (Claim 100 free credits via Discord).

2. **Studio Web Application (Full App)**:
   - **Dual Platform Styles**:
     - **iOS iMessage Mode**: Blue outgoing bubbles, grey incoming bubbles, camera icon, chevron, timestamps, contact avatar.
     - **WhatsApp Mode**: Dark/light themes, dark green outgoing bubbles, dark grey incoming bubbles, WhatsApp wallpaper background, online status, phone and video call icons.
   - **Complete UI Controls**:
     - Light & Dark mode toggle for both app interface and phone canvas.
     - Sliders: Bubble Scale, Font Size, Max Bubble Width %, Min Bubble Width, Bubble Gap, Line Spacing, Messages Per Page, Chat Y Offset, Container Scale, Corner Radius.
     - Switches: Rounded corners, Persistent Header, Header Gradient, Unread Badge, Bubble Fade + Intensity, Group Fade, Notification Sound, Container Shadow, Music Fade Out, End Fade Out.
   - **Live Script Editor**:
     - Fast syntax parser (`1:Name> text`, `2:Name> text`, `2: img: image_name`, `wing`, `rizz`, `plug`).
     - Real-time debounced preview (`POST /preview/{page}`) returning exact 9:16 vertical chroma-green frames with pagination.
   - **ElevenLabs Voice Settings & TTS**:
     - ElevenLabs profiles manager (Multilingual v2, Turbo v2.5, Flash v2.5).
     - Stability, Similarity, Audio Speed, and TTS Speed controls.
     - Quota monitor (`/api/eleven_quota`).
     - In-browser audio player with waveform scrubber and single-clip regenerator (`/api/regenerate_clip`).
     - Update Audio mode (only generates new lines to save credits).
   - **Video Rendering Engine**:
     - FFmpeg-powered vertical 1080x1920 video generator (`POST /api/generate_video`).
     - Chroma keying of chat frames over gameplay backgrounds.
     - Audio mixer blending dialogue voiceovers with background music and notification SFX.
     - Real-time progress bar with live polling (`/api/video_progress`).
     - Auto-shorten / manual shorten to 2:59 (`/api/shorten`).
   - **Media Management**:
     - Custom contact avatar uploader per character.
     - Script image bubbles uploader.
     - Gameplay video library and uploader.
     - Background music library and uploader.
   - **Projects**:
     - Create, save, auto-save, load, and delete projects.
     - Pre-loaded with 5 projects: `Promo`, `23`, `w`, `Goated`, `1`.

3. **Admin Panel (`/admin`)**:
   - Access key generator and inspector.
   - Add/edit credit balances.
   - Activate, deactivate, extend, or delete keys.
   - Server health metrics and video generation logs.

---

## 🏗️ Architecture

```
d:\Github\Bot\
├── server.py              # FastAPI server (all 62 routes)
├── config.py              # Centralized settings & environment loader
├── db.py                  # SQLite database & data seeding
├── renderer.py            # PIL chat preview renderer (iOS & WhatsApp)
├── audio_generator.py     # ElevenLabs & synthetic audio engine
├── video_generator.py     # FFmpeg video compositing & encoding
├── run_server.py          # Server runner with reload support & diagnostics
├── run.bat                # 1-click startup batch script
├── verify_all.py          # Quick runner for test suites
├── tests/                 # Automated test suite
│   ├── test_api.py        # 15-test API & auth verification suite
│   └── test_pipeline.py   # End-to-end rendering pipeline integration test
├── templates/
│   ├── landing.html       # Exact Botyk public landing page
│   ├── app.html           # Full Studio web application
│   └── admin.html         # Admin panel interface
├── assets/
│   ├── favicon.png
│   ├── og_preview.png
│   ├── phone_preview.png
│   ├── phone_preview2.png
│   ├── phone_preview3.jpg
│   └── demo/
│       ├── demo1.mp4
│       ├── demo2.mp4
│       ├── demo3.mp4
│       └── demo4.mp4
└── data/                  # Persistent SQLite database and user media
```
