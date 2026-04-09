param(
  [string]$RepoPath = "C:\Users\shiva\Downloads\Integrated-Management-Business-Suite",
  [string]$WSLDistro = "Ubuntu"
)

$ErrorActionPreference = "Stop"

$wslScript = @"
set -euo pipefail
export SITE_NAME=ibms.localhost
export ADMIN_PASSWORD=admin
export MYSQL_ROOT_PASSWORD=admin
export APPS_SRC=/mnt/c/Users/shiva/Downloads/Integrated-Management-Business-Suite/apps
cd /mnt/c/Users/shiva/Downloads/Integrated-Management-Business-Suite
chmod +x scripts/bootstrap-frappe-wsl.sh
./scripts/bootstrap-frappe-wsl.sh
"@

wsl -d $WSLDistro bash -lc $wslScript
Write-Host "Frappe bootstrap via WSL completed."
Write-Host "Start bench: wsl -d $WSLDistro bash -lc 'cd ~/frappe-bench && bench start'"
