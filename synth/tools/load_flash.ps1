param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$python = Join-Path $root '.venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $python)) { throw 'Project Python environment is missing.' }
$loader = Join-Path $root 'synth/band/tools/load_flash.py'
if ($CheckOnly) { & $python $loader } else { & $python $loader --execute }
if ($LASTEXITCODE -ne 0) { throw 'Flash operation failed. Inspect synth/band/evidence/flash_program_*; do not assume boot is ready.' }
