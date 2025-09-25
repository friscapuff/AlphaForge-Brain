from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--history", default="zz_artifacts/type_hygiene/metrics_history.json"
    )
    p.add_argument("--event", default="ci_append")
    p.add_argument("--baseline-errors", type=int, required=True)
    p.add_argument("--strictplus-errors", type=int, required=True)
    p.add_argument("--strictplus-ruff-violations", type=int, required=True)
    return p.parse_args()


def load_hist(path: pathlib.Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return data
    except FileNotFoundError:
        return []
    except Exception:
        return []


def main() -> int:
    ns = parse_args()
    path = pathlib.Path(ns.history)
    path.parent.mkdir(parents=True, exist_ok=True)
    hist = load_hist(path)
    # Config provenance (hashes of relevant config files)
    config_files = [
        pathlib.Path("mypy.ini"),
        pathlib.Path("mypy.strictplus.ini"),
        pathlib.Path("ruff.strictplus.toml"),
        pathlib.Path("pyproject.toml"),
        pathlib.Path("pytest.ini"),
    ]
    config_hashes = {}
    for cf in config_files:
        try:
            data = cf.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            config_hashes[str(cf)] = digest
        except FileNotFoundError:
            config_hashes[str(cf)] = None
    entry = {
        "timestamp_utc": dt.datetime.utcnow().isoformat() + "Z",
        "event": ns.event,
        "baseline_errors": ns.baseline_errors,
        "strictplus_errors": ns.strictplus_errors,
        "strictplus_ruff_violations": ns.strictplus_ruff_violations,
        "config_hashes": config_hashes,
    }
    hist.append(entry)
    path.write_text(json.dumps(hist, indent=2), encoding="utf-8")
    print(f"Appended metrics entry: {entry}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
