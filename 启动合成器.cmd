@echo off
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" "synth\host\app.py"
