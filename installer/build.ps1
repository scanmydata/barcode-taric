# Build local installer: (1) venv+deps, (2) icon, (3) PyInstaller, (4) Inno Setup.
# Χρήση: powershell -ExecutionPolicy Bypass -File installer\build.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "== 1/4 Εγκατάσταση dependencies ==" -ForegroundColor Cyan
if (-not (Test-Path ".venv")) { python -m venv .venv }
$py = Join-Path $Root ".venv\Scripts\python.exe"
& $py -m pip install --upgrade pip
& $py -m pip install -e ".[gui]"
& $py -m pip install pyinstaller

Write-Host "== 2/4 Δημιουργία icon ==" -ForegroundColor Cyan
& $py installer\make_icon.py

Write-Host "== 3/4 PyInstaller (one-dir bundle) ==" -ForegroundColor Cyan
if (Test-Path "dist\BarcodeTaric") { Remove-Item -Recurse -Force "dist\BarcodeTaric" }
& $py -m PyInstaller --noconfirm --clean installer\barcodetaric.spec

Write-Host "== 4/4 Inno Setup ==" -ForegroundColor Cyan
$iscc = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    Write-Warning "Δεν βρέθηκε Inno Setup 6 (ISCC.exe). Εγκατάσταση: winget install JRSoftware.InnoSetup"
    Write-Host "Το frozen app βρίσκεται στο dist\BarcodeTaric\BarcodeTaric.exe" -ForegroundColor Yellow
    exit 0
}
& $iscc installer\barcodetaric.iss
Write-Host "Έτοιμο. Installer: dist\installer\BarcodeTaric-0.1.0-setup.exe" -ForegroundColor Green
