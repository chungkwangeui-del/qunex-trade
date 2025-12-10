# Health check against local server (/api/status)
Set-Location -LiteralPath ([Environment]::GetFolderPath('Desktop'))
Set-Location -LiteralPath 'PENNY STOCK TRADE'

try {
    $resp = curl.exe -s http://localhost:5000/api/status
    if (-not $resp) {
        Write-Host "No response. Is the server running?" -ForegroundColor Yellow
        exit 1
    }
    Write-Host $resp
} catch {
    Write-Host "Health check failed: $_" -ForegroundColor Red
    exit 1
}

