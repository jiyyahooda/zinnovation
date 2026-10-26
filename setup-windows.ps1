param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv-windows\Scripts\python.exe')) {
    & $Python -m venv .venv-windows
    if ($LASTEXITCODE -ne 0) { throw 'Creating the Windows Python environment failed.' }
}
& '.\.venv-windows\Scripts\python.exe' -m pip install -r requirements-serving.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
Write-Host 'Windows environment ready. Existing macOS .venv is preserved and unused.'
Write-Host 'Frontend: cd frontend; pnpm install; pnpm build'
Write-Host 'Start: .\START-CIVICFLUX.cmd'
