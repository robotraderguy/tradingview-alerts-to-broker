# Render CLI installer (Windows). Called by bootstrap.bat / bootstrap.ps1.
#
# Render publishes no winget or npm package, so this pulls the official binary
# from the vendor's own GitHub releases. The one non-obvious bit: the .exe inside
# the zip is VERSION-STAMPED (cli_vX.Y.Z.exe), so it must be renamed to
# render.exe or nothing will ever find it on PATH.
$ErrorActionPreference = 'Stop'

if (Get-Command render -ErrorAction SilentlyContinue) {
    Write-Host '  [OK] already installed.' -ForegroundColor Green
    exit 0
}

$ver  = (Invoke-RestMethod 'https://api.github.com/repos/render-oss/cli/releases/latest').tag_name.TrimStart('v')
$arch = if ([Environment]::Is64BitOperatingSystem) { 'amd64' } else { '386' }
$url  = 'https://github.com/render-oss/cli/releases/download/v' + $ver + '/cli_' + $ver + '_windows_' + $arch + '.zip'
$zip  = Join-Path $env:TEMP 'render-cli.zip'
$dest = Join-Path $env:LOCALAPPDATA 'Programs\render'

Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Expand-Archive -Path $zip -DestinationPath $dest -Force
Remove-Item $zip -Force -ErrorAction SilentlyContinue

$stamped = Get-ChildItem $dest -Filter 'cli_v*.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($stamped) { Move-Item $stamped.FullName (Join-Path $dest 'render.exe') -Force }
if (-not (Test-Path (Join-Path $dest 'render.exe'))) { throw 'render.exe not found after extracting' }

# Put it on the USER PATH (no admin needed, no desktop icon).
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($userPath -notlike "*$dest*") {
    [Environment]::SetEnvironmentVariable('Path', "$userPath;$dest", 'User')
}
Write-Host "  [OK] Render CLI $ver installed to $dest - open a NEW terminal to use it." -ForegroundColor Green
