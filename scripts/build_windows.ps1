param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$AppName = "LocalTranscriber"
$EntryPoint = Join-Path $ProjectRoot "src\local_transcriber\gui.py"

function Invoke-Checked {
    param(
        [string]$Label,
        [scriptblock]$Command
    )

    Write-Host $Label
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

Set-Location $ProjectRoot

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

Invoke-Checked "Upgrading pip..." { & $VenvPython -m pip install --upgrade pip }
Invoke-Checked "Installing dependencies..." { & $VenvPython -m pip install -r requirements.txt -r requirements-dev.txt }

if ($Clean) {
    Write-Host "Cleaning previous build outputs..."
    if (Test-Path ".\build") { Remove-Item ".\build" -Recurse -Force }
    if (Test-Path ".\dist") { Remove-Item ".\dist" -Recurse -Force }
}

Invoke-Checked "Building $AppName..." { & $VenvPython -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name $AppName `
    --paths ".\src" `
    --collect-all faster_whisper `
    --collect-all ctranslate2 `
    $EntryPoint }

Write-Host ""
Write-Host "Build complete:"
Write-Host "  $ProjectRoot\dist\$AppName\$AppName.exe"
