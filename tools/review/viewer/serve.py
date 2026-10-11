"""The viewer's local server: every exported place (`export.py`) to walk through in a browser, and the picked
viewpoints saved from it.

    .venv/bin/python tools/review/viewer/serve.py [--port 8770] [--web ~/.farm-factory-props/work/web] \
        [--picks data/review]

then open http://localhost:8770/ in the Windows browser (WSL hands localhost on to it). It listens on this machine
only (127.0.0.1). Routes:

    GET  /                   the index: every place with a web copy, its size and triangles
    GET  /view/<place>       the viewer (viewer.html)
    GET  /web/<place>/<file> the place's web copy (<place>.glb, <place>.json)
    GET  /picks/<place>      the place's picked viewpoints
    POST /picks/<place>      save one ({name, eye, aim, fov}; viewpoints.append): the viewpoint as saved
"""
import argparse
import html
import json
import pathlib
import shutil
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import viewpoints

HERE = pathlib.Path(__file__).resolve().parent
WEB = pathlib.Path.home() / ".farm-factory-props/work/web"
PORT = 8770
TYPES = {".glb": "model/gltf-binary", ".json": "application/json", ".html": "text/html; charset=utf-8"}
LARGEST_POST = 10_000


def places(web):
    """Each place with a web copy, by name: its sidecar's numbers."""
    found = {}
    for sidecar in sorted(web.glob("*/*.json")):
        if sidecar.stem == sidecar.parent.name and (sidecar.parent / f"{sidecar.stem}.glb").exists():
            numbers = json.loads(sidecar.read_text())
            found[sidecar.stem] = {"bytes": numbers["bytes"], "triangles": numbers["triangles"],
                                   "cameras": len(numbers["cameras"])}
    return found


def index_page(web, picks):
    """The index: a line per place with a web copy, linking to its viewer."""
    rows = "".join(
        f'<tr><td><a href="/view/{name}">{html.escape(name)}</a></td><td>{numbers["bytes"] / 1e6:.1f} MB</td>'
        f'<td>{numbers["triangles"]:,}</td><td>{numbers["cameras"]}</td>'
        f'<td>{len(viewpoints.read(name, picks))}</td></tr>' for name, numbers in places(web).items())
    return (f"<!doctype html><meta charset=utf-8><title>SCORE places</title><style>body{{font:15px system-ui;"
            f"margin:2em}}td,th{{padding:.3em 1.2em .3em 0;text-align:left}}</style><h1>Places</h1>"
            f"<table><tr><th>Place</th><th>Web copy</th><th>Triangles</th><th>Proposed views</th><th>Picked</th></tr>"
            f"{rows or '<tr><td colspan=5>No place exported yet: run tools/review/viewer/export.py</td></tr>'}"
            f"</table><p>Web copies in {html.escape(str(web))}; picks in {html.escape(str(picks))}.</p>")


def handler(web, picks):
    """The request handler for a server over the web copies in `web` and the picks in `picks`."""

    class Handler(BaseHTTPRequestHandler):
        def send(self, status, body, kind):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, status, value):
            self.send(status, json.dumps(value).encode(), TYPES[".json"])

        def send_file(self, path):
            self.send_response(200)
            self.send_header("Content-Type", TYPES[path.suffix])
            self.send_header("Content-Length", str(path.stat().st_size))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            with path.open("rb") as source:
                shutil.copyfileobj(source, self.wfile)

        def do_GET(self):
            parts = [part for part in self.path.split("?")[0].split("/") if part]
            known = places(web)
            if not parts:
                return self.send(200, index_page(web, picks).encode(), TYPES[".html"])
            if parts[0] == "view" and len(parts) == 2 and parts[1] in known:
                return self.send_file(HERE / "viewer.html")
            if parts[0] == "web" and len(parts) == 3 and parts[1] in known and parts[2] in (
                    f"{parts[1]}.glb", f"{parts[1]}.json"):
                return self.send_file(web / parts[1] / parts[2])
            if parts[0] == "picks" and len(parts) == 2 and parts[1] in known:
                return self.send_json(200, {"place": parts[1], "viewpoints": viewpoints.read(parts[1], picks)})
            return self.send_json(404, {"error": f"nothing at {self.path}"})

        def do_POST(self):
            parts = [part for part in self.path.split("/") if part]
            if len(parts) != 2 or parts[0] != "picks" or parts[1] not in places(web):
                return self.send_json(404, {"error": f"nothing to save at {self.path}"})
            length = int(self.headers.get("Content-Length") or 0)
            if not 0 < length <= LARGEST_POST:
                return self.send_json(400, {"error": "send one viewpoint as JSON"})
            try:
                saved = viewpoints.append(parts[1], json.loads(self.rfile.read(length)), picks)
            except (json.JSONDecodeError, viewpoints.BadViewpoint) as error:
                return self.send_json(400, {"error": str(error)})
            self.send_json(200, saved)

        def log_message(self, *_):
            pass  # one line at start is the server's whole output; a failing request answers its error

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--web", type=pathlib.Path, default=WEB)
    parser.add_argument("--picks", type=pathlib.Path, default=viewpoints.PICKS)
    arguments = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", arguments.port), handler(arguments.web, arguments.picks))
    print(f"{len(places(arguments.web))} places; open http://localhost:{arguments.port}/ (ctrl-c stops)", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
