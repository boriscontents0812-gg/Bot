@echo off
title Botyk - iMessage Video Generator
cd /d "%~dp0"

echo ========================================================
echo   Starting Botyk (iMessage Video Generator)
echo   Configuration loaded securely from .env
echo   Admin Panel: http://127.0.0.1:8000/admin
echo ========================================================
echo.

if not exist .venv (
    echo [Setup] Creating virtual environment...
    where uv >nul 2>nul
    if %errorlevel% equ 0 (
        uv venv .venv
        uv pip install -r requirements.txt --python .venv\Scripts\python.exe
    ) else if exist "%USERPROFILE%\.local\bin\uv.exe" (
        "%USERPROFILE%\.local\bin\uv.exe" venv .venv
        "%USERPROFILE%\.local\bin\uv.exe" pip install -r requirements.txt --python .venv\Scripts\python.exe
    ) else (
        python -m venv .venv
        .venv\Scripts\pip.exe install -r requirements.txt
    )
)

start "" http://127.0.0.1:8000

if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe run_server.py --reload
) else (
    python run_server.py --reload
)
pause
