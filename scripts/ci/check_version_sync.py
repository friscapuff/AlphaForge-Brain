import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PYPROJECT = ROOT / "pyproject.toml"
OPENAPI_YAML = ROOT / "specs" / "001-initial-dual-tier" / "contracts" / "openapi.yaml"
OPENAPI_HTML = ROOT / "openapi.html"  # bundled redoc artifact
README = ROOT / "README.md"

VERSION_PATTERN = re.compile(r"version\s*=\s*\"(?P<ver>[^\"]+)\"")


def extract_version_pyproject() -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.strip().startswith("version") and "tool.poetry" in text:
            m = VERSION_PATTERN.search(line)
            if m:
                return m.group("ver")
    raise SystemExit("FAILED: Could not find version in pyproject.toml")


def extract_version_openapi_yaml() -> str:
    text = OPENAPI_YAML.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.strip().startswith("version:") and "info:" not in line:
            # naive first match inside info block; spec keeps it near top
            parts = line.split(":", 1)
            if len(parts) == 2:
                return parts[1].strip()
    raise SystemExit("FAILED: Could not find version in openapi.yaml")


def extract_version_openapi_html() -> str:
    text = OPENAPI_HTML.read_text(encoding="utf-8")
    # Search for embedded JSON __redoc_state info.version
    m = re.search(r'__redoc_state = .*?"version":"(?P<ver>[^"]+)"', text)
    if m:
        return m.group("ver")
    raise SystemExit("FAILED: Could not find info.version in openapi.html")


def assert_readme_contains(version: str) -> None:
    text = README.read_text(encoding="utf-8")
    if version not in text:
        raise SystemExit(f"FAILED: README missing version {version}")


async def probe_health(expected: str) -> dict:
    """Import the FastAPI app and issue an in-process request to /health.

    Tries httpx AsyncClient against ASGI app without binding a real port.
    Returns JSON response dict if successful.
    """
    try:
        import importlib

        import httpx  # third-party; types provided via stub dependency
    except Exception as e:  # pragma: no cover - dependency missing
        raise SystemExit(f"FAILED: health probe dependencies missing: {e}") from e

    app_mod = importlib.import_module("api.app")
    create_app = app_mod.create_app
    app = create_app()

    async with httpx.AsyncClient(app=app, base_url="http://testserver") as client:
        r = await client.get("/health")
        if r.status_code != 200:
            raise SystemExit(f"FAILED: /health status {r.status_code}")
        data = r.json()
        got = data.get("version")
        if got != expected:
            raise SystemExit(f"FAILED: /health version {got} != expected {expected}")
        return data


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Check version synchronization across artifacts"
    )
    p.add_argument(
        "--probe-health",
        action="store_true",
        help="Also import app and GET /health to verify runtime version",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)

    py_version = extract_version_pyproject()
    yaml_version = extract_version_openapi_yaml()
    html_version = extract_version_openapi_html()

    mismatches: list[tuple[str, str]] = []
    if yaml_version != py_version:
        mismatches.append(("openapi.yaml", yaml_version))
    if html_version != py_version:
        mismatches.append(("openapi.html", html_version))

    assert_readme_contains(py_version)

    health_payload = None
    if args.probe_health:
        try:
            import asyncio

            health_payload = asyncio.run(probe_health(py_version))
        except SystemExit:
            raise
        except Exception as e:  # pragma: no cover
            raise SystemExit(f"FAILED: health probe exception: {e}") from e

    if mismatches:
        details = ", ".join(f"{f}={v}" for f, v in mismatches)
        raise SystemExit(
            f"FAILED: Version drift vs pyproject ({py_version}): {details}"
        )

    output = {
        "status": "ok",
        "version": py_version,
        "checked": {
            "pyproject.toml": py_version,
            "openapi.yaml": yaml_version,
            "openapi.html": html_version,
            "README.md": "present",
        },
    }
    if health_payload is not None:
        output["health"] = {
            "version": health_payload.get("version"),
            "status": health_payload.get("status"),
        }

    print(json.dumps(output))


if __name__ == "__main__":  # pragma: no cover
    try:
        main()
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        raise
