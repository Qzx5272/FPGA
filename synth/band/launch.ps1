$ErrorActionPreference='Stop'
$projectRoot=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$python=Join-Path $projectRoot '.venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $python)) {
 throw 'Create a Python 3.11 virtual environment in the project root: py -3.11 -m venv .venv ; then install synth/band/requirements-host.txt'
}
& $python (Join-Path $PSScriptRoot 'host/app.py') --workstation --muted @args
