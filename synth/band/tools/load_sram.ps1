param(
 [Parameter(Mandatory=$true)][string]$ReleaseDirectory,
 [string]$BitstreamName='starcluster_band.fs',
 [int]$Location=0,
 [int]$Channel=0,
 [string]$Programmer='D:\Gowin\Gowin_V1.9.12.03_x64\Programmer\bin\programmer_cli.exe'
)
$ErrorActionPreference='Stop'
$band=Split-Path $PSScriptRoot -Parent
$release=(Resolve-Path -LiteralPath $ReleaseDirectory).Path
if ([IO.Path]::GetFileName($BitstreamName) -ne $BitstreamName -or [IO.Path]::GetExtension($BitstreamName) -ne '.fs') {throw 'BitstreamName must be a local .fs filename'}
$bitstream=Join-Path $release $BitstreamName
$manifestPath=Join-Path $release 'manifest.json'
$manifest=Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$checkedRelease=Join-Path $band ('release/'+[IO.Path]::GetFileName($release))
if ((Resolve-Path -LiteralPath $checkedRelease).Path -ne $release) {throw 'Use a frozen local release directory'}
$projectRoot=Split-Path (Split-Path $band -Parent) -Parent
$python=Join-Path $projectRoot '.venv/Scripts/python.exe'
$preflight=& $python (Join-Path $PSScriptRoot 'load_flash.py') --release ([IO.Path]::GetFileName($release))
if ($LASTEXITCODE -ne 0) {throw 'Complete timing/source preflight failed; no USB access'}
if ($null -eq $manifest.setup_violations -or $null -eq $manifest.hold_violations -or $manifest.setup_violations -ne 0 -or $manifest.hold_violations -ne 0) {throw 'Missing clean timing evidence'}
if ((Get-FileHash -LiteralPath $bitstream -Algorithm SHA256).Hash -ne $manifest.bitstream_sha256) {throw 'Release hash mismatch'}
if (!(Test-Path -LiteralPath $Programmer)) {throw 'Set -Programmer to the installed Gowin programmer_cli.exe'}
$logDir=Join-Path $band ('evidence/program_'+(Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $logDir | Out-Null
function Invoke-BoundedProgrammer([string[]]$Arguments,[string]$Name,[int]$Seconds) {
 $stdout=Join-Path $logDir ($Name+'.out.txt');$stderr=Join-Path $logDir ($Name+'.err.txt')
 $process=Start-Process -FilePath $Programmer -ArgumentList $Arguments -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
 # Keep a process handle before waiting: Windows PowerShell otherwise can lose
 # ExitCode for a fast native process and mistake null for a failing exit code.
 $processHandle=$process.Handle
 if (!$process.WaitForExit($Seconds*1000)) {
  Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
  throw "USB operation timed out. Reconnect the download cable before retrying. Logs: $logDir"
 }
 $process.Refresh()
 $result=(Get-Content -LiteralPath $stdout -Raw -ErrorAction SilentlyContinue)+(Get-Content -LiteralPath $stderr -Raw -ErrorAction SilentlyContinue)
 if ($process.ExitCode -ne 0 -or $result -match '(?im)\b(error|failed|failure)\b') {throw "Programmer rejected operation, even if exit code was zero: $result"}
 return $result
}
$scan=Invoke-BoundedProgrammer @('--scan-cables','F') 'scan' 15
if ($scan -notmatch 'Cable found:') {throw 'No FTDI cable found'}
$probe=Invoke-BoundedProgrammer @('--device','GW5AST-138B','--run','0','--cable-index','4','--location',"$Location",'--channel',"$Channel") 'probe' 15
if ($probe -notmatch '(?i)(success|IDCODE|ID code)') {throw "No affirmative device-read result. Inspect $logDir"}
$quotedBitstream='"'+$bitstream+'"'
$result=Invoke-BoundedProgrammer @('--device','GW5AST-138B','--run','2','--fsFile',$quotedBitstream,'--cable-index','4','--location',"$Location",'--channel',"$Channel") 'sram' 90
if ($result -notmatch '(?i)success' -and !($result -match 'Programming[^\r\n]*100%' -and $result -match '(?m)^\s*Finished\.')) {throw "No affirmative SRAM completion. Inspect $logDir"}
Copy-Item -LiteralPath $manifestPath -Destination (Join-Path $logDir 'loaded_manifest.json')
Write-Output "SRAM loaded; Flash was not written. Run hardware_check.py with this release path. Logs: $logDir"
