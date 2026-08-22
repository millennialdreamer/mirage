#!/usr/bin/env bash
# Local CI — one-shot pytest + benchmark self-check + ruff + mypy.
# Replaces GitHub Actions (Actions disabled by quota in this environment); ruff/mypy missing will skip gracefully and prompt install.
# Usage:  bash scripts/ci.sh
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1          # Run from repo root consistently, ensure ruff/mypy read pyproject config
fail=0
step() { echo; echo "━━ $1 ━━"; }

step "pytest (tests)"
if python3 -c "import pytest" 2>/dev/null; then
    python3 -m pytest "$ROOT/tests" -q || fail=1
else
    echo "  ⚠ pytest not installed, skipping → pip install pytest"
fi

step "benchmark scoring logic self-check (no browser)"
if python3 "$ROOT/scripts/fingerprint_benchmark.py" --self-test >/dev/null 2>&1; then
    echo "  ✓ fingerprint_benchmark self-test passed"
else
    echo "  ✗ benchmark self-test failed"; fail=1
fi

step "ruff (lint)"
if command -v ruff >/dev/null 2>&1; then
    ruff check "$ROOT/scripts" || fail=1
else
    echo "  ⚠ ruff not installed, skipping → pip install ruff"
fi

step "mypy (type check · all scripts)"
if command -v mypy >/dev/null 2>&1; then
    mypy "$ROOT/scripts" --ignore-missing-imports || fail=1
else
    echo "  ⚠ mypy not installed, skipping → pip install mypy"
fi

echo
if [ "$fail" -eq 0 ]; then
    echo "🎉 Local CI all green"
else
    echo "✗ Local CI has failures (see above)"; exit 1
fi
