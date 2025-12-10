# Run tests reliably on Windows/OneDrive
Set-Location -LiteralPath ([Environment]::GetFolderPath('Desktop'))
Set-Location -LiteralPath 'PENNY STOCK TRADE'
python -m pytest tests

