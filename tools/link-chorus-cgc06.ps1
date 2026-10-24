$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskOutput='../../工作文件夹/output/CGC06_scene3'
$taskPython='C:/Users/hiral/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$taskFfmpeg='D:/ffmpeg-7.0.2-essentials_build/bin/ffmpeg.exe'
$taskIncoming=Join-Path $taskRoot 'godot/chorus-phone/assets/incoming-cgc06.png'
& $taskFfmpeg -hide_banner -v error -y -i (Join-Path $taskOutput 'scene3.avi') -frames:v 1 $taskIncoming
if ($LASTEXITCODE -ne 0) {throw 'Cannot extract third-shot opening frame'}
Copy-Item -LiteralPath (Join-Path $taskRoot 'godot/chorus-cgc06/assets/e-overscan.png') -Destination (Join-Path $taskRoot 'godot/chorus-phone/assets/incoming-cgc06-overscan.png')
Copy-Item -LiteralPath (Join-Path $taskRoot 'godot/chorus-cgc06/closeup_motion.gd') -Destination (Join-Path $taskRoot 'godot/chorus-phone/assets/cgc06-motion.gd')
Copy-Item -LiteralPath (Join-Path $taskRoot 'godot/chorus-cgc06/atmosphere.gd') -Destination (Join-Path $taskRoot 'godot/chorus-phone/atmosphere.gd')
foreach ($taskAssetFolder in @('particles','frames')) {
    $taskAssetTarget=Join-Path $taskRoot ('godot/chorus-phone/assets/'+$taskAssetFolder)
    New-Item -ItemType Directory -Force -Path $taskAssetTarget | Out-Null
    if ($taskAssetFolder -eq 'particles') {
        Copy-Item -Path (Join-Path $taskRoot 'godot/chorus-cgc06/assets/particles/*.png') -Destination $taskAssetTarget
    } else {
        Copy-Item -LiteralPath (Join-Path $taskRoot 'godot/chorus-cgc06/assets/frames/white-rectangle.png') -Destination $taskAssetTarget
    }
}
$taskPreviousPath=$env:PATH
try {
    $env:PATH=(Split-Path $taskPython)+';'+(Split-Path $taskFfmpeg)+';'+$env:PATH
    & (Join-Path $PSScriptRoot 'render-godot-chorus-phone.ps1')
    & $taskPython -X utf8 (Join-Path $PSScriptRoot 'build-chorus-cgc06.py') --join-previous
    if ($LASTEXITCODE -ne 0) {throw 'Linked preview failed'}
} finally {$env:PATH=$taskPreviousPath}
