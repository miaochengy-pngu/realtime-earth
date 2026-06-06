"""Cross-platform starter for Realtime Earth.

Run:
    python start.py            # Windows / macOS / Linux
    py start.py                # Windows launcher fallback

What it does:
    1. Finds a Python >= 3.11 on PATH.
    2. Creates backend/.venv (idempotent) using the project-local Python.
    3. pip install -e backend/ into the venv (idempotent — skips if already done).
    4. Copies backend/.env.example to backend/.env if missing.
    5. Kills any process still bound to PORT (default 8000).
    6. Runs uvicorn in the foreground — API + built frontend in one process.

Open:
    http://localhost:8000         -- 3D globe
    http://localhost:8000/docs    -- FastAPI Swagger
    http://localhost:8000/healthz -- per-source status
    ws://localhost:8000/ws        -- real-time push channel
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
import time
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
VENV = BACKEND / ".venv"
PORT = int(os.environ.get("REALTIME_EARTH_PORT", "8000"))
MIN_PY = (3, 11)


# ---------------------------------------------------------------------------
# 1. Find a usable Python
# ---------------------------------------------------------------------------
def find_python() -> str:
    """Return the path of a Python >= 3.11. Prefer the one matching sys.executable
    so a venv can re-invoke itself correctly; fall back to PATH lookups."""
    candidates: list[str] = []
    # 1. The interpreter that's running this script
    if Path(sys.executable).name.lower().startswith("python"):
        candidates.append(sys.executable)
    # 2. Standard names on PATH
    for name in ("python3.12", "python3.11", "python3.13", "python3",
                 "python", "py"):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    # Dedupe, keep order
    seen: set[str] = set()
    ordered = []
    for c in candidates:
        c = str(Path(c).resolve())
        if c not in seen:
            seen.add(c)
            ordered.append(c)
    for cand in ordered:
        try:
            out = subprocess.run(
                [cand, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                capture_output=True, text=True, timeout=10, check=True,
            ).stdout.strip()
            major, minor = (int(x) for x in out.split("."))
            if (major, minor) >= MIN_PY:
                return cand
        except Exception:
            continue
    raise SystemExit(
        f"Could not find Python >= {MIN_PY[0]}.{MIN_PY[1]} on PATH.\n"
        f"  Install one: https://www.python.org/downloads/\n"
        f"  Tried: {ordered}"
    )


# ---------------------------------------------------------------------------
# 2. venv + install
# ---------------------------------------------------------------------------
def venv_python() -> str:
    if os.name == "nt":
        return str(VENV / "Scripts" / "python.exe")
    return str(VENV / "bin" / "python")


def ensure_venv(py: str) -> str:
    if not VENV.exists():
        print(f">> creating venv at {VENV} using {py}")
        venv.EnvBuilder(with_pip=True, upgrade_deps=True).create(str(VENV))
    return venv_python()


def deps_installed(vpy: str) -> bool:
    """Cheap check: does the package's import work?"""
    try:
        subprocess.run(
            [vpy, "-c", "import fastapi, uvicorn, sgp4, apscheduler, orjson, websockets"],
            check=True, capture_output=True, timeout=30,
        )
        return True
    except Exception:
        return False


def ensure_deps(vpy: str) -> None:
    if deps_installed(vpy):
        print(">> backend deps already installed, skipping pip")
        return
    print(f">> installing backend deps (this can take 1-2 min)...")
    subprocess.run([vpy, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([vpy, "-m", "pip", "install", "-e", str(BACKEND)], check=True)
    print(">> backend deps installed")


def ensure_env() -> None:
    src = BACKEND / ".env.example"
    dst = BACKEND / ".env"
    if not dst.exists() and src.exists():
        shutil.copyfile(src, dst)
        print(f">> wrote {dst}")


# ---------------------------------------------------------------------------
# 3. Free the port
# ---------------------------------------------------------------------------
def free_port(port: int) -> None:
    if os.name == "nt":
        out = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True, check=False,
        ).stdout
        pids: set[str] = set()
        for line in out.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                m = re.search(r"\s(\d+)\s*$", line)
                if m:
                    pids.add(m.group(1))
        if not pids:
            print(f">> port {port} is free")
            return
        print(f">> port {port} busy, killing pids: {sorted(pids)}")
        for pid in pids:
            subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
    else:
        # macOS / Linux — anything listening on tcp:PORT
        try:
            out = subprocess.run(
                ["lsof", "-ti", f"tcp:{port}"],
                capture_output=True, text=True, check=False,
            ).stdout.strip()
            if not out:
                print(f">> port {port} is free")
                return
            pids = [p for p in out.splitlines() if p]
            print(f">> port {port} busy, killing pids: {pids}")
            for pid in pids:
                subprocess.run(["kill", "-9", pid], capture_output=True)
        except FileNotFoundError:
            # lsof missing on minimal containers — try fuser
            subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True)
            print(f">> port {port} may have been freed by fuser")


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 60)
    print(f"  Realtime Earth — starting ({platform.system()} {platform.machine()})")
    print("=" * 60)
    py = find_python()
    print(f">> using python: {py}")
    vpy = ensure_venv(py)
    print(f">> venv python: {vpy}")
    ensure_deps(vpy)
    ensure_env()
    free_port(PORT)

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    # CWD matters — the Settings class looks for .env relative to CWD
    os.chdir(BACKEND)

    cmd = [
        vpy, "-m", "uvicorn", "app.main:app",
        "--host", "0.0.0.0", "--port", str(PORT), "--log-level", "info",
    ]
    print(">>", " ".join(cmd))
    print(f">> Open  http://localhost:{PORT}        (3D globe)")
    print(f">>       http://localhost:{PORT}/docs   (FastAPI Swagger)")
    print(f">>       http://localhost:{PORT}/healthz (per-source status)")
    print(f">>       http://localhost:{PORT}/diag.html (WebGL diagnostic)")
    sys.stdout.flush()
    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    sys.exit(main())
