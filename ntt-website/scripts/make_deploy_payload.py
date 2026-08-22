from pathlib import Path
import json

root = Path(__file__).resolve().parents[1]
worker = (root / "worker-single.mjs").read_text(encoding="utf-8")
code = (
    "async () => {\n"
    f"  const code = {json.dumps(worker)};\n"
    "  const b = 'F' + Date.now();\n"
    "  const metadata = JSON.stringify({\n"
    "    main_module: 'worker.mjs',\n"
    "    compatibility_date: '2026-08-17'\n"
    "  });\n"
    "  const body = [\n"
    "    '--' + b,\n"
    "    'Content-Disposition: form-data; name=\"metadata\"',\n"
    "    'Content-Type: application/json',\n"
    "    '',\n"
    "    metadata,\n"
    "    '--' + b,\n"
    "    'Content-Disposition: form-data; name=\"worker.mjs\"; filename=\"worker.mjs\"',\n"
    "    'Content-Type: application/javascript+module',\n"
    "    '',\n"
    "    code,\n"
    "    '--' + b + '--',\n"
    "  ].join('\\r\\n');\n"
    "  return cloudflare.request({\n"
    "    method: 'PUT',\n"
    "    path: `/accounts/${accountId}/workers/scripts/ntt-site`,\n"
    "    body,\n"
    "    contentType: 'multipart/form-data; boundary=' + b,\n"
    "    rawBody: true,\n"
    "  });\n"
    "}"
)
(root / "deploy_code.js").write_text(code, encoding="utf-8")
print(len(code))
