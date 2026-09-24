import os
import sys

# Ensure site-packages from local .venv are loaded
base_dir = os.path.dirname(os.path.abspath(__file__))
venv_site = os.path.join(base_dir, ".venv", "Lib", "site-packages")
if os.path.exists(venv_site) and venv_site not in sys.path:
    sys.path.insert(0, venv_site)

if __name__ == "__main__":
    import uvicorn
    print("=" * 65)
    print(" [GENGAR STUDIO] Local Autonomous Server")
    print(" - Local URL: http://127.0.0.1:8000")
    print(" - Default Key: 6C6W-K6LD-JRVV-QGTM (Unlimited Lifetime)")
    print(" - Mode: 100% Self-Hosted (No third-party botyk credits needed)")
    print(" - Max Duration: 8 Minutes (480 Seconds)")
    print(" - Direct ElevenLabs TTS & Local GPU/CPU FFmpeg Engine Active")
    print("=" * 65)
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
