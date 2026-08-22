from pathlib import Path
import base64
import json
import re

root = Path(__file__).resolve().parents[1]
public = root / "public"
html = (public / "index.html").read_text(encoding="utf-8")
css = (public / "styles.css").read_text(encoding="utf-8")
js = (public / "app.js").read_text(encoding="utf-8")
svg = (public / "logo-ntt.svg").read_bytes()

svg_uri = "data:image/svg+xml;base64," + base64.b64encode(svg).decode("ascii")

html = html.replace('<link rel="stylesheet" href="./styles.css">', "<style>" + css + "</style>")
html = html.replace('<script src="./app.js"></script>', "<script>" + js + "</script>")
html = html.replace("./logo-ntt.svg", svg_uri)
html = html.replace("./logo-ntt.png", svg_uri)
html = html.replace(
    ' onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'block\'"',
    "",
)

worker = (
    "export default {\n"
    "  async fetch() {\n"
    f"    return new Response({json.dumps(html)}, {{\n"
    "      headers: {\n"
    "        'content-type': 'text/html; charset=utf-8',\n"
    "        'x-content-type-options': 'nosniff',\n"
    "        'referrer-policy': 'strict-origin-when-cross-origin',\n"
    "        'x-frame-options': 'DENY'\n"
    "      }\n"
    "    });\n"
    "  }\n"
    "};\n"
)
(root / "worker-single.mjs").write_text(worker, encoding="utf-8")
print("html", len(html), "worker", (root / "worker-single.mjs").stat().st_size)
