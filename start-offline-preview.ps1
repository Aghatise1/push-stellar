$ErrorActionPreference = 'Stop'
$projectPath = $PSScriptRoot
$pythonPath = [System.IO.Path]::GetFullPath((Join-Path $projectPath '../../work/push-venv/Scripts/python.exe'))

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'The Push Python environment is missing.'
}

$env:PUSH_DATABASE_URL = 'local'
Set-Location -LiteralPath $projectPath
& $pythonPath (Join-Path $projectPath 'manage.py') migrate --noinput
if ($LASTEXITCODE -ne 0) { throw 'Local preview database setup failed.' }
Write-Host 'Push local preview is running at http://127.0.0.1:8765/' -ForegroundColor Green
Write-Host 'Keep this window open. Press Ctrl+C when you want to stop the preview.'
& $pythonPath (Join-Path $projectPath 'manage.py') runserver 127.0.0.1:8765 --noreload
