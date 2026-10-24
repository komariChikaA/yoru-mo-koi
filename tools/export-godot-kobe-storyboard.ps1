param(
    [string]$MapsetPath = '',
    [string]$GodotPath = 'D:\software\Godot\4.7.2-stable\Godot_v4.7.2-stable_win64_console.exe',
    [ValidateSet(540, 720, 1080)] [int]$Height = 540,
    [ValidateSet('original', 'simple')] [string]$Buildings = 'simple'
)
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
if (-not $MapsetPath) {
    $userConfig = Get-Content -LiteralPath (Join-Path $workspace '.sbrew/user.yaml') -Encoding UTF8 -Raw
    if ($userConfig -notmatch '(?m)^MapsetPath:\s*"([^"]+)"') {
        throw 'Pass -MapsetPath or configure the Storybrew project mapset first.'
    }
    $MapsetPath = $Matches[1]
}
if (-not (Test-Path -LiteralPath $MapsetPath -PathType Container)) { throw 'Mapset directory does not exist.' }
if (-not (Test-Path -LiteralPath $GodotPath -PathType Leaf)) { throw 'Godot executable does not exist.' }
Get-Command ffmpeg -ErrorAction Stop | Out-Null

$fps = 24
$start = 26600
$end = 40000
$frameCount = [int][Math]::Ceiling(($end - $start) * $fps / 1000.0)
$captureDir = Join-Path $workspace '_preview/godot-kobe/sequence24'
$frameFolder = if ($Buildings -eq 'simple') { 'sb/kobe3d-simple' } else { 'sb/kobe3d' }
$frameDir = Join-Path $MapsetPath $frameFolder
New-Item -ItemType Directory -Path $captureDir, $frameDir -Force | Out-Null
$moviePath = Join-Path $captureDir 'tour24.avi'
$outLog = Join-Path $captureDir 'godot.log'
$errLog = Join-Path $captureDir 'godot-errors.log'
$scenePath = Join-Path $workspace 'godot/kobe-map'
# Movie Maker calls _process before its first capture. Offset by one fixed delta
# so frame 0 samples song 26.600, frame 321 samples 39.975, and Bridge owns 40s.
$offset = (($start - 27500) / 1000.0 - 1.0 / $fps).ToString('R', [Globalization.CultureInfo]::InvariantCulture)
$arguments = '--path "' + $scenePath + '" --resolution 1920x1080 --rendering-driver vulkan --audio-driver Dummy --write-movie "' + $moviePath + '" --fixed-fps ' + $fps + ' --quit-after ' + $frameCount + ' -- --tour --render --no-hud --tour-start=' + $offset
if ($Buildings -eq 'simple') { $arguments += ' --buildings=simple' }
Write-Output "Rendering $frameCount frames at $fps fps (26.60-40s)..."
$process = Start-Process -FilePath $GodotPath -ArgumentList $arguments -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru
$null = $process.Handle
$process.WaitForExit()
$errors = Get-Content -LiteralPath $errLog -Raw
if ($process.ExitCode -ne 0 -or $errors -match '(?m)^(SCRIPT ERROR|ERROR):') { throw "Godot render failed: $errors" }
$width = [int]($Height * 16 / 9)
& ffmpeg -hide_banner -loglevel error -y -i $moviePath -map 0:v:0 -vf "scale=${width}:${Height}:flags=lanczos" -fps_mode passthrough -frames:v $frameCount -start_number 0 (Join-Path $frameDir 'frame-%04d.png')
if ($LASTEXITCODE -ne 0) { throw 'PNG sequence extraction failed.' }

$timeline = [Collections.Generic.List[string]]::new()
for ($i = 0; $i -lt $frameCount; $i++) {
    $file = 'frame-{0:D4}.png' -f $i
    if (-not (Test-Path -LiteralPath (Join-Path $frameDir $file) -PathType Leaf)) { throw "Missing frame: $file" }
    $from = [int][Math]::Round($start + $i * 1000.0 / $fps)
    $to = [int][Math]::Min($end, [Math]::Round($start + ($i + 1) * 1000.0 / $fps))
    $timeline.Add("$from`t$to`t$file`t$Height")
}
$utf8 = [Text.UTF8Encoding]::new($false)
[IO.File]::WriteAllLines((Join-Path $frameDir 'timeline.tsv'), $timeline, $utf8)

# Select the installed sequence only after every frame and the timeline are ready.
$effectPath = Join-Path $workspace '.sbrew/effect.32e4ca649d2e4c4caa0b27e86d713924.yaml'
$effectConfig = [IO.File]::ReadAllText($effectPath)
$effectConfig = [Regex]::Replace($effectConfig, '(?m)^(    Value: )"sb/kobe3d(?:-simple)?/timeline\.tsv"', '$1"' + $frameFolder + '/timeline.tsv"')
[IO.File]::WriteAllText($effectPath, $effectConfig, $utf8)

# Add this effect's layer once, preserving every existing layer and its order.
$indexPath = Join-Path $workspace '.sbrew/index.yaml'
$layerId = '821b2d592742488bb83863a18dbfd018'
$index = [IO.File]::ReadAllText($indexPath)
if ($index -notmatch [Regex]::Escape($layerId)) {
    $indexBytes = [IO.File]::ReadAllBytes($indexPath)
    $hasBom = $indexBytes.Length -ge 3 -and $indexBytes[0] -eq 239 -and $indexBytes[1] -eq 187 -and $indexBytes[2] -eq 191
    $indexEncoding = [Text.UTF8Encoding]::new($hasBom)
    [IO.File]::WriteAllText($indexPath, $index.TrimEnd() + "`n  - `"$layerId`"`n", $indexEncoding)
}
Write-Output "Ready: $frameCount PNGs and timeline in $frameDir"
Write-Output 'Storybrew effect: Godot Kobe 3D 26.60-40s / 24fps (Kobe3D).'
Get-Content -LiteralPath $outLog | Select-String -Pattern 'Using Device|frames at'
