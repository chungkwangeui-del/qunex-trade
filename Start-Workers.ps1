# QunexTrade Agent Control Center
# Double-click this file or run in PowerShell

$Host.UI.RawUI.WindowTitle = "QunexTrade - Agent Control Center"

# Navigate to project directory
Set-Location $PSScriptRoot

# Show welcome screen
python -m agents.cli welcome

Write-Host ""
Write-Host "Press ENTER to start workers, or close this window to exit..." -ForegroundColor Yellow
Read-Host

# Start workers
python -m agents.cli work


