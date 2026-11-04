@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "synth\tools\load_sram.ps1"
pause
