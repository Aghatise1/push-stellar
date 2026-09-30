$ErrorActionPreference = 'Stop'
$projectPath = $PSScriptRoot
$envPath = Join-Path $projectPath '.env'

Write-Host 'Push Brevo email delivery setup' -ForegroundColor Cyan
Write-Host 'Create a Brevo transactional API key and verify the sender before continuing.' -ForegroundColor Yellow
$sender = (Read-Host 'Verified sender email address').Trim()
if ($sender -notmatch '^[^@\s]+@[^@\s]+\.[^@\s]+$') {
    throw 'Enter a valid verified sender address.'
}

$secureApiKey = Read-Host 'Brevo API key (input is hidden)' -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureApiKey)
try {
    $apiKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer).Trim()
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
}
if ($apiKey.Length -lt 20) {
    throw 'The Brevo API key is missing or too short.'
}

$values = [ordered]@{
    PUSH_BREVO_API_KEY = $apiKey
    PUSH_EMAIL_FROM = "Push <$sender>"
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
$apiKey = $null
Write-Host 'Brevo HTTPS email delivery is configured. Restart the Push preview server to activate it.' -ForegroundColor Green
