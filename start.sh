#!/usr/bin/env bash
# ============================================================================
# Realtime Earth — macOS / Linux 启动器
# 委托给跨平台的 start.py
# ============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo
echo "=========================================================="
echo "  Realtime Earth - Starting up..."
echo "=========================================================="
echo

# 找 Python (优先 python3, 然后 python)
PY=""
for candidate in python3.12 python3.11 python3.13 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PY="$candidate"
        break
    fi
done

if [ -z "$PY" ]; then
    echo
    echo "[ERROR] Python not found on PATH."
    echo
    echo "Install Python 3.11+:"
    echo "  macOS:   brew install python@3.12"
    echo "  Ubuntu:  sudo apt install python3.12 python3.12-venv"
    echo "  Fedora:  sudo dnf install python3.12"
    echo
    exit 1
fi

exec "$PY" "$SCRIPT_DIR/start.py" "$@"
