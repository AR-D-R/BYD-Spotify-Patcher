$ErrorActionPreference = 'Stop'

Write-Host 'BYD Spotify Patcher v0.5.2 single-file portable Windows build'
Write-Host 'Android SDK / Android Studio are needed only on this BUILD PC.'
Write-Host 'The resulting BYDSpotifyPatcher.exe contains apksigner + a minimal Java runtime.'

$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Project

# 1) Locate the newest installed Android Build Tools and its AOSP apksigner JAR.
$SdkRoots = @()
if ($env:ANDROID_SDK_ROOT) { $SdkRoots += $env:ANDROID_SDK_ROOT }
if ($env:ANDROID_HOME) { $SdkRoots += $env:ANDROID_HOME }
if ($env:LOCALAPPDATA) { $SdkRoots += (Join-Path $env:LOCALAPPDATA 'Android\Sdk') }
$SdkRoots = $SdkRoots | Select-Object -Unique

$ApkSignerJar = $null
foreach ($sdk in $SdkRoots) {
    $bt = Join-Path $sdk 'build-tools'
    if (!(Test-Path $bt)) { continue }
    $versions = Get-ChildItem $bt -Directory | Sort-Object {
        try { [version](($_.Name -split '-')[0]) } catch { [version]'0.0.0' }
    } -Descending
    foreach ($v in $versions) {
        $candidate = Join-Path $v.FullName 'lib\apksigner.jar'
        if (Test-Path $candidate) { $ApkSignerJar = $candidate; break }
    }
    if ($ApkSignerJar) { break }
}
if (!$ApkSignerJar) {
    throw 'Could not find build-tools\<version>\lib\apksigner.jar. Install Android SDK Build Tools first.'
}
Write-Host "Using apksigner: $ApkSignerJar"

# 2) Locate a full JDK with jdeps + jlink + jmods.
# Android Studio JBR can contain java/jdeps/jlink but omit the jmods image needed
# by jlink, so prefer a normal JDK (Temurin 21 works well).
$JavaHomes = @()
if ($env:JAVA_HOME) { $JavaHomes += $env:JAVA_HOME }

$JdkRoots = @(
    'C:\Program Files\Eclipse Adoptium',
    'C:\Program Files\Microsoft',
    'C:\Program Files\Java'
)
foreach ($root in $JdkRoots) {
    if (Test-Path $root) {
        $JavaHomes += Get-ChildItem $root -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like 'jdk*' } |
            Sort-Object Name -Descending |
            ForEach-Object { $_.FullName }
    }
}

# Keep Android Studio locations as a last-resort candidate only if they are full
# enough to contain jmods\java.base.jmod.
$JavaHomes += 'C:\Program Files\Android\Android Studio\jbr'
$JavaHomes += 'C:\Program Files\Android\Android Studio\jre'
$JavaHomes = $JavaHomes | Select-Object -Unique

$JavaHome = $JavaHomes | Where-Object {
    (Test-Path (Join-Path $_ 'bin\java.exe')) -and
    (Test-Path (Join-Path $_ 'bin\jdeps.exe')) -and
    (Test-Path (Join-Path $_ 'bin\jlink.exe')) -and
    (Test-Path (Join-Path $_ 'jmods\java.base.jmod'))
} | Select-Object -First 1
if (!$JavaHome) {
    throw 'Could not find a full JDK with java.exe, jdeps.exe, jlink.exe and jmods\java.base.jmod. Install a full JDK (Temurin 21 recommended) or set JAVA_HOME to it.'
}
$Jdeps = Join-Path $JavaHome 'bin\jdeps.exe'
$Jlink = Join-Path $JavaHome 'bin\jlink.exe'
Write-Host "Using Java: $JavaHome"

# 3) Build a temporary minimal Java runtime for apksigner.
$Stage = Join-Path $Project '.portable_stage'
if (Test-Path $Stage) { Remove-Item $Stage -Recurse -Force }
$StageRuntime = Join-Path $Stage 'runtime'
$StageTools = Join-Path $Stage 'tools'
New-Item $StageTools -ItemType Directory -Force | Out-Null
Copy-Item $ApkSignerJar (Join-Path $StageTools 'apksigner.jar') -Force

$Modules = (& $Jdeps --ignore-missing-deps --print-module-deps $ApkSignerJar 2>$null)
if (!$Modules) { $Modules = 'java.base,java.logging,java.naming,java.xml' }
$ModuleList = (($Modules -split ',') + 'jdk.crypto.ec' | Sort-Object -Unique) -join ','
Write-Host "Java modules: $ModuleList"
& $Jlink `
  --add-modules $ModuleList `
  --output $StageRuntime `
  --strip-debug `
  --no-man-pages `
  --no-header-files `
  --compress=2
if ($LASTEXITCODE -ne 0) { throw 'jlink failed.' }

# Smoke-test the staged signing runtime before packaging it.
$StageJava = Join-Path $StageRuntime 'bin\java.exe'
$StageJar = Join-Path $StageTools 'apksigner.jar'
& $StageJava -jar $StageJar version
if ($LASTEXITCODE -ne 0) { throw 'Staged apksigner smoke test failed.' }

# 4) Build one self-contained EXE. PyInstaller extracts runtime/tools to _MEIPASS
#    while the program is running; the patcher already knows how to find them.
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
  --add-data "$StageRuntime;runtime" `
  --add-data "$StageJar;tools" `
  --add-data ".\THIRD_PARTY_NOTICES.md;." `
  .\byd_spotify_patcher.py

if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }

Remove-Item $Stage -Recurse -Force

Write-Host ''
Write-Host "Portable single-file build ready: $Project\dist\BYDSpotifyPatcher.exe"
Write-Host 'Target users need only this EXE and their own original Spotify 8.9.76.538 APK.'
Write-Host 'They do NOT need Android Studio, Android SDK, Java, apksigner, zipalign, or PowerShell.'
