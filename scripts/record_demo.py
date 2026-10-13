"""Record a real PTY session and guide interactions with Chromium; no invented stdout."""

import argparse
import json
import os
import pty
import re
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SCREEN = (ROOT / "videos/terminal.html").read_text()


def record(output, guide_url):
    directory = ROOT / ".data/demo-recording"
    directory.mkdir(parents=True, exist_ok=True)
    state = {"text": "", "done": False, "events": [], "commands": []}
    lock = threading.Lock()
    started = time.monotonic()

    def emit(text):
        clean = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text).replace("\r\n", "\n")
        with lock:
            state["text"] += clean
            state["events"].append({"time": time.monotonic() - started, "text": clean})

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/events":
                with lock:
                    content = json.dumps({"text": state["text"], "done": state["done"]}).encode()
                kind = "application/json"
            else:
                content, kind = SCREEN.encode(), "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *args):
            pass

    def run(argv):
        emit("$ " + " ".join(argv) + "\n")
        parent, child = pty.openpty()
        process = subprocess.Popen(
            argv,
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=child,
            stderr=child,
            env={**os.environ, "TERM": "dumb", "NO_COLOR": "1"},
        )
        os.close(child)
        begin = time.monotonic()
        while True:
            try:
                block = os.read(parent, 8192)
            except OSError:
                break
            if not block:
                break
            emit(block.decode(errors="replace"))
        os.close(parent)
        code = process.wait()
        state["commands"].append(
            {"argv": argv, "exit_code": code, "runtime_seconds": time.monotonic() - begin}
        )
        emit(f"\n[exit {code}]\n\n")
        if code:
            raise RuntimeError("Recorded command failed")
        time.sleep(2)

    def commands():
        try:
            run(
                [
                    "uv",
                    "run",
                    "python",
                    "scripts/test_portfolio.py",
                    "--reuse-build",
                    "--skip-model",
                    "--output",
                    ".data/demo-recording/run.json",
                ]
            )
            result = json.loads((directory / "run.json").read_text())
            fix = next(item for item in result["cases"] if item["case"] == "rendered-title-repair")
            sha = fix["result"]["merged_sha"]
            run(
                [
                    "git",
                    "-C",
                    ".data/portfolio-test",
                    "show",
                    "--format=short",
                    sha,
                    "--",
                    "public/index.html",
                ]
            )
            run(["uv", "run", "pytest", "-q", "--disable-warnings"])
        except Exception as error:
            emit(f"Recording failure: {error}\n")
            state["error"] = type(error).__name__
        finally:
            state["done"] = True

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(channel="chromium")
        context = browser.new_context(
            viewport={"width": 1200, "height": 680},
            record_video_dir=str(directory / "raw"),
            record_video_size={"width": 1200, "height": 680},
        )
        page = context.new_page()
        page.goto(f"http://127.0.0.1:{server.server_port}")
        page.wait_for_timeout(1200)
        started = time.monotonic()
        worker = threading.Thread(target=commands)
        worker.start()
        deadline = time.monotonic() + 180
        while not state["done"] and time.monotonic() < deadline:
            page.wait_for_timeout(200)
        if not state["done"]:
            raise RuntimeError("Recording exceeded its budget")
        worker.join()
        page.wait_for_timeout(1800)
        page.screenshot(path=str(directory / "terminal.png"))
        video = page.video
        context.close()
        video.save_as(str(directory / "terminal.webm"))
        guide = browser.new_context(
            viewport={"width": 1200, "height": 680},
            record_video_dir=str(directory / "raw"),
            record_video_size={"width": 1200, "height": 680},
        )
        page = guide.new_page()
        page.goto(guide_url)
        page.locator("#workflow").scroll_into_view_if_needed()
        page.evaluate("window.scrollTo(0, document.querySelector('#workflow').offsetTop - 32)")
        page.wait_for_timeout(1200)
        for index in [2, 3, 4, 5, 6, 7]:
            page.locator(f'[data-step="{index}"]').click()
            page.wait_for_timeout(900)
        page.screenshot(path=str(directory / "guide.png"))
        video = page.video
        guide.close()
        video.save_as(str(directory / "guide.webm"))
        browser.close()
    server.shutdown()
    server.server_close()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "capture": "Actual subprocess PTY streamed to a browser and recorded",
                "commands": state["commands"],
                "events": state["events"],
                "error": state.get("error"),
                "terminal_video": "terminal.webm",
                "guide_video": "guide.webm",
            },
            indent=2,
        )
        + "\n"
    )
    assert state.get("error") is None
    print("Recorded real terminal execution and guide interactions", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "videos/public/capture.json")
    parser.add_argument("--guide-url", default="http://127.0.0.1:8787/guide")
    args = parser.parse_args()
    record(args.output, args.guide_url)
