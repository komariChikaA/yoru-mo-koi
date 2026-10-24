param([double]$Time=-1,[switch]$SkipPrepare,[switch]$NoInstall)
$ErrorActionPreference='Stop'
$taskWorkspace=Split-Path -Parent $PSScriptRoot
$taskProject=Join-Path $taskWorkspace 'godot/chorus-cgc06'
$taskOutput='../../工作文件夹/output/CGC06_scene3'
$taskPython='C:/Users/hiral/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$taskGodot='D:/software/Godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
New-Item -ItemType Directory -Force -Path $taskOutput | Out-Null
if (-not $SkipPrepare) {
    & $taskPython -X utf8 (Join-Path $PSScriptRoot 'build-chorus-cgc06.py')
    if ($LASTEXITCODE -ne 0) {throw 'CGC06 asset preparation failed'}
}
& $taskPython -X utf8 (Join-Path $PSScriptRoot 'build-chorus-cgc06-particles.py')
if ($LASTEXITCODE -ne 0) {throw 'CGC06 particle preparation failed'}
$taskImport=Start-Process -FilePath $taskGodot -ArgumentList ('--headless --editor --path "'+$taskProject+'" --import --quit') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskOutput 'import.log') -RedirectStandardError (Join-Path $taskOutput 'import-errors.log') -PassThru
$null=$taskImport.Handle
$taskImport.WaitForExit()
if ($taskImport.ExitCode -ne 0 -or (Get-Content -LiteralPath (Join-Path $taskOutput 'import-errors.log') -Raw) -match '(?m)^(SCRIPT ERROR|SHADER ERROR|ERROR):') {throw 'Godot import failed'}
$taskStem=if ($Time -lt 0) {'scene3'} else {'still-'+$Time.ToString('0.000',[Globalization.CultureInfo]::InvariantCulture)}
$taskMovie=Join-Path $taskOutput ($taskStem+$(if ($Time -lt 0) {'.avi'} else {'.png'}))
$taskFrames=if ($Time -lt 0) {378} else {4}
# scene.gd exits after its capture counter reaches --frames. Engine iterations
# can outpace that counter during startup, so --quit-after can truncate a movie.
$taskArguments='--path "'+$taskProject+'" --resolution 1920x1080 --audio-driver Dummy --write-movie "'+$taskMovie+'" --fixed-fps 60 -- --render --fps=60 --frames='+$taskFrames
if ($Time -ge 0) {$taskArguments+=' --time='+$Time.ToString('R',[Globalization.CultureInfo]::InvariantCulture)}
$taskProcess=Start-Process -FilePath $taskGodot -ArgumentList $taskArguments -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskOutput ($taskStem+'.log')) -RedirectStandardError (Join-Path $taskOutput ($taskStem+'-errors.log')) -PassThru
$null=$taskProcess.Handle
$taskProcess.WaitForExit()
$taskErrors=Get-Content -LiteralPath (Join-Path $taskOutput ($taskStem+'-errors.log')) -Raw
if ($taskProcess.ExitCode -ne 0 -or $taskErrors -match '(?m)^(SCRIPT ERROR|SHADER ERROR|ERROR):') {throw "Render failed: $taskErrors"}
$taskRecorded=[regex]::Match((Get-Content -LiteralPath (Join-Path $taskOutput ($taskStem+'.log')) -Raw),'(?m)^(\d+) frames at')
if (-not $taskRecorded.Success -or [int]$taskRecorded.Groups[1].Value -lt $taskFrames) {
    throw "Godot ended before rendering all $taskFrames requested frames; incomplete capture was not installed"
}
if ($Time -lt 0) {
    if (-not $NoInstall) {
        & $taskPython -X utf8 (Join-Path $PSScriptRoot 'build-chorus-cgc06.py') --install
        if ($LASTEXITCODE -ne 0) {throw 'CGC06 installation failed'}
    }
} else {Write-Output (Join-Path $taskOutput ($taskStem+'00000003.png'))}
Get-Content -LiteralPath (Join-Path $taskOutput ($taskStem+'.log')) | Select-String 'Using Device|SCENE3_READY|frames at'
