param([string]$ProjectPath='../..')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskProject=(Resolve-Path -LiteralPath $ProjectPath).Path
$taskFiles=@('ChorusFiveEnding.cs','.sbrew/effect.51e051e051e051e051e051e051e051e0.yaml',
    'tools/prepare-storybrew-ending.py','tools/prepare-ending-title.py','tools/install-storybrew-ending.ps1',
    'godot/chorus-five/ending.json','godot/chorus-five/timeline.json','godot/chorus-five/scene.gd',
    'godot/chorus-five/ending-title.gd','godot/chorus-five/export-ending-titles.gd',
    'docs/storybrew-ending.md','docs/five-heroine-ending.md')
foreach($taskFile in $taskFiles){
    $taskFrom=Join-Path $taskRoot $taskFile
    $taskTo=Join-Path $taskProject $taskFile
    if([IO.Path]::GetFullPath($taskFrom) -ne [IO.Path]::GetFullPath($taskTo)){
        Copy-Item -LiteralPath $taskFrom -Destination $taskTo -Force
    }
}
# Append only the six new layers. Existing production WIP and layer order stay.
$taskIndexPath=Join-Path $taskProject '.sbrew/index.yaml'
$taskIndex=[IO.File]::ReadAllText($taskIndexPath)
foreach($taskSuffix in 1..6){
    $taskId='51e051e051e051e051e051e051e051e'+$taskSuffix
    if(-not $taskIndex.Contains($taskId)){$taskIndex=$taskIndex.TrimEnd()+"`n  - `"$taskId`"`n"}
}
[IO.File]::WriteAllText($taskIndexPath,$taskIndex,[Text.UTF8Encoding]::new($false))
Write-Output ('Installed native Storybrew ending: '+$taskProject)
Write-Output 'Mapset assets: sb/ending/ (prepare-storybrew-ending.py)'
