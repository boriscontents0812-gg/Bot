import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_dotenv(dotenv_path: str = None, override: bool = False) -> bool:
    """
    Lightweight, zero-dependency .env loader that populates os.environ.
    Handles quotes, comments, whitespace, and export prefixes.
    """
    if dotenv_path is None:
        dotenv_path = os.path.join(BASE_DIR, ".env")
    
    if not os.path.isfile(dotenv_path):
        return False

    try:
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[7:].strip()
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                # Strip matching surrounding quotes
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                if override or key not in os.environ:
                    os.environ[key] = val
        return True
    except Exception as e:
        print(f"Warning: Failed to load .env file: {e}")
        return False

# Automatically load .env on import
load_dotenv()

# Centralized Settings & Secrets
ELEVEN_API_KEY = os.environ.get("ELEVEN_API_KEY", "")
DEFAULT_ACCESS_KEY = os.environ.get("DEFAULT_ACCESS_KEY", "6C6W-K6LD-JRVV-QGTM")
DEFAULT_USERNAME = os.environ.get("DEFAULT_USERNAME", "mONSEY")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
UPSTREAM_BASE = os.environ.get("UPSTREAM_BASE", "https://botyk.app")
SESSION_COOKIE_NAME = os.environ.get("SESSION_COOKIE_NAME", "imsg_session")
SECRET_KEY = os.environ.get("SECRET_KEY", "botyk_secret_key_8f29d3b41c0e8a7192df6a3e")
HOST = os.environ.get("HOST", "127.0.0.1")
try:
    PORT = int(os.environ.get("PORT", "8000"))
except ValueError:
    PORT = 8000

# Directory paths
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    DATA_DIR = "/tmp/data"
else:
    DATA_DIR = os.path.join(BASE_DIR, "data")

DB_PATH = os.path.join(DATA_DIR, "botyk.db")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
