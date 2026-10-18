"""Run the web and API processes together; stop the container when either fails."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    port = int(os.getenv("PORT", "8080"))
    if not 1024 <= port <= 65535 or port in {3000, 8000}:
        raise ValueError("PORT must be an unprivileged ingress port other than 3000/8000")
    config = Path("/tmp/your-optimiser-nginx.conf")
    config.write_text(
        Path("/app/deploy/combined-nginx.conf").read_text().replace("__PORT__", str(port))
    )
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
