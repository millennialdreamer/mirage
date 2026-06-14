#!/bin/bash
# weekly_maintenance.sh — MediaCrawler 每周自动维护
#
# 做两件事：
#   1. 从上游拉最新 stealth.min.js（反检测指纹库会随浏览器更新而过时）
#   2. 检查上游 MediaCrawler 是否有新提交（可能含反检测修复），仅提醒不自动合并
#
# 用法：
#   weekly_maintenance.sh /path/to/MediaCrawler     # 显式指定
#   weekly_maintenance.sh                            # 部署到 tools/ 下时自动推断根目录
#
# 建议挂到 cron（每周一凌晨 3 点）：
#   0 3 * * 1 /bin/bash /path/to/weekly_maintenance.sh /path/to/MediaCrawler

set -u

# ── 定位 MediaCrawler 根目录 ───────────────────────────────────────
if [ -n "${1:-}" ]; then
    CRAWLER_DIR="$1"
else
    # 无参数：假设本脚本被部署在 <root>/tools/ 下，取上级目录
    CRAWLER_DIR="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)"
fi

if [ ! -f "$CRAWLER_DIR/config/base_config.py" ]; then
    echo "✗ $CRAWLER_DIR 不像 MediaCrawler 安装（缺 config/base_config.py）"
    echo "  用法：weekly_maintenance.sh /path/to/MediaCrawler"
    exit 1
fi

STEALTH_DST="$CRAWLER_DIR/libs/stealth.min.js"
STEALTH_URL="https://raw.githubusercontent.com/berstend/puppeteer-extra/master/packages/puppeteer-extra-plugin-stealth/evasions/_utils/stealth.min.js"
LOG="$CRAWLER_DIR/maintenance.log"
TMP="$STEALTH_DST.tmp"

echo "=== $(date '+%Y-%m-%d %H:%M') 周维护开始 ($CRAWLER_DIR) ===" >> "$LOG"

# ── 1. 更新 stealth.min.js ─────────────────────────────────────────
echo "[stealth] 从上游下载…" >> "$LOG"
mkdir -p "$(dirname "$STEALTH_DST")"
if /usr/bin/curl -fsSL --max-time 30 "$STEALTH_URL" -o "$TMP" 2>>"$LOG"; then
    # 校验：非空且含 stealth 特征串，才覆盖
    if [ -s "$TMP" ] && /usr/bin/grep -q "webdriver" "$TMP"; then
        /bin/mv "$TMP" "$STEALTH_DST"
        echo "[stealth] ✓ 更新成功 ($(wc -c < "$STEALTH_DST" | tr -d ' ') bytes)" >> "$LOG"
    else
        /bin/rm -f "$TMP"
        echo "[stealth] ⚠ 下载内容异常，保留原版本" >> "$LOG"
    fi
else
    /bin/rm -f "$TMP"
    echo "[stealth] ⚠ 下载失败（网络？），保留原版本" >> "$LOG"
fi

# ── 2. 检查上游是否有新提交 ────────────────────────────────────────
echo "[upstream] 检查 GitHub 最新状态…" >> "$LOG"
cd "$CRAWLER_DIR" || exit 1
if [ -d .git ] && /usr/bin/git fetch origin --quiet 2>>"$LOG"; then
    BRANCH="$(/usr/bin/git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
    BEHIND=$(/usr/bin/git rev-list "HEAD..origin/$BRANCH" --count 2>/dev/null || echo 0)
    if [ "$BEHIND" -gt 0 ]; then
        echo "[upstream] ⚠ 上游有 $BEHIND 个新提交，可能含反检测修复" >> "$LOG"
        /usr/bin/git log "origin/$BRANCH" --oneline -5 >> "$LOG" 2>/dev/null
        echo "[upstream]   合并前先备份你的加固：apply_hardening.py <root> --revert 后再 git pull 再重打" >> "$LOG"
        # macOS 桌面通知（非 macOS 自动忽略）
        /usr/bin/osascript -e "display notification \"MediaCrawler 上游有 $BEHIND 个新提交\" with title \"小红书爬虫维护\"" 2>/dev/null || true
    else
        echo "[upstream] ✓ 已是最新" >> "$LOG"
    fi
else
    echo "[upstream] ⚠ 非 git 仓库或 fetch 失败，跳过" >> "$LOG"
fi

echo "=== 维护完成 ===" >> "$LOG"
echo "" >> "$LOG"
