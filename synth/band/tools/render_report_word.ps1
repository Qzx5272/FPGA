param([Parameter(Mandatory=$true)][string]$Document,[Parameter(Mandatory=$true)][string]$Pdf)
$ErrorActionPreference='Stop'
if (Get-Process WINWORD -ErrorAction SilentlyContinue) {throw 'Word is already open; use the standard document renderer or close the owned review instance first.'}
$inputPath=(Resolve-Path -LiteralPath $Document).Path
$outputPath=[IO.Path]::GetFullPath($Pdf)
$word=$null
$opened=$null
try {
 $word=New-Object -ComObject Word.Application
 $word.Visible=$false
 $word.DisplayAlerts=0
 $opened=$word.Documents.Open($inputPath,$false,$true)
 $opened.ExportAsFixedFormat($outputPath,17)
 $opened.Close(0)
 $opened=$null
 if (!(Test-Path -LiteralPath $outputPath)) {throw 'Word did not create the PDF'}
 Write-Output $outputPath
} finally {
 if ($null -ne $opened) {try {$opened.Close(0)} catch {}}
 if ($null -ne $word) {try {$word.Quit()} catch {Write-Warning 'Word COM quit returned an error; PDF existence is checked separately.'}}
}
