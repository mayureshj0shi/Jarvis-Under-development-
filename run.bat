@echo off
cd /d F:\Jarvis
call .venv\Scripts\activate.bat
if "%1"=="api" (
    python run_api.py
) else (
    python main.py %*
)
pause
