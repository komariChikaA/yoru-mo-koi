param([double]$Time=-1,[int]$Fps=60,[switch]$SkipPrepare,[double]$Lighting=1,[double]$Petals=1,[double]$Hair=1,[int]$HairVisible=1,[double]$Hand=1,[string]$Suffix='',[double]$StartSong=-1)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskProject=Join-Path $taskRoot 'godot/chorus-five'
$taskTimeline=Get-Content -LiteralPath (Join-Path $taskProject 'timeline.json') -Raw | ConvertFrom-Json
$taskSongStart=[double]$taskTimeline.song_start
if($StartSong -ge 0){$taskSongStart=$StartSong}
$taskSongEnd=[double]$taskTimeline.song_end
$taskDuration=$taskSongEnd-$taskSongStart
$taskRange=$taskSongStart.ToString('0.000',[Globalization.CultureInfo]::InvariantCulture)+'-'+$taskSongEnd.ToString('0.000',[Globalization.CultureInfo]::InvariantCulture)
$taskOut='../../工作文件夹/output/CGC16_scene5'
$taskGodot='D:/software/Godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
New-Item -ItemType Directory -Force -Path $taskOut | Out-Null
if(-not $SkipPrepare){
    & 'C:/Python312/python.exe' -X utf8 (Join-Path $PSScriptRoot 'prepare-chorus-five.py')
    if($LASTEXITCODE -ne 0){throw 'CGC16 preparation failed'}
    & 'C:/Python312/python.exe' -X utf8 (Join-Path $PSScriptRoot 'prepare-heroine-ending.py')
    if($LASTEXITCODE -ne 0){throw 'Ending portrait preparation failed'}
    & 'C:/Python312/python.exe' -X utf8 (Join-Path $PSScriptRoot 'prepare-ending-title.py')
    if($LASTEXITCODE -ne 0){throw 'Ending title preparation failed'}
}
function Invoke-SceneGodot([string]$Arguments,[string]$Stem){
    $taskLog=Join-Path $taskOut ($Stem+'.log')
    $taskErrors=Join-Path $taskOut ($Stem+'-errors.log')
    $taskProc=Start-Process -FilePath $taskGodot -ArgumentList $Arguments -WindowStyle Hidden -RedirectStandardOutput $taskLog -RedirectStandardError $taskErrors -PassThru
    $null=$taskProc.Handle
    $taskProc.WaitForExit()
    if($taskProc.ExitCode -ne 0 -or (Get-Content -LiteralPath $taskErrors -Raw) -match '(?m)^(SCRIPT ERROR|SHADER ERROR|ERROR):'){throw "Godot failed: $taskErrors"}
}
Invoke-SceneGodot ('--headless --editor --path "'+$taskProject+'" --import --quit') 'import'
$taskStem='scene5'+$Suffix
if($Time -ge 0){$taskStem+='-'+$Time.ToString('0.000',[Globalization.CultureInfo]::InvariantCulture)}
$taskFrames=if($Time -ge 0){3}else{[int][Math]::Round($taskDuration*$Fps)}
$taskMovie=Join-Path $taskOut ($taskStem+$(if($Time -ge 0){'.png'}else{'.avi'}))
$taskArgs='--path "'+$taskProject+'" --resolution 1920x1080 --audio-driver Dummy --write-movie "'+$taskMovie+'" --fixed-fps '+$Fps+' -- --render --frames='+$taskFrames+' --fps='+$Fps+' --lighting='+$Lighting.ToString('R',[Globalization.CultureInfo]::InvariantCulture)+' --petals='+$Petals.ToString('R',[Globalization.CultureInfo]::InvariantCulture)
$taskArgs+=' --hair='+$Hair.ToString('R',[Globalization.CultureInfo]::InvariantCulture)+' --hair-visible='+$HairVisible
$taskArgs+=' --hand='+$Hand.ToString('R',[Globalization.CultureInfo]::InvariantCulture)
$taskArgs+=' --start-time='+($taskSongStart-[double]$taskTimeline.song_start).ToString('R',[Globalization.CultureInfo]::InvariantCulture)
if($Time -ge 0){$taskArgs+=' --time='+$Time.ToString('R',[Globalization.CultureInfo]::InvariantCulture)}
Invoke-SceneGodot $taskArgs $taskStem
if($Time -lt 0){
    $taskOutput=Join-Path $taskOut ('第五分镜-场景预览-'+$taskRange+$Suffix+'.mp4')
    $taskAudio=Join-Path '../..' '夜もすがら君想ふ-短剪通透平衡版.wav'
    # Native capture frame zero is already the first requested pose. Keep it;
    # MovieWriter's extra final frame is excluded by the requested frame count.
    $taskVideoFilter='trim=end_frame='+$taskFrames+',setpts=PTS-STARTPTS'
    & ffmpeg -hide_banner -loglevel warning -y -i $taskMovie -ss $taskSongStart.ToString('R',[Globalization.CultureInfo]::InvariantCulture) -i $taskAudio -map 0:v:0 -map 1:a:0 -vf $taskVideoFilter -r $Fps -fps_mode cfr -frames:v $taskFrames -t $taskDuration.ToString('0.000',[Globalization.CultureInfo]::InvariantCulture) -c:v libx264 -crf 17 -preset medium -pix_fmt yuv420p -c:a aac -b:a 256k -movflags +faststart $taskOutput
    if($LASTEXITCODE -ne 0){throw 'Preview encoding failed'}
    Write-Output $taskOutput
}else{
    $taskPng=Get-ChildItem -LiteralPath $taskOut -Filter ($taskStem+'*.png') | Where-Object {$_.Name -match ([regex]::Escape($taskStem)+'\d{8}\.png$')} | Sort-Object Name | Select-Object -Skip 1 -First 1
    if(-not $taskPng){throw 'Godot PNG capture missing'}
    Copy-Item -LiteralPath $taskPng.FullName -Destination $taskMovie -Force
    Write-Output $taskMovie
}
