param([switch]$SkipEngineStage)
$ErrorActionPreference = 'Stop'
$desktopRoot = Split-Path $PSScriptRoot -Parent
Push-Location $desktopRoot
try {
    $env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
    $sdk = Join-Path $desktopRoot '.build\dotnet\dotnet.exe'
    if (!(Test-Path -LiteralPath $sdk)) { $sdk = (Get-Command dotnet).Source }
    $python = Join-Path $desktopRoot '..\.venv\Scripts\python.exe'
    $bundle = Join-Path $desktopRoot 'artifacts\win-x64'
    if (!$SkipEngineStage -and !(Test-Path -LiteralPath "$bundle\engine")) {
        & $python scripts\prepare_engine.py --python-home .build\python\cpython-3.12.13-windows-x86_64-none --output "$bundle\engine"
        if ($LASTEXITCODE) { throw 'Engine staging failed' }
    }
    & $sdk publish src\Marker.Desktop -c Release -r win-x64 --self-contained true -o $bundle --nologo
    if ($LASTEXITCODE) { throw 'Desktop publish failed' }
    & $python scripts\build_wiki.py "$bundle\Wiki"
    if ($LASTEXITCODE) { throw 'Wiki build failed' }
    & $python scripts\manifest.py $bundle
    if ($LASTEXITCODE) { throw 'Manifest generation failed' }
    & $python scripts\build_msi.py $bundle .build\MarkerDesktop.wxs
    if ($LASTEXITCODE) { throw 'WiX source generation failed' }
    $wix = Join-Path $desktopRoot '.build\wix\wix.exe'
    if (!(Test-Path -LiteralPath $wix)) {
        & $sdk tool install wix --version 4.0.6 --tool-path .build\wix
        if ($LASTEXITCODE) { throw 'WiX installation failed' }
    }
    $release = Join-Path $desktopRoot 'artifacts\release'
    New-Item -ItemType Directory -Force -Path $release | Out-Null
    & $wix build .build\MarkerDesktop.wxs -arch x64 -cc .build\cab-cache -o "$release\MarkerDesktop-0.1.0-win-x64.msi"
    if ($LASTEXITCODE) { throw 'MSI build failed' }
    Get-FileHash -LiteralPath "$release\MarkerDesktop-0.1.0-win-x64.msi" -Algorithm SHA256 |
        ForEach-Object { "$($_.Hash.ToLower())  MarkerDesktop-0.1.0-win-x64.msi" } |
        Set-Content "$release\MarkerDesktop-0.1.0-win-x64.msi.sha256" -Encoding ascii
} finally { Pop-Location }
