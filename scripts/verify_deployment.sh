#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Docker Compose =="
docker compose ps

echo "== Health =="
python3 - <<'PY'
import json, urllib.request
url='http://127.0.0.1:8000/api/v1/health'
with urllib.request.urlopen(url, timeout=10) as r:
    body=r.read().decode('utf-8')
    print(body)
    if r.status != 200:
        raise SystemExit(f'health status={r.status}')
PY

echo "== Persistent directories =="
test -d data
test -d backups
mkdir -p data/uploads backups

echo "Deployment verification passed."
