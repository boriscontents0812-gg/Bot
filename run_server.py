import os
import sys

# Ensure site-packages from local .venv are loaded
base_dir = os.path.dirname(os.path.abspath(__file__))
venv_site = os.path.join(base_dir, ".venv", "Lib", "site-packages")
if os.path.exists(venv_site) and venv_site not in sys.path:
    sys.path.insert(0, venv_site)

import config
from config import HOST, PORT, DEFAULT_ACCESS_KEY

if __name__ == "__main__":
    import uvicorn
    reload_mode = "--reload" in sys.argv
    print("=" * 65)
    print(" [BOTYK STUDIO] Local Autonomous Server")
    print(f" - Local URL:  http://{HOST}:{PORT}")
    print(f" - Admin URL:  http://{HOST}:{PORT}/admin")
    print(f" - Default Key: {DEFAULT_ACCESS_KEY} (Unlimited Lifetime)")
    print(" - Mode: 100% Self-Hosted (Unlimited Credits)")
    print(" - Direct ElevenLabs TTS & Local FFmpeg Engine Active")
    print(f" - Reload: {'Enabled' if reload_mode else 'Disabled'}")
    print("=" * 65)
    uvicorn.run("server:app", host=HOST, port=PORT, reload=reload_mode)
