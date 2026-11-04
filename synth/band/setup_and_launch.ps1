$ErrorActionPreference='Stop'
$projectRoot=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$python=Join-Path $projectRoot '.venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $python)) {
 & py -3.11 -m venv (Join-Path $projectRoot '.venv')
 if ($LASTEXITCODE -ne 0) {throw 'Install Python 3.11 with the Windows py launcher, then run again.'}
}
& $python -m pip install -r (Join-Path $PSScriptRoot 'requirements-host.txt')
if ($LASTEXITCODE -ne 0) {throw 'Dependency installation failed; see the installer output.'}
& $python (Join-Path $PSScriptRoot 'host/app.py')
