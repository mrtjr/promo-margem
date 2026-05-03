# Build do backend Python via PyInstaller.
# Pré-requisito: venv criado e dependências instaladas.
#   python -m venv .venv
#   .\.venv\Scripts\pip install -r requirements.txt
# Output final: ..\resources\backend\promomargem-backend\

$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
  Write-Host "[backend] activating venv..." -ForegroundColor Cyan
  if (-not (Test-Path .\.venv\Scripts\Activate.ps1)) {
    Write-Error "venv nao encontrado em .\.venv. Rode: python -m venv .venv && .\.venv\Scripts\pip install -r requirements.txt"
  }
  & .\.venv\Scripts\Activate.ps1

  Write-Host "[backend] cleaning previous build..." -ForegroundColor Cyan
  Remove-Item -Recurse -Force .\dist, .\build -ErrorAction SilentlyContinue

  Write-Host "[backend] running pyinstaller..." -ForegroundColor Cyan
  pyinstaller promomargem.spec --noconfirm --clean

  $target = Join-Path $PSScriptRoot "..\resources\backend"
  Write-Host "[backend] copying to $target ..." -ForegroundColor Cyan
  if (Test-Path $target) { Remove-Item -Recurse -Force $target }
  New-Item -ItemType Directory -Force -Path $target | Out-Null
  Copy-Item -Recurse -Force .\dist\promomargem-backend\* $target

  $size = (Get-ChildItem $target -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
  Write-Host ("[backend] done. Output: {0} ({1:N1} MB)" -f $target, $size) -ForegroundColor Green
} finally {
  Pop-Location
}
