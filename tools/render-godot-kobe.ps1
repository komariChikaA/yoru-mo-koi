param(
    [ValidateSet('city', 'map', 'oblique', 'orbit', 'tour')]
    [string]$View = 'oblique',
    [ValidateSet('image', 'video')]
    [string]$Kind = 'image',
    [double]$Time = -1,
    [int]$Fps = 30,
    [double]$Seconds = 25.0,
    [double]$Start = 0,
    [string]$AudioPath = '',
    [ValidateSet('original', 'simple')]
    [string]$Buildings = 'original',
    [switch]$Hud
)
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$scenePath = Join-Path $workspace 'godot\kobe-map'
$outputPath = Join-Path $workspace '_preview\godot-kobe'
New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
$stem = $View
if ($Buildings -ne 'original') { $stem += '-buildings-' + $Buildings }
if ($Start -ne 0) { $stem += "-start" + $Start.ToString("0.00", [Globalization.CultureInfo]::InvariantCulture) }
if ($Time -ne -1) { $stem += '-t' + $Time.ToString('0.00', [Globalization.CultureInfo]::InvariantCulture) }
$extension = if ($Kind -eq 'video') { '.avi' } else { '.png' }
$moviePath = Join-Path $outputPath ($stem + $extension)
$frames = if ($Kind -eq 'video') { [int][math]::Ceiling($Fps * $Seconds) } else { 2 }
$userArgs = if ($View -eq 'tour') { '--tour' } else { '--view=' + $View }
$userArgs += ' --render'
if ($Buildings -ne 'original') { $userArgs += ' --buildings=' + $Buildings }
if ($View -eq 'tour' -and $Kind -eq 'video' -and $Time -eq -1) {
    # Movie Maker's first captured frame already represents the requested start.
    $tourClock = $Start
    $userArgs += ' --tour-start=' + $tourClock.ToString('R', [Globalization.CultureInfo]::InvariantCulture)
} elseif ($Start -ne 0) { $userArgs += ' --tour-start=' + $Start.ToString([Globalization.CultureInfo]::InvariantCulture) }
if ($Time -ne -1) { $userArgs += ' --time=' + $Time.ToString([Globalization.CultureInfo]::InvariantCulture) }
if (-not $Hud) { $userArgs += ' --no-hud' }
$argumentLine = '--path "' + $scenePath + '" --resolution 1920x1080 --rendering-driver vulkan --audio-driver Dummy --write-movie "' + $moviePath + '" --fixed-fps ' + $Fps + ' --quit-after ' + $frames + ' -- ' + $userArgs
$outLog = Join-Path $outputPath ($stem + '.log')
$errLog = Join-Path $outputPath ($stem + '-errors.log')
$executable = 'D:\software\Godot\4.7.2-stable\Godot_v4.7.2-stable_win64_console.exe'
$process = Start-Process -FilePath $executable -ArgumentList $argumentLine -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru
# Retain the process handle before it exits so Windows exposes its exit code.
$null = $process.Handle
$process.WaitForExit()
$errors = Get-Content -LiteralPath $errLog -Raw
if ($process.ExitCode -ne 0 -or $errors -match '(?m)^(SCRIPT ERROR|ERROR):') {
    throw "Godot rendering failed ($($process.ExitCode)): $errors"
}
if ($Kind -eq 'video') {
    $mp4Path = Join-Path $outputPath ($stem + '.mp4')
    & ffmpeg -hide_banner -loglevel error -y -i $moviePath -an -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart $mp4Path
    if ($LASTEXITCODE -ne 0) { throw 'FFmpeg encode failed' }
    if ($AudioPath) {
        if (-not (Test-Path -LiteralPath $AudioPath)) { throw 'Song audio file not found' }
        if ($View -ne 'tour') { throw 'Song audio sync is for the timed tour view' }
        $songPath = Join-Path $outputPath ($stem + '-song.mp4')
        $audioStart = (27.5 + $Start).ToString([Globalization.CultureInfo]::InvariantCulture)
        & ffmpeg -hide_banner -loglevel error -y -i $mp4Path -ss $audioStart -i $AudioPath -map 0:v:0 -map 1:a:0 -t $Seconds -c:v copy -c:a aac -b:a 192k -movflags +faststart $songPath
        if ($LASTEXITCODE -ne 0) { throw 'Song audio mux failed' }
        Write-Output $songPath
    }
    Write-Output $mp4Path
} else {
    Write-Output (Join-Path $outputPath ($stem + '00000001.png'))
}
Get-Content -LiteralPath $outLog | Select-String -Pattern 'Using Device|KOBE_SCENE_READY|frames at'
