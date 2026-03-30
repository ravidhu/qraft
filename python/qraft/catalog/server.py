import http.server
import functools
from pathlib import Path


def serve_catalog(catalog_dir: Path, port: int = 8080) -> None:
    """Start a local HTTP server to view the generated catalog."""
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=str(catalog_dir),
    )
    with http.server.HTTPServer(("", port), handler) as httpd:
        print(f"Serving catalog at http://localhost:{port}")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
