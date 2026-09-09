$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repository '.venv-ui\Scripts\python.exe'
$frontend = Join-Path $repository 'web\dist\index.html'

if (-not (Test-Path -LiteralPath $python)) {
    throw 'Visual editor environment is missing. Follow docs/visual_editor.md to install it.'
}
if (-not (Test-Path -LiteralPath $frontend)) {
    throw 'Visual editor build is missing. Run "npm install" and "npm run build" in the web directory.'
}

Set-Location -LiteralPath $repository
Write-Host 'Stock Pipeline Workflow Studio: http://127.0.0.1:8765' -ForegroundColor Green
Write-Host 'Press Ctrl+C to stop.' -ForegroundColor DarkGray
& $python visual_api.py
