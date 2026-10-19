"""Run the web and API processes together; stop the container when either fails."""

import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

NGINX_TEMPLATE = Path("/app/deploy/combined-nginx.conf")
NGINX_CONFIG = Path("/tmp/your-optimiser-nginx.conf")


def wait_for_backends(
    processes: list[subprocess.Popen[bytes]],
    stopped: Callable[[], bool],
    timeout: float = 180,
) -> bool:
    """Keep ingress closed until both servers can handle HTTP requests.

    Cloud Run's TCP startup check otherwise succeeds as soon as nginx binds,
    ending startup CPU allocation while its upstream processes are still loading.
    """
    pending = {"http://127.0.0.1:8000/api/v1/health", "http://127.0.0.1:3000/"}
    deadline = time.monotonic() + timeout
    while pending and time.monotonic() < deadline:
        if stopped() or any(process.poll() is not None for process in processes):
            return False
        for url in tuple(pending):
            try:
                with urlopen(url, timeout=2) as response:  # noqa: S310
                    if response.status == 200:
                        pending.remove(url)
            except (URLError, TimeoutError, OSError):
                pass
        if pending:
            time.sleep(0.2)
    if pending:
        print("Startup timed out waiting for the frontend and API.", file=sys.stderr, flush=True)
    return not pending and not stopped()


def main() -> int:
    port = int(os.getenv("PORT", "8080"))
    if not 1024 <= port <= 65535 or port in {3000, 8000}:
        raise ValueError("PORT must be an unprivileged ingress port other than 3000/8000")
    config = NGINX_CONFIG
    config.write_text(NGINX_TEMPLATE.read_text().replace("__PORT__", str(port)))
    processes: list[subprocess.Popen[bytes]] = []
    stopped = False

    def stop(*_: object) -> None:
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "seo_optimizer.web:create_app",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                    "--proxy-headers",
                    "--forwarded-allow-ips",
                    "127.0.0.1",
                ]
            )
        )
        processes.append(
            subprocess.Popen(
                ["node", "server.js"],
                cwd="/app/web",
                env={**os.environ, "HOSTNAME": "127.0.0.1", "PORT": "3000"},
            )
        )
        if not wait_for_backends(processes, lambda: stopped):
            return 1
        print("Frontend and API ready; opening ingress.", flush=True)
        processes.append(subprocess.Popen(["nginx", "-c", str(config), "-g", "daemon off;"]))
        while not stopped:
            if any(process.poll() is not None for process in processes):
                return 1
            time.sleep(0.2)
        return 0
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        deadline = time.monotonic() + 8
        for process in processes:
            try:
                process.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
