# Git add/commit/push helper
Param(
    [string]$Message = "Update"
)

$ErrorActionPreference = "Stop"

# Resolve repo root from script location
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot

git status -sb
git add -A
git commit -m $Message
git push

