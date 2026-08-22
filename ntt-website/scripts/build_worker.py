"""Build a single Cloudflare Worker module that serves the static site."""
from __future__ import annotations

import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
OUT = ROOT / "worker.mjs"

TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
}

SKIP = {"_headers", "logo-ds.png", "logo-ntt.png"}


def main() -> None:
    files = {}
    for path in sorted(PUBLIC.rglob("*")):
        if not path.is_file() or path.name in SKIP:
            continue
        rel = "/" + path.relative_to(PUBLIC).as_posix()
        mime = TYPES.get(path.suffix.lower(), "application/octet-stream")
        raw = path.read_bytes()
        files[rel] = {
            "type": mime,
            "b64": base64.b64encode(raw).decode("ascii"),
        }
        if rel == "/index.html":
            files["/"] = files[rel]

    payload = json.dumps(files, separators=(",", ":"))
    OUT.write_text(
        "const files = "
        + payload
        + ";\n"
        + "export default {\n"
        + "  async fetch(request) {\n"
        + "    const url = new URL(request.url);\n"
        + "    const key = url.pathname === '' ? '/' : url.pathname;\n"
        + "    const file = files[key] || files[key.replace(/\\/$/, '')];\n"
        + "    if (!file) return new Response('Introuvable', { status: 404, headers: { 'content-type': 'text/plain; charset=utf-8' } });\n"
        + "    const bytes = Uint8Array.from(atob(file.b64), (c) => c.charCodeAt(0));\n"
        + "    return new Response(bytes, { headers: { 'content-type': file.type, 'x-content-type-options': 'nosniff', 'referrer-policy': 'strict-origin-when-cross-origin', 'x-frame-options': 'DENY' } });\n"
        + "  }\n"
        + "};\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes, {len(files)} routes)")


if __name__ == "__main__":
    main()
