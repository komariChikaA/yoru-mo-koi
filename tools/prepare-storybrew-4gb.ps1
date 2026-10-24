param(
    [string]$EditorDirectory = (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)))
)
$ErrorActionPreference = 'Stop'
if (-not [Environment]::Is64BitOperatingSystem) {
    throw 'The 4 GiB address space requires 64-bit Windows.'
}
$source = Join-Path $EditorDirectory 'StorybrewEditor.exe'
$destination = Join-Path $EditorDirectory 'StorybrewEditor-4GB.exe'
$bytes = [IO.File]::ReadAllBytes($source)
$peOffset = [BitConverter]::ToInt32($bytes, 0x3c)
if ([BitConverter]::ToUInt32($bytes, $peOffset) -ne 0x00004550 -or
    [BitConverter]::ToUInt16($bytes, $peOffset + 4) -ne 0x014c) {
    throw 'Expected the existing 32-bit Storybrew Windows launcher.'
}
# IMAGE_FILE_LARGE_ADDRESS_AWARE: 32-bit processes can use 4 GiB on 64-bit Windows.
# Keep the original launcher and all native DLLs unchanged.
$bytes[$peOffset + 22] = $bytes[$peOffset + 22] -bor 0x20
[IO.File]::WriteAllBytes($destination, $bytes)
Write-Output "Prepared: $destination"
Write-Output 'Save and close Storybrew, then open this launcher to use the larger address space.'
