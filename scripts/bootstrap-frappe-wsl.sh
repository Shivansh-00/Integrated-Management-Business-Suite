#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a local Frappe Bench in WSL2 for IMBS.
# Usage:
#   SITE_NAME=imbs.localhost ADMIN_PASSWORD=admin MYSQL_ROOT_PASSWORD=admin ./scripts/bootstrap-frappe-wsl.sh

: "${SITE_NAME:=imbs.localhost}"
: "${ADMIN_PASSWORD:=admin}"
: "${MYSQL_ROOT_PASSWORD:=admin}"
: "${BENCH_DIR:=$HOME/frappe-bench}"
: "${APPS_SRC:=/mnt/c/Users/shiva/Downloads/Integrated-Management-Business-Suite/apps}"

sudo apt-get update
sudo apt-get install -y git python3-dev python3-venv python3-pip redis-server mariadb-server libmariadb-dev pkg-config npm nodejs

python3 -m pip install --upgrade pip
python3 -m pip install frappe-bench

if [[ ! -d "$BENCH_DIR" ]]; then
  bench init "$BENCH_DIR" --frappe-branch version-15
fi

cd "$BENCH_DIR"

if [[ ! -d "apps/imbs_core" ]]; then
  ln -s "$APPS_SRC/imbs_core" "$BENCH_DIR/apps/imbs_core"
fi

if ! bench --site "$SITE_NAME" list-apps >/dev/null 2>&1; then
  bench new-site "$SITE_NAME" --admin-password "$ADMIN_PASSWORD" --mariadb-root-password "$MYSQL_ROOT_PASSWORD"
fi

bench --site "$SITE_NAME" install-app imbs_core || true
bench --site "$SITE_NAME" set-config imbs_jwt_secret "replace-in-prod-$(date +%s)"
bench use "$SITE_NAME"

echo "Bootstrap completed."
echo "Run: cd $BENCH_DIR && bench start"
