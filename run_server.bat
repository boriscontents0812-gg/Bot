@echo off
title Gengar Studio Local Server
cd /d "%~dp0"
set "UV_PY=%APPDATA%\uv\python\cpython-3.12-windows-x86_64-none\python.exe"

if exist "%UV_PY%" (
    "%UV_PY%" run_server.py
) else (
    python run_server.py
)
pause
