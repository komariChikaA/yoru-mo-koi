param([double]$Time = -1, [ValidateSet('simple','detail')][string]$SilhouetteStyle = 'simple')
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$scene = Join-Path $workspace 'godot/chorus-phone'
$output = Join-Path $workspace '_preview/chorus-photo-phone'
New-Item -ItemType Directory -Force -Path $output | Out-Null
$exe = 'D:\software\Godot\4.7.2-stable\Godot_v4.7.2-stable_win64_console.exe'
& python -X utf8 (Join-Path $PSScriptRoot 'build-chorus-phone.py')
if ($LASTEXITCODE -ne 0) { throw 'Chorus asset preparation failed' }
$importErrors = Join-Path $output 'import-errors.log'
$importProcess = Start-Process -FilePath $exe -ArgumentList ('--headless --editor --path "' + $scene + '" --import') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $output 'import.log') -RedirectStandardError $importErrors -PassThru
$null = $importProcess.Handle
$importProcess.WaitForExit()
if ($importProcess.ExitCode -ne 0 -or (Get-Content $importErrors -Raw) -match '(?m)^(SCRIPT ERROR|SHADER ERROR|ERROR):') { throw 'Godot import failed; see import-errors.log' }
$baseStem = if ($SilhouetteStyle -eq 'simple') { 'final' } else { 'final-detail' }
$stem = if ($Time -lt 0) { $baseStem } else { $baseStem + '-t' + $Time.ToString('0.000',[Globalization.CultureInfo]::InvariantCulture) }
$movie = Join-Path $output ($stem + $(if ($Time -lt 0) { '.avi' } else { '.png' }))
$frames = if ($Time -lt 0) { 225 } else { 3 }
$timeline = if ($Time -lt 0) { '--start=0' } else { '--time=' + $Time.ToString('R',[Globalization.CultureInfo]::InvariantCulture) }
$outLog = Join-Path $output ($stem + '.log')
$errLog = Join-Path $output ($stem + '-errors.log')
$arguments = '--path "' + $scene + '" --rendering-driver vulkan --audio-driver Dummy --write-movie "' + $movie + '" --fixed-fps 30 --quit-after ' + $frames + ' -- ' + $timeline + ' --capture-fps=30 --silhouette-style=' + $SilhouetteStyle
$process = Start-Process -FilePath $exe -ArgumentList $arguments -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru
$null = $process.Handle
$process.WaitForExit()
$errors = Get-Content -LiteralPath $errLog -Raw
if ($process.ExitCode -ne 0 -or $errors -match '(?m)^(SCRIPT ERROR|SHADER ERROR|ERROR):') {
    throw "Godot chorus rendering failed: $errors"
}
if ($Time -lt 0) {
    $review = Join-Path $output $(if ($SilhouetteStyle -eq 'simple') { 'Chorus-Photo-Phone-59.2-66.7-song.mp4' } else { 'Chorus-Photo-Phone-detail-59.2-66.7-song.mp4' })
    & python -X utf8 (Join-Path $PSScriptRoot 'build-chorus-phone.py') --install --style $SilhouetteStyle
    if ($LASTEXITCODE -ne 0) { throw 'Storybrew chorus frame installation failed' }
    Write-Output $review
} else {
    Write-Output (Join-Path $output ($stem + '00000002.png'))
}
