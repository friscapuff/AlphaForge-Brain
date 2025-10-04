#!/usr/bin/env python3
"""Launch AlphaForge (backend + frontend) with one command.

Usage (after adding console entrypoint):
  poetry run launch-alphaforge

What it does:
  1. Starts the FastAPI backend with uvicorn on http://127.0.0.1:8000
  2. Starts the frontend dev server (Vite) in `alphaforge-mind` on http://127.0.0.1:5173
  3. Opens your default browser to the frontend URL once both are responsive.

Ctrl+C once to stop both processes gracefully.

Designed to be beginner friendly (minimal flags) and Windows-friendly.
"""
from __future__ import annotations

import argparse
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from contextlib import suppress
from pathlib import Path
from typing import Optional


def _try_url(url: str) -> bool:
    with suppress(Exception):
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=0.8) as resp:  # nosec - local dev
            return 200 <= getattr(resp, "status", 200) < 500
    return False


import shutil

BACKEND_HOST = "127.0.0.1"
# Default ports (can be overridden via CLI)
DEFAULT_BACKEND_PORT = 8000
DEFAULT_FRONTEND_PORT = 5173


def _is_port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        return s.connect_ex((host, port)) != 0


def _find_free_port(host: str, preferred: int, search_limit: int = 15) -> int:
    if _is_port_free(host, preferred):
        return preferred
    for offset in range(1, search_limit + 1):
        candidate = preferred + offset
        if _is_port_free(host, candidate):
            return candidate
    raise RuntimeError(
        f"No free port found near {preferred} (checked {search_limit} increments)"
    )


BACKEND_URL_TEMPLATE = "http://{host}:{port}/health"


def _port_open(host: str, port: int) -> bool:
    # Try IPv4 then IPv6
    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            with socket.socket(family, socket.SOCK_STREAM) as s:
                s.settimeout(0.25)
                if s.connect_ex((host, port)) == 0:
                    return True
        except OSError:
            continue
    return False


def wait_for_port(
    host: str,
    port: int,
    label: str,
    timeout: float = 35.0,
    alt_hosts: list[str] | None = None,
    url_probe: str | None = None,
    early_event: threading.Event | None = None,
) -> Optional[str]:
    start = time.time()
    spinner = "|/-\\"
    i = 0
    while time.time() - start < timeout:
        if early_event and early_event.is_set():
            print(f"[{label}] readiness signaled externally.")
            return host
        if _port_open(host, port):
            ready_note = " (url ok)" if (url_probe and _try_url(url_probe)) else ""
            print(f"[{label}] port {port} is up.{ready_note}")
            return host
        if alt_hosts:
            for h in alt_hosts:
                if _port_open(h, port):
                    # Adjust url_probe to use alt host when probing root page
                    effective_probe = (
                        url_probe.replace("localhost", h)
                        if (url_probe and "localhost" in url_probe)
                        else url_probe
                    )
                    ready_note = (
                        " (url ok)"
                        if (effective_probe and _try_url(effective_probe))
                        else ""
                    )
                    print(f"[{label}] port {port} is up on {h}.{ready_note}")
                    return h
        sys.stdout.write(f"\r[{label}] starting {spinner[i % len(spinner)]}")
        sys.stdout.flush()
        i += 1
        time.sleep(0.35)
    print(f"\n[{label}] timed out waiting for port {port}.")
    return None


def launch(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Launch AlphaForge full stack")
    parser.add_argument(
        "--backend-port",
        type=int,
        default=DEFAULT_BACKEND_PORT,
        help="Backend port (default 8000)",
    )
    parser.add_argument(
        "--frontend-port",
        type=int,
        default=DEFAULT_FRONTEND_PORT,
        help="Frontend port (default 5173)",
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="Do not open a browser window"
    )
    parser.add_argument(
        "--frontend-host",
        default=BACKEND_HOST,
        help="Frontend host bind (default 127.0.0.1)",
    )
    parser.add_argument(
        "--backend-host",
        default=BACKEND_HOST,
        help="Backend host bind (default 127.0.0.1)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=45.0,
        help="Seconds to wait for services to become ready",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose diagnostics output"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Minimal output (overrides verbose)"
    )
    args = parser.parse_args(argv)

    backend_port = args.backend_port
    frontend_port_preferred = args.frontend_port
    backend_host = args.backend_host
    frontend_host = args.frontend_host

    # Determine effective frontend port (auto-fallback if taken)
    try:
        frontend_port = _find_free_port(frontend_host, frontend_port_preferred)
    except RuntimeError as e:
        print(f"ERROR: {e}")
        return 1
    if frontend_port != frontend_port_preferred:
        print(
            f"[frontend] Preferred port {frontend_port_preferred} in use; selected free port {frontend_port} instead."
        )

    backend_health_url = BACKEND_URL_TEMPLATE.format(
        host=backend_host, port=backend_port
    )
    root = Path(__file__).resolve().parent.parent
    brain_app_module = "api.app:app"  # uvicorn target (already configured in project)

    # 1. Start backend
    env = os.environ.copy()
    # Ensure Python path includes brain src
    brain_src = root / "alphaforge-brain" / "src"
    env["PYTHONPATH"] = str(brain_src) + os.pathsep + env.get("PYTHONPATH", "")

    if not args.quiet:
        print("Starting backend (FastAPI / uvicorn)...")
    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        brain_app_module,
        "--host",
        backend_host,
        "--port",
        str(backend_port),
    ]
    backend_proc = subprocess.Popen(backend_cmd, cwd=root, env=env)

    # 2. Start frontend (Vite dev server)
    mind_dir = root / "alphaforge-mind"
    if not (mind_dir / "package.json").exists():
        print(
            "ERROR: Frontend directory 'alphaforge-mind' not found or missing package.json."
        )
        backend_proc.terminate()
        return 1
    # Prefer npm; detect actual executable (Windows typically npm.cmd)
    npm_exe: str | None = shutil.which("npm")
    if npm_exe is None:
        # Attempt common installation path fallback (user installed Node but shell not restarted)
        possible_roots = [
            Path(os.getenv("ProgramFiles", "C:/Program Files")) / "nodejs",
            Path(os.getenv("ProgramFiles(x86)", "C:/Program Files (x86)")) / "nodejs",
        ]
        for root_path in possible_roots:
            candidate = root_path / "npm.cmd"
            if candidate.exists():
                npm_exe = str(candidate)
                break
    if npm_exe is None:
        print(
            "ERROR: 'npm' not found in PATH.\nFix: Install Node.js from https://nodejs.org/ OR reopen your terminal so PATH updates.\nIf already installed, ensure the Node.js installation directory (e.g. C\\\Program Files\\\nodejs) is in your PATH."
        )
        backend_proc.terminate()
        return 1
    if args.verbose and not args.quiet:
        print(f"Detected npm at: {npm_exe}")
    # Force Vite to bind explicitly to 127.0.0.1 to avoid environments where it defaults to ::1 only.
    node_cmd = [
        npm_exe,
        "run",
        "dev",
        "--",
        "--host",
        frontend_host,
        "--port",
        str(frontend_port),
    ]
    if not args.quiet:
        print("Starting frontend (Vite)...")
    # 3. Start frontend ONCE with captured stdout for diagnostics
    vite_ready_event = threading.Event()
    vite_url_box: dict[str, str] = {}

    url_pattern = re.compile(r"Local:\s*(https?://[\w\.-]+:\d+)")

    def _capture_frontend():
        assert frontend_proc.stdout is not None
        for raw in iter(frontend_proc.stdout.readline, b""):
            try:
                line = raw.decode(errors="replace").rstrip()
            except Exception:
                continue
            if not line:
                continue
            print(f"[frontend-log] {line}")
            m = url_pattern.search(line)
            if m and not vite_ready_event.is_set():
                vite_url_box["url"] = m.group(1)
                vite_ready_event.set()
        # Stream ended
        vite_ready_event.set()

    try:
        frontend_proc = subprocess.Popen(
            node_cmd,
            cwd=mind_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )
    except Exception as exc:  # broader catch with message
        print(f"ERROR: Failed to start frontend via npm ({exc}).")
        backend_proc.terminate()
        return 1
    threading.Thread(target=_capture_frontend, daemon=True).start()

    backend_host_resolved = wait_for_port(
        backend_host,
        backend_port,
        "backend",
        url_probe=backend_health_url,
        timeout=args.timeout,
    )
    frontend_host_resolved = wait_for_port(
        frontend_host,
        frontend_port,
        "frontend",
        alt_hosts=["localhost", "127.0.0.1", "::1"],
        url_probe=f"http://{frontend_host}:{frontend_port}",
        timeout=args.timeout,
        early_event=vite_ready_event,
    )

    # Choose final URL (prefer captured Vite URL if available)
    chosen_frontend_url = vite_url_box.get(
        "url", f"http://{frontend_host_resolved or frontend_host}:{frontend_port}"
    )

    if backend_host_resolved and frontend_host_resolved:
        if not args.quiet:
            print(
                f"[ready] Backend: http://{backend_host_resolved}:{backend_port}  Health: {backend_health_url}"
            )
            print(f"[ready] Frontend: {chosen_frontend_url}")
        if not args.no_browser:
            if not args.quiet:
                print(f"Opening browser at {chosen_frontend_url} ...")
            try:
                webbrowser.open(chosen_frontend_url)
            except Exception:
                print(f"Please open your browser and go to: {chosen_frontend_url}")
        elif not args.quiet:
            print("Browser launch suppressed (--no-browser).")
        if not args.quiet:
            print("Both services running. Press Ctrl+C to stop.")
    else:
        print("One or more services failed to start; shutting down.")
        for p in (backend_proc, frontend_proc):
            if p.poll() is None:
                p.terminate()
        return 1

    # 4. Handle Ctrl+C gracefully
    try:
        while True:
            time.sleep(1)
            # If either process exited unexpectedly, abort
            if backend_proc.poll() is not None:
                print("Backend process exited; stopping frontend.")
                break
            if frontend_proc.poll() is not None:
                print("Frontend process exited; stopping backend.")
                break
    except KeyboardInterrupt:
        print("\nStopping AlphaForge...")
    finally:
        for p in (backend_proc, frontend_proc):
            if p.poll() is None:
                if os.name == "nt":
                    (
                        p.send_signal(signal.CTRL_BREAK_EVENT)
                        if hasattr(signal, "CTRL_BREAK_EVENT")
                        else p.terminate()
                    )
                else:
                    p.terminate()
        # Small grace period
        time.sleep(1.0)
    return 0


def main() -> None:
    code = launch(sys.argv[1:])
    raise SystemExit(code)


if __name__ == "__main__":  # pragma: no cover
    main()
