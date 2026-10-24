param([double]$Time=-1,[int]$Puppet=0,[switch]$SkipPrepare,[switch]$NoInstall,[switch]$HideHair,[double]$Strength=1,[double]$BlinkSpeed=1)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskProject=Join-Path $taskRoot 'godot/chorus-four'
$taskOut='../../工作文件夹/output/CGC14-15_scene4'
$taskGodot='D:/software/Godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
$taskPython='C:/Python312/python.exe'
New-Item -ItemType Directory -Force -Path $taskOut | Out-Null
if (-not $SkipPrepare) {
    & $taskPython -X utf8 (Join-Path $PSScriptRoot 'build-chorus-four.py')
    if ($LASTEXITCODE -ne 0) {throw 'Shot four preparation failed'}
}
$taskProc=Start-Process -FilePath $taskGodot -ArgumentList ('--headless --editor --path "'+$taskProject+'" --import --quit') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskOut 'import.log') -RedirectStandardError (Join-Path $taskOut 'import-errors.log') -PassThru
$null=$taskProc.Handle;$taskProc.WaitForExit()
if ($taskProc.ExitCode -ne 0 -or (Get-Content (Join-Path $taskOut 'import-errors.log') -Raw) -match '(?m)^(SCRIPT ERROR|SHADER ERROR|ERROR):') {throw 'Godot import failed'}
$taskStem=if ($Puppet -gt 0) {'puppet'+$Puppet} else {'scene4'}
if ($HideHair) {$taskStem+='-hidden'}
if ($BlinkSpeed -ne 1) {$taskStem+='-slow'}
if ($Strength -eq 0) {$taskStem+='-rest'}
elseif ($Strength -ne 1) {$taskStem+='-strength-'+$Strength.ToString('0.###',[Globalization.CultureInfo]::InvariantCulture)}
if ($Time -ge 0) {$taskStem+='-'+$Time.ToString('0.000',[Globalization.CultureInfo]::InvariantCulture)}
$taskFrames=if ($Time -ge 0) {4} elseif ($Puppet -eq 14) {336} elseif ($Puppet -eq 15) {552} else {420}
$taskMovie=Join-Path $taskOut ($taskStem+$(if ($Time -ge 0) {'.png'} else {'.avi'}))
$taskArgs='--path "'+$taskProject+'" --resolution 1920x1080 --audio-driver Dummy --write-movie "'+$taskMovie+'" --fixed-fps 60 -- --render --frames='+$taskFrames+' --strength='+$Strength.ToString('R',[Globalization.CultureInfo]::InvariantCulture)
if ($BlinkSpeed -ne 1) {$taskArgs+=' --blink-speed='+$BlinkSpeed.ToString('R',[Globalization.CultureInfo]::InvariantCulture)}
if ($Puppet -gt 0) {$taskArgs+=' --puppet'+$Puppet}
if ($HideHair) {$taskArgs+=' --hide-hair'}
if ($Time -ge 0) {$taskArgs+=' --time='+$Time.ToString('R',[Globalization.CultureInfo]::InvariantCulture)}
$taskProc=Start-Process -FilePath $taskGodot -ArgumentList $taskArgs -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskOut ($taskStem+'.log')) -RedirectStandardError (Join-Path $taskOut ($taskStem+'-errors.log')) -PassThru
$null=$taskProc.Handle;$taskProc.WaitForExit()
if ($taskProc.ExitCode -ne 0 -or (Get-Content (Join-Path $taskOut ($taskStem+'-errors.log')) -Raw) -match '(?m)^(SCRIPT ERROR|SHADER ERROR|ERROR):') {throw 'Godot capture failed'}
$taskRecorded=[regex]::Match((Get-Content -LiteralPath (Join-Path $taskOut ($taskStem+'.log')) -Raw),'(?m)^(\d+) frames at')
if (-not $taskRecorded.Success -or [int]$taskRecorded.Groups[1].Value -lt $taskFrames) {
    throw "Godot captured fewer than $taskFrames frames; incomplete movie was not installed"
}
if ($Puppet -eq 0 -and $Time -lt 0 -and -not $NoInstall) {
    & $taskPython -X utf8 (Join-Path $PSScriptRoot 'build-chorus-four.py') --install
    if ($LASTEXITCODE -ne 0) {throw 'Shot four installation failed'}
}
Write-Output $taskMovie
