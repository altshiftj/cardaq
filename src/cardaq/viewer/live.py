"""Read-only loopback viewer for a directory of recordings."""

import csv
import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit

from . import _read_capture, _render_page, _viewer_data


class RecordingFolder:
    def __init__(self, folder: Path):
        self.folder = folder.resolve()
        self.cache = {}
        self.lock = Lock()

    def inventory(self):
        entries = {}
        for path in sorted(self.folder.rglob("*")):
            if path.suffix.lower() != ".csv" or path.is_symlink() or not path.is_file():
                continue
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            entries[path.relative_to(self.folder).as_posix()] = (stat.st_size, stat.st_mtime_ns)
        return entries

    @staticmethod
    def revision(entries):
        return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()

    def page(self):
        with self.lock:
            entries = self.inventory()
            drives = []
            skipped = []
            for name in self.cache.keys() - entries.keys():
                del self.cache[name]
            for name, stamp in entries.items():
                if name not in self.cache or self.cache[name][0] != stamp:
                    try:
                        drive = _read_capture(self.folder / name, name[:-4])
                    except (ValueError, OSError, csv.Error):
                        drive = None
                    self.cache[name] = stamp, drive
                drive = self.cache[name][1]
                if drive is None:
                    skipped.append(name)
                else:
                    drives.append(drive)
            data = _viewer_data(drives)
            data["live"] = {"revision": self.revision(entries), "folder": str(self.folder), "skipped": skipped}
            return _render_page(data)


def serve(folder: Path, port: int) -> None:
    if not 0 <= port <= 65535:
        raise ValueError("Use a port between 0 and 65535.")
    if folder.exists() and not folder.is_dir():
        raise ValueError(f"{folder} is not a directory.")
    library = RecordingFolder(folder)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            port = self.server.server_port
            if self.headers.get("Host") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
                self.send_error(403)
                return
            route = urlsplit(self.path).path
            if route == "/":
                body = library.page().encode()
                mime = "text/html; charset=utf-8"
            elif route == "/revision":
                body = library.revision(library.inventory()).encode()
                mime = "text/plain"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
        print(f"Watching {library.folder}\nOpen http://127.0.0.1:{server.server_port}/  (Ctrl+C to stop)", flush=True)
        server.serve_forever()
