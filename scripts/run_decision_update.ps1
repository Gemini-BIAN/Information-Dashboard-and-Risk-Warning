# Example only: no background task is registered by this script.
param([string]$Python = ".\.venv\Scripts\python.exe")
$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepositoryRoot
& $Python -m scm.platform.cli update --output-dir runtime/platform/updates
# Exit2 means completed with one or more source failures; inspect update.json.
exit $LASTEXITCODE
