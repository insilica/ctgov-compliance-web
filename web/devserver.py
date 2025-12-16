"""
Developer convenience server that starts both the Flask API and the Vite
frontend, mirroring what we previously ran manually in two terminals.

Run via:
    uv run devserver
or inside the nix shell:
    nix develop -c devserver
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "web" / "frontend"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_BACKEND_PORT = 6525
DEFAULT_FRONTEND_PORT = 5173


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Flask + Vite dev servers together.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind both servers to.")
    parser.add_argument(
        "--backend-port",
        type=int,
        default=DEFAULT_BACKEND_PORT,
        help="Port for the Flask server.",
    )
    parser.add_argument(
        "--frontend-port",
        type=int,
        default=DEFAULT_FRONTEND_PORT,
        help="Port for the Vite dev server.",
    )
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Run only the backend. Useful when iterating on Flask.",
    )
    parser.add_argument(
        "--skip-backend",
        action="store_true",
        help="Run only the Vite dev server. Useful when iterating purely on React.",
    )
    return parser.parse_args()


def ensure_node_modules() -> None:
    node_modules = FRONTEND_DIR / "node_modules"
    if node_modules.exists():
        return

    if shutil.which("npm") is None:
        raise RuntimeError(
            "npm was not found on PATH. Install Node.js/npm or run inside the nix shell."
        )
    print("[devserver] Installing frontend dependencies (npm install)…", flush=True)
    subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, check=True)


def stream_process(prefix: str, process: subprocess.Popen[str]) -> None:
    assert process.stdout is not None
    for raw_line in process.stdout:
        print(f"[{prefix}] {raw_line.rstrip()}")


def launch_process(
    prefix: str, cmd: Iterable[str], cwd: Path, env: dict[str, str]
) -> subprocess.Popen[str]:
    proc = subprocess.Popen(
        list(cmd),
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    thread = threading.Thread(target=stream_process, args=(prefix, proc), daemon=True)
    thread.start()
    return proc


def main() -> None:
    args = parse_args()
    if args.skip_backend and args.skip_frontend:
        print("Both --skip-backend and --skip-frontend were provided, nothing to run.", file=sys.stderr)
        sys.exit(1)

    processes: list[subprocess.Popen[str]] = []

    def shutdown(_: int, __: int) -> None:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        # give processes time to shut down to avoid zombie warnings
        time.sleep(0.5)
        for proc in processes:
            if proc.poll() is None:
                proc.kill()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        if not args.skip_backend:
            backend_env = os.environ.copy()
            backend_env.setdefault("FLASK_APP", "web.app")
            backend_env.setdefault("ENVIRONMENT", "dev")
            backend_cmd = [
                sys.executable,
                "-m",
                "flask",
                "run",
                "--host",
                args.host,
                "--port",
                str(args.backend_port),
            ]
            print(
                f"[devserver] Starting Flask backend on http://{args.host}:{args.backend_port}",
                flush=True,
            )
            processes.append(launch_process("backend", backend_cmd, REPO_ROOT, backend_env))

        if not args.skip_frontend:
            ensure_node_modules()
            frontend_env = os.environ.copy()
            # Vite uses HOST env var if set; avoid overriding
            frontend_cmd = [
                "npm",
                "run",
                "dev",
                "--",
                "--host",
                args.host,
                "--port",
                str(args.frontend_port),
            ]
            print(
                f"[devserver] Starting Vite frontend on http://{args.host}:{args.frontend_port}",
                flush=True,
            )
            processes.append(launch_process("frontend", frontend_cmd, FRONTEND_DIR, frontend_env))

        while processes:
            for proc in list(processes):
                code = proc.poll()
                if code is None:
                    continue
                if code != 0:
                    shutdown(0, 0)
                    sys.exit(code)
                processes.remove(proc)
            time.sleep(0.2)
    finally:
        shutdown(0, 0)


if __name__ == "__main__":
    main()
