$ErrorActionPreference = 'Stop'

$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Project

py -m pip install --upgrade pyinstaller cryptography pillow

if (Test-Path '.\build') { Remove-Item '.\build' -Recurse -Force }
if (Test-Path '.\dist\BYDSpotifyPatcher.exe') { Remove-Item '.\dist\BYDSpotifyPatcher.exe' -Force }

py -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name BYDSpotifyPatcher `
  --collect-all cryptography `
  --collect-all PIL `
  .\byd_spotify_patcher.py

Write-Host "Built development EXE: $PWD\dist\BYDSpotifyPatcher.exe"
Write-Host 'This development EXE still uses a locally installed Android SDK/Java for APK signing.'
Write-Host 'For a single-file self-contained public build, use build_portable_windows.ps1 instead.'
