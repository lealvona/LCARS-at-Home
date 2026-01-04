from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    cwd_candidate = Path.cwd() / "lcars_guide.py"
    if cwd_candidate.exists():
        return Path.cwd()

    # Best-effort fallback for editable installs.
    package_root = Path(__file__).resolve().parents[1]
    if (package_root / "lcars_guide.py").exists():
        return package_root

    raise FileNotFoundError(
        "Unable to locate lcars_guide.py. Run from the repo root (where lcars_guide.py exists)."
    )


def _passthrough_args() -> list[str]:
    """Return args intended for the underlying script.

    `uv run <cmd> -- <args>` typically forwards the literal `--` into argv.
    Strip a leading `--` so `--help` works consistently.
    """
    argv = sys.argv[1:]
    if argv and argv[0] == "--":
        return argv[1:]
    return argv


def guide() -> None:
    """Run the Streamlit installer UI."""
    argv = _passthrough_args()
    if argv and argv[0] in {"-h", "--help"}:
        print(
            "Usage: lcars-guide [-- <streamlit args>]\n"
            "Runs the Streamlit installer UI (lcars_guide.py).\n\n"
            "Examples:\n"
            "  uv run lcars-guide\n"
            "  uv run lcars-guide -- --server.headless true\n"
        )
        raise SystemExit(0)

    repo_root = _project_root()
    app_path = repo_root / "lcars_guide.py"

    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path), *argv]
    raise SystemExit(subprocess.call(cmd, cwd=str(repo_root), env=os.environ.copy()))


def setup_env() -> None:
    """Generate docker/.env (defaults to scripts/setup.py --generate-env).

    Pass through args as-is; if no args are provided, defaults to --generate-env.
    """
    repo_root = _project_root()

    argv = _passthrough_args()
    if not argv:
        argv = ["--generate-env"]

    cmd = [sys.executable, str(repo_root / "scripts" / "setup.py"), *argv]
    raise SystemExit(subprocess.call(cmd, cwd=str(repo_root), env=os.environ.copy()))


def health_check() -> None:
    """Run the health check script (equivalent to scripts/health_check.py)."""
    repo_root = _project_root()
    cmd = [sys.executable, str(repo_root / "scripts" / "health_check.py"), *_passthrough_args()]
    raise SystemExit(subprocess.call(cmd, cwd=str(repo_root), env=os.environ.copy()))


def backup() -> None:
    """Run the backup script (equivalent to scripts/backup.py)."""
    repo_root = _project_root()
    cmd = [sys.executable, str(repo_root / "scripts" / "backup.py"), *_passthrough_args()]
    raise SystemExit(subprocess.call(cmd, cwd=str(repo_root), env=os.environ.copy()))


def update() -> None:
    """Run the update script (equivalent to scripts/update.sh).

    Use `--help` here to show usage without executing updates.
    """
    argv = _passthrough_args()
    if argv and argv[0] in {"-h", "--help"}:
        print(
            "Usage: lcars-update\n"
            "Runs scripts/update.sh from the repo root.\n\n"
            "Examples:\n"
            "  uv run lcars-update\n"
        )
        raise SystemExit(0)

    repo_root = _project_root()
    script_path = repo_root / "scripts" / "update.sh"
    cmd = ["bash", str(script_path), *argv]
    raise SystemExit(subprocess.call(cmd, cwd=str(repo_root), env=os.environ.copy()))
