@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Project Python environment is missing. See synth\band\README.txt.
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "synth\band\host\app.py" --port COM12 --workstation --muted %*
