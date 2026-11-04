param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$python = Join-Path $root '.venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $python)) { throw 'Project Python environment is missing.' }
# This offline gate validates the selected image without accessing USB.
$preflight = & $python (Join-Path $root 'synth/band/tools/load_flash.py')
if ($LASTEXITCODE -ne 0) { throw 'Selected release preflight failed; no SRAM programming attempted.' }
$verified = ($preflight -join "`n") | ConvertFrom-Json
if ($CheckOnly) { $preflight; return }
$release = Join-Path $root ('synth/band/release/' + $verified.release)
& (Join-Path $root 'synth/band/tools/load_sram.ps1') -ReleaseDirectory $release
