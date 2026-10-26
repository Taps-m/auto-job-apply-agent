@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Run Start Assistant.cmd first to install the project environment.
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" -m app.background
start "" "http://127.0.0.1:8765/#/applications"
