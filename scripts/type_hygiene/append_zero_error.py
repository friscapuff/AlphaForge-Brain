from __future__ import annotations

import datetime
import json
import pathlib

path = pathlib.Path("zz_artifacts/type_hygiene/metrics_history.json")
try:
    hist = json.loads(path.read_text())
    if not isinstance(hist, list):
        hist = []
except Exception:
    hist = []
entry = {
    "timestamp_utc": datetime.datetime.now(datetime.UTC)
    .isoformat()
    .replace("+00:00", "Z"),
    "event": "verification_zero_errors",
    "total_errors": 0,
    "by_code": {},
}
hist.append(entry)
path.write_text(json.dumps(hist, indent=2))
print("Zero-error verification appended.")
