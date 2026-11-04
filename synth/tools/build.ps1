$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location -LiteralPath $root
$gowin = 'D:\Gowin\Gowin_V1.9.12.03_x64\IDE\bin\gw_sh.exe'
& $gowin 'synth/build.tcl' 2>&1 | Tee-Object -FilePath 'synth/build.log'
if ($LASTEXITCODE -ne 0) { throw 'Gowin build failed. See synth/build.log.' }
$timing = Get-Content -LiteralPath 'synth/impl/pnr/aurora_synth_tr_content.html' -Raw
foreach ($kind in @('Setup', 'Hold')) {
    $pattern = 'Numbers of ' + $kind + ' Violated Endpoints</td>\s*<td>(\d+)</td>'
    if ($timing -notmatch $pattern) { throw "Cannot confirm $kind timing from PnR report." }
    if ([int]$Matches[1] -ne 0) { throw "$kind timing violations: refusing to publish bitstream." }
}
New-Item -ItemType Directory -Force -Path 'synth/release' | Out-Null
if (Test-Path -LiteralPath 'synth/release/aurora_synth.fs') {
    (Get-Item -LiteralPath 'synth/release/aurora_synth.fs').IsReadOnly = $false
}
Copy-Item -LiteralPath 'synth/impl/pnr/aurora_synth.fs' -Destination 'synth/release/aurora_synth.fs' -Force
Write-Host 'Build complete: synth/release/aurora_synth.fs'
