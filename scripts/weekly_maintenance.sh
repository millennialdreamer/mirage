#!/bin/bash
# weekly_maintenance.sh — MediaCrawler weekly automatic maintenance
#
# Does two things:
#   1. Pull the latest stealth.min.js from upstream (the anti-detection fingerprint library can go stale as browsers update)
#   2. Check if upstream MediaCrawler has new commits (may contain anti-detection fixes), only notify, do not auto-merge
#
# Usage:
#   weekly_maintenance.sh /path/to/MediaCrawler     # explicit path
#   weekly_maintenance.sh                            # auto-detects repo root when deployed under tools/
#
# Suggested cron (Monday 3 AM):
#   0 3 * * 1 /bin/bash /path/to/weekly_maintenance.sh /path/to/MediaCrawler

set -u

# ── Locate MediaCrawler root directory ───────────────────────────────────────
if [ -n "${1:-}" ]; then
    CRAWLER_DIR="$1"
else
    # No argument: assume this script is deployed under <root>/tools/, take parent directory
    CRAWLER_DIR="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)"
fi

if [ ! -f "$CRAWLER_DIR/config/base_config.py" ]; then
    echo "✗ $CRAWLER_DIR does not look like a MediaCrawler installation (missing config/base_config.py)"
    echo "  Usage: weekly_maintenance.sh /path/to/MediaCrawler"
    exit 1
fi

STEALTH_DST="$CRAWLER_DIR/libs/stealth.min.js"
STEALTH_URL="https://raw.githubusercontent.com/berstend/puppeteer-extra/master/packages/puppeteer-extra-plugin-stealth/evasions/_utils/stealth.min.js"
LOG="$CRAWLER_DIR/maintenance.log"
TMP="$STEALTH_DST.tmp"

echo "=== $(date '+%Y-%m-%d %H:%M') weekly maintenance start ($CRAWLER_DIR) ===" >> "$LOG"

# ── 1. Update stealth.min.js ─────────────────────────────────────────
echo "[stealth] downloading from upstream..." >> "$LOG"
mkdir -p "$(dirname "$STEALTH_DST")"
if /usr/bin/curl -fsSL --max-time 30 "$STEALTH_URL" -o "$TMP" 2>>"$LOG"; then
    # Validate: non-empty and contains stealth signature string before overwriting
    if [ -s "$TMP" ] && /usr/bin/grep -q "webdriver" "$TMP"; then
        /bin/mv "$TMP" "$STEALTH_DST"
        echo "[stealth] ✓ update succeeded ($(wc -c < "$STEALTH_DST" | tr -d ' ') bytes)" >> "$LOG"
    else
        /bin/rm -f "$TMP"
        echo "[stealth] ⚠ downloaded content is invalid, keeping previous version" >> "$LOG"
    fi
else
    /bin/rm -f "$TMP"
    echo "[stealth] ⚠ download failed (network?), keeping previous version" >> "$LOG"
fi

# ── 2. Check upstream for new commits ────────────────────────────────────────
echo "[upstream] checking latest GitHub status..." >> "$LOG"
cd "$CRAWLER_DIR" || exit 1
if [ -d .git ] && /usr/bin/git fetch origin --quiet 2>>"$LOG"; then
    BRANCH="$(/usr/bin/git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
    BEHIND=$(/usr/bin/git rev-list "HEAD..origin/$BRANCH" --count 2>/dev/null || echo 0)
    if [ "$BEHIND" -gt 0 ]; then
        echo "[upstream] ⚠ upstream has $BEHIND new commits, may contain anti-detection fixes" >> "$LOG"
        /usr/bin/git log "origin/$BRANCH" --oneline -5 >> "$LOG" 2>/dev/null
        echo "[upstream]   before merging back up your hardening: apply_hardening.py <root> --revert, then git pull, then re-apply" >> "$LOG"
        # macOS desktop notification (ignored automatically on non-macOS)
        /usr/bin/osascript -e "display notification \"MediaCrawler upstream has $BEHIND new commits\" with title \"Xiaohongshu crawler maintenance\"" 2>/dev/null || true
    else
        echo "[upstream] ✓ already up to date" >> "$LOG"
    fi
else
    echo "[upstream] ⚠ not a git repository or fetch failed, skipping" >> "$LOG"
fi

echo "=== maintenance complete ===" >> "$LOG"
echo "" >> "$LOG"
