@echo off
title Botyk - iMessage Video Generator
echo ========================================================
echo   Starting Botyk (iMessage Video Generator)
echo   Configuration loaded securely from .env
echo   Admin Panel: http://127.0.0.1:8000/admin
echo ========================================================
echo.

if not exist .venv (
    echo Creating virtual environment...
    C:\Users\%USERNAME%\.local\bin\uv.exe venv .venv --python 3.12
    C:\Users\%USERNAME%\.local\bin\uv.exe pip install --python .venv\Scripts\python.exe fastapi uvicorn jinja2 pillow python-multipart aiofiles httpx imageio-ffmpeg
)

start "" http://127.0.0.1:8000
.venv\Scripts\uvicorn.exe server:app --host 127.0.0.1 --port 8000 --reload
pause
