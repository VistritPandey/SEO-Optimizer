"""Serve compiled assets while reflecting source head edits for metadata-only tests."""

import argparse
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


class PortfolioHandler(SimpleHTTPRequestHandler):
    repository: Path
    build: Path

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(self.build), **kwargs)

    def do_GET(self):
        if urlsplit(self.path).path == "/":
            compiled = (self.build / "index.html").read_text()
            source = (self.repository / "public/index.html").read_text()
            head = re.search(r"<head\b.*?</head>", source, re.I | re.S)
            if head is None:
                self.send_error(500, "Source document head unavailable")
                return
            html = re.sub(
                r"<head\b.*?</head>",
                lambda _: head.group().replace("%PUBLIC_URL%", ""),
                compiled,
                count=1,
                flags=re.I | re.S,
            )
            body = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

    def log_message(self, format, *args):
        pass


def serve(repository: Path, build: Path, port: int):
    handler = type(
        "ConfiguredPortfolioHandler",
        (PortfolioHandler,),
        {
            "repository": repository.resolve(),
            "build": build.resolve(),
        },
    )
    return ThreadingHTTPServer(("127.0.0.1", port), handler)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8811)
    arguments = parser.parse_args()
    server = serve(arguments.repository, arguments.build, arguments.port)
    print(f"Portfolio fixture: http://127.0.0.1:{arguments.port}", flush=True)
    server.serve_forever()
