param(
    [ValidateSet('CGC14_a', 'CGC14_b', 'CGC14_c', 'CGC15_c', 'CGC16')]
    [string]$Shot = 'CGC14_a',
    [double]$Seconds = 6.0,
    [int]$Fps = 60,
    [double]$Intensity = 1.0,
    [double]$Time = -1.0,
    [switch]$Original,
    [string]$Suffix = '-layered',
    [switch]$HideHair,
    [switch]$HairOnly,
    [switch]$EyesOnly,
    [double]$Blink = -1.0
)
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$projectPath = Join-Path $workspace 'godot\cg-puppet'
$outputPath = Join-Path $workspace '_preview\cg-puppet'
New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
$stem = $Shot + $Suffix
if ($Original) { $Intensity = 0; $stem += '-original' }
if ($Time -ge 0) { $stem += '-t' + $Time.ToString('0.000', [Globalization.CultureInfo]::InvariantCulture) }
$moviePath = Join-Path $outputPath ($stem + $(if ($Time -ge 0) { '.png' } else { '.avi' }))
$frames = if ($Time -ge 0) { 2 } else { [int][math]::Round($Seconds * $Fps) }
$arguments = '--path "' + $projectPath + '" --resolution 1280x720 --audio-driver Dummy --write-movie "' + $moviePath + '" --fixed-fps ' + $Fps + ' --quit-after ' + ($frames + 600) + ' -- --render --shot=' + $Shot + ' --fps=' + $Fps + ' --frames=' + $frames + ' --intensity=' + $Intensity.ToString([Globalization.CultureInfo]::InvariantCulture)
if ($Time -ge 0) { $arguments += ' --time=' + $Time.ToString([Globalization.CultureInfo]::InvariantCulture) }
if ($HideHair) { $arguments += ' --hide-hair' }
if ($HairOnly) { $arguments += ' --hair-only' }
if ($EyesOnly) { $arguments += ' --eyes-only' }
if ($Blink -ge 0) { $arguments += ' --blink=' + $Blink.ToString([Globalization.CultureInfo]::InvariantCulture) }
$outLog = Join-Path $outputPath ($stem + '.log')
$errLog = Join-Path $outputPath ($stem + '-errors.log')
$executable = 'D:\software\Godot\4.7.2-stable\Godot_v4.7.2-stable_win64_console.exe'
$process = Start-Process -FilePath $executable -ArgumentList $arguments -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru
$null = $process.Handle
$process.WaitForExit()
$errors = Get-Content -LiteralPath $errLog -Raw
if ($process.ExitCode -ne 0 -or $errors -match '(?m)^(SCRIPT ERROR|ERROR|SHADER ERROR):') {
    throw "Godot rendering failed ($($process.ExitCode)): $errors"
}
if ($Time -lt 0) {
    $mp4Path = Join-Path $outputPath ($stem + '.mp4')
    & ffmpeg -hide_banner -loglevel error -y -i $moviePath -frames:v $frames -an -c:v libx264 -crf 16 -pix_fmt yuv420p -movflags +faststart $mp4Path
    if ($LASTEXITCODE -ne 0) { throw 'FFmpeg encode failed' }
    & ffmpeg -hide_banner -loglevel error -i $mp4Path -f null -
    if ($LASTEXITCODE -ne 0) { throw 'FFmpeg full decode failed' }
    $frameCount = & ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1:nokey=1 $mp4Path
    if ($LASTEXITCODE -ne 0 -or [int]$frameCount -ne $frames) { throw "Unexpected captured frame count: $frameCount (expected $frames)" }
    # Exact file generated above; no recursive deletion or computed tree cleanup.
    Remove-Item -LiteralPath $moviePath
    Write-Output $mp4Path
} else {
    Write-Output (Join-Path $outputPath ($stem + '00000001.png'))
}
Get-Content -LiteralPath $outLog | Select-String -Pattern 'Using Device|CG_PUPPET_READY|frames at'
