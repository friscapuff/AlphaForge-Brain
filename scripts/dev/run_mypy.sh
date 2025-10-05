#!/usr/bin/env bash
set -euo pipefail
poetry run mypy --config-file pyproject.toml .
