$ErrorActionPreference = 'Stop'
$projectPath = $PSScriptRoot
$pythonCandidates = @(
    (Join-Path $projectPath '.runtime-venv/Scripts/python.exe'),
    ([System.IO.Path]::GetFullPath((Join-Path $projectPath '../../work/push-venv/Scripts/python.exe')))
)
$pythonPath = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $pythonPath) {
    throw 'Python environment missing. Follow the new-computer setup in README.md.'
}
if ($env:PUSH_ENV -eq 'production') {
    throw 'This script runs local development only. Use a separately configured production deployment.'
}
Push-Location -LiteralPath $projectPath
try {
    & $pythonPath manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) { throw 'Database setup failed.' }
    Write-Host 'Open http://127.0.0.1:8765/ . Stop the server with Ctrl+C.'
    & $pythonPath manage.py runserver 127.0.0.1:8765 --noreload
    if ($LASTEXITCODE -ne 0) { throw 'Server stopped with an error. Check whether the preview is already running.' }
} finally { Pop-Location }
