@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>nul || (echo Python 3.12 or later is required. & pause & exit /b 1)
  echo First run: installing dependencies...
  py -m venv .venv || (pause & exit /b 1)
  ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || (pause & exit /b 1)
)
start "" "http://127.0.0.1:8765"
".venv\Scripts\python.exe" -m app.main
pause
