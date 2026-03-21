#!/usr/bin/env bash
set -euo pipefail

echo "==> Ruff"
uv run ruff check src

echo "==> MyPy"
uv run mypy src

echo "==> Pylint"
uv run pylint src

echo "==> Radon"
uv run radon cc --show-complexity src -a

echo "✔ All checks passed"
