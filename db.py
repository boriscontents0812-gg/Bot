import sqlite3
import os
import json
import time
import shutil

import config
from config import BASE_DIR, DATA_DIR, DB_PATH, DEFAULT_ACCESS_KEY, DEFAULT_USERNAME, ADMIN_PASSWORD, ELEVEN_API_KEY

if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    os.makedirs(DATA_DIR, exist_ok=True)
    src_db = os.path.join(BASE_DIR, "data", "botyk.db")
    if not os.path.exists(DB_PATH) and os.path.exists(src_db):
        try:
            shutil.copyfile(src_db, DB_PATH)
        except Exception:
            pass

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    except Exception:
        pass
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS access_keys (
                code TEXT PRIMARY KEY,
                discord_name TEXT NOT NULL,
                credits_remaining INTEGER NOT NULL,
                credits_total INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                voice_model TEXT DEFAULT 'eleven_multilingual_v2',
                voice_stability REAL DEFAULT 0.25,
                voice_similarity REAL DEFAULT 0.70,
                voice_tts_speed REAL DEFAULT 1.0,
                voice_audio_speed REAL DEFAULT 1.15,
                voice_language TEXT DEFAULT 'en',
                eleven_key TEXT DEFAULT ''
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS eleven_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_code TEXT NOT NULL,
                name TEXT NOT NULL,
                api_key TEXT NOT NULL,
                created_at TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 0,
                UNIQUE(key_code, name)
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                key_code TEXT NOT NULL,
                name TEXT NOT NULL,
                data TEXT NOT NULL,
                style TEXT DEFAULT 'ios',
                created_at REAL NOT NULL,
                PRIMARY KEY (key_code, name)
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS media_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_code TEXT NOT NULL,
                category TEXT NOT NULL,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                created_at REAL NOT NULL,
                UNIQUE(key_code, category, filename)
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                token TEXT PRIMARY KEY,
                key_code TEXT NOT NULL,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                duration_s REAL NOT NULL,
                created_at REAL NOT NULL
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS admin_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')

        conn.execute('''
            INSERT INTO admin_config (key, value) VALUES ('admin_password', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        ''', (ADMIN_PASSWORD,))

        # Unlimited credits for DEFAULT_ACCESS_KEY
        conn.execute('''
            INSERT INTO access_keys (
                code, discord_name, credits_remaining, credits_total, expires_at, created_at, active, eleven_key
            ) VALUES (
                ?, ?, 999999999, 999999999, 'Lifetime Unlimited', '2026-09-09 23:22:31', 1, ?
            )
            ON CONFLICT(code) DO UPDATE SET
                credits_remaining = 999999999,
                credits_total = 999999999,
                expires_at = 'Lifetime Unlimited',
                eleven_key = CASE WHEN (eleven_key = '' OR eleven_key IS NULL) AND ? != '' THEN ? ELSE eleven_key END
        ''', (DEFAULT_ACCESS_KEY, DEFAULT_USERNAME, ELEVEN_API_KEY, ELEVEN_API_KEY, ELEVEN_API_KEY))

        if ELEVEN_API_KEY:
            conn.execute('''
                INSERT OR IGNORE INTO eleven_profiles (
                    key_code, name, api_key, created_at, active
                ) VALUES (
                    ?, 'default', ?, '2026-09-19 06:13:22', 1
                )
            ''', (DEFAULT_ACCESS_KEY, ELEVEN_API_KEY))

        conn.commit()

if __name__ == '__main__':
    init_db()
    print("Database updated with Unlimited Credits.")
