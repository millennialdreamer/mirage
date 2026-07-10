#!/usr/bin/env bash
# 本地 CI —— 一键 pytest + benchmark 自检 + ruff + mypy。
# 代替 GitHub Actions（本环境额度禁 Actions）；ruff/mypy 没装会优雅跳过并提示安装。
# 用法：  bash scripts/ci.sh
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1          # 统一在 repo 根跑，确保 ruff/mypy 读到 pyproject 配置
fail=0
step() { echo; echo "━━ $1 ━━"; }

step "pytest（测试）"
if python3 -c "import pytest" 2>/dev/null; then
    python3 -m pytest "$ROOT/tests" -q || fail=1
else
    echo "  ⚠ 未装 pytest，跳过 → pip install pytest"
fi

step "benchmark 评分逻辑自检（无浏览器）"
if python3 "$ROOT/scripts/fingerprint_benchmark.py" --self-test >/dev/null 2>&1; then
    echo "  ✓ fingerprint_benchmark self-test 通过"
else
    echo "  ✗ benchmark self-test 失败"; fail=1
fi

step "ruff（lint）"
if command -v ruff >/dev/null 2>&1; then
    ruff check "$ROOT/scripts" || fail=1
else
    echo "  ⚠ 未装 ruff，跳过 → pip install ruff"
fi

step "mypy（类型检查 · 全 scripts）"
if command -v mypy >/dev/null 2>&1; then
    mypy "$ROOT/scripts" --ignore-missing-imports || fail=1
else
    echo "  ⚠ 未装 mypy，跳过 → pip install mypy"
fi

echo
if [ "$fail" -eq 0 ]; then
    echo "🎉 本地 CI 全绿"
else
    echo "✗ 本地 CI 有失败项（见上）"; exit 1
fi
