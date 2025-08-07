# Script to automatically add Claude API snippets to Cursor
Write-Host "Installing Claude API snippets to Cursor..." -ForegroundColor Green

# Path to Cursor settings file
$cursorSettingsPath = "$env:APPDATA\Cursor\User\settings.json"

# Check if Cursor is installed
if (-not (Test-Path $cursorSettingsPath)) {
    Write-Host "ERROR: Cursor settings file not found at: $cursorSettingsPath" -ForegroundColor Red
    Write-Host "Make sure Cursor is installed and has been run at least once." -ForegroundColor Yellow
    exit 1
}

# Create backup
$backupPath = "$cursorSettingsPath.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item $cursorSettingsPath $backupPath
Write-Host "Backup created: $backupPath" -ForegroundColor Green

# Load current settings
try {
    $settings = Get-Content $cursorSettingsPath -Raw | ConvertFrom-Json
} catch {
    Write-Host "ERROR: Failed to load Cursor settings" -ForegroundColor Red
    Write-Host "Restoring backup..." -ForegroundColor Yellow
    Copy-Item $backupPath $cursorSettingsPath
    exit 1
}

# Snippets to add
$claudeTestBody = @'
$headers = @{
    "Content-Type" = "application/json"
    "Authorization" = "Bearer ${1:YOUR_API_KEY}"
}

$body = @{
    "messages" = @(
        @{
            "role" = "system"
            "content" = "${2:You are a helpful assistant.}"
        },
        @{
            "role" = "user"
            "content" = "${3:Your message here}"
        }
    )
    "max_tokens" = ${4:100}
    "model" = "${5:claude-3-sonnet-20240229}"
} | ConvertTo-Json

try {
    $response = Invoke-WebRequest -Uri "https://api.anthropic.com/v1/messages" -Method Post -Headers $headers -Body $body
    $response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Error: $($_.Exception.Message)"
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Error details: $responseBody"
    }
}
'@

$claudeSimpleBody = @'
$headers = @{
    "Content-Type" = "application/json"
    "Authorization" = "Bearer ${1:YOUR_API_KEY}"
}

$body = @{
    "messages" = @(
        @{
            "role" = "user"
            "content" = "${2:Your message}"
        }
    )
    "max_tokens" = 100
    "model" = "claude-3-sonnet-20240229"
} | ConvertTo-Json

Invoke-WebRequest -Uri "https://api.anthropic.com/v1/messages" -Method Post -Headers $headers -Body $body
'@

# Add snippets to settings
if (-not $settings.snippets) {
    $settings | Add-Member -MemberType NoteProperty -Name "snippets" -Value @{}
}

# Add Claude API Test snippet
$settings.snippets["Claude API Test"] = @{
    "prefix" = "claude-test"
    "body" = $claudeTestBody -split "`n"
    "description" = "Test Claude API in PowerShell"
}

# Add Claude API Simple snippet
$settings.snippets["Claude API Simple"] = @{
    "prefix" = "claude-simple"
    "body" = $claudeSimpleBody -split "`n"
    "description" = "Simple Claude API test"
}

Write-Host "Added snippet: Claude API Test" -ForegroundColor Green
Write-Host "Added snippet: Claude API Simple" -ForegroundColor Green

# Save settings
try {
    $settings | ConvertTo-Json -Depth 10 | Set-Content $cursorSettingsPath -Encoding UTF8
    Write-Host "SUCCESS: Snippets have been added to Cursor!" -ForegroundColor Green
    Write-Host ""
    Write-Host "How to use:" -ForegroundColor Cyan
    Write-Host "1. Open a .ps1 file in Cursor" -ForegroundColor White
    Write-Host "2. Type 'claude-test' or 'claude-simple'" -ForegroundColor White
    Write-Host "3. Press Tab" -ForegroundColor White
    Write-Host "4. Fill in the placeholders" -ForegroundColor White
    Write-Host ""
    Write-Host "WARNING: Replace YOUR_API_KEY with your actual API key!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Restart Cursor for changes to take effect." -ForegroundColor Cyan
} catch {
    Write-Host "ERROR: Failed to save settings" -ForegroundColor Red
    Write-Host "Restoring backup..." -ForegroundColor Yellow
    Copy-Item $backupPath $cursorSettingsPath
    exit 1
} 