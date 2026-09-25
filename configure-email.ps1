$ErrorActionPreference = 'Stop'
$projectPath = $PSScriptRoot
$envPath = Join-Path $projectPath '.env'

Write-Host 'Push email delivery setup' -ForegroundColor Cyan
Write-Host 'Use a Google App Password. Do not enter your normal Gmail password.' -ForegroundColor Yellow
$sender = (Read-Host 'Gmail address that will send Push verification codes').Trim()
if ($sender -notmatch '^[^@\s]+@[^@\s]+\.[^@\s]+$') {
    throw 'Enter a valid Gmail address.'
}

$securePassword = Read-Host 'Google App Password (input is hidden)' -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $appPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer).Replace(' ', '')
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
}
if ($appPassword.Length -lt 16) {
    throw 'The Google App Password is missing or too short.'
}

$values = [ordered]@{
    PUSH_EMAIL_HOST = 'smtp.gmail.com'
    PUSH_EMAIL_USER = $sender
    PUSH_EMAIL_PASSWORD = $appPassword
    PUSH_EMAIL_FROM = "Push <$sender>"
    PUSH_EMAIL_PORT = '587'
}
$lines = if (Test-Path -LiteralPath $envPath) { [Collections.Generic.List[string]](Get-Content -LiteralPath $envPath) } else { [Collections.Generic.List[string]]::new() }
foreach ($name in $values.Keys) {
    $replacement = "$name=$($values[$name])"
    $index = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match "^$([regex]::Escape($name))=") { $index = $i; break }
    }
    if ($index -ge 0) { $lines[$index] = $replacement } else { $lines.Add($replacement) }
}
$lines | Set-Content -LiteralPath $envPath -Encoding utf8
$appPassword = $null
Write-Host 'Email delivery is configured. Restart the Push preview server to activate it.' -ForegroundColor Green
