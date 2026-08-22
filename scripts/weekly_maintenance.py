#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
weekly_maintenance.py — MediaCrawler weekly automatic maintenance (cross-platform Python version)

Functionality is exactly the same as weekly_maintenance.sh, but runs on Windows/Mac/Linux:
  1. Pull latest stealth.min.js from upstream (anti-detection fingerprint library goes stale as browsers update)
  2. Check upstream MediaCrawler for new commits (reminder only, no auto merge)

Usage:
  python scripts/weekly_maintenance.py /path/to/MediaCrawler
  python scripts/weekly_maintenance.py          # When deployed under tools/, root is inferred automatically

Suggested schedule (Monday 3 AM):
  # Mac/Linux cron:
  0 3 * * 1 python /path/to/weekly_maintenance.py /path/to/MediaCrawler
  # Windows Task Scheduler: same command
"""

import os
import subprocess
import sys
import urllib.request
from datetime import datetime

STEALTH_URL = (
    "https://raw.githubusercontent.com/berstend/puppeteer-extra/master/"
    "packages/puppeteer-extra-plugin-stealth/evasions/_utils/stealth.min.js"
)


def locate_root(argv):
    """Locate MediaCrawler root: prefer CLI arg, otherwise infer (assumes script is under tools/)."""
    if len(argv) > 1:
        return os.path.abspath(argv[1])
    # No args: assume this script is deployed under <root>/tools/, take parent dir
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, ".."))


def validate_root(root):
    """Confirm it's a MediaCrawler installation."""
    marker = os.path.join(root, "config", "base_config.py")
    if not os.path.isfile(marker):
        print(f"✗ {root} doesn't look like a MediaCrawler installation (missing config/base_config.py)")
        print("  Usage: python weekly_maintenance.py /path/to/MediaCrawler")
        sys.exit(1)


def update_stealth(root, log):
    """Download latest stealth.min.js, validate then atomically replace."""
    dst = os.path.join(root, "libs", "stealth.min.js")
    tmp = dst + ".tmp"
    _log(log, "[stealth] Downloading from upstream...")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        with urllib.request.urlopen(STEALTH_URL, timeout=30) as resp:
            data = resp.read()
        # Validate: only overwrite if non-empty and contains stealth signature string
        if len(data) > 1000 and b"webdriver" in data:
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, dst)   # Atomic replace to avoid corruption from interruption
            _log(log, f"[stealth] ✓ Update succeeded ({len(data)} bytes)")
        else:
            _log(log, "[stealth] ⚠ Downloaded content abnormal, keeping existing version")
            if os.path.exists(tmp):
                os.remove(tmp)
    except Exception as e:
        _log(log, f"[stealth] ⚠ Download failed ({e}), keeping existing version")
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def check_upstream(root, log):
    """Check upstream for new commits; reminder only, no auto-merge."""
    _log(log, "[upstream] Checking latest GitHub status...")
    git_dir = os.path.join(root, ".git")
    if not os.path.isdir(git_dir):
        _log(log, "[upstream] ⚠ Not a git repository, skipping")
        return

    def _run(cmd):
        return subprocess.run(
            cmd, capture_output=True, text=True, cwd=root
        )

    # fetch origin
    r = _run(["git", "fetch", "origin", "--quiet"])
    if r.returncode != 0:
        _log(log, f"[upstream] ⚠ git fetch failed: {r.stderr.strip()}")
        return

    # Current branch name
    r_branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    branch = r_branch.stdout.strip() if r_branch.returncode == 0 else "main"

    # Number of commits behind
    r_count = _run(["git", "rev-list", f"HEAD..origin/{branch}", "--count"])
    try:
        behind = int(r_count.stdout.strip())
    except ValueError:
        behind = 0

    if behind > 0:
        _log(log, f"[upstream] ⚠ Upstream has {behind} new commit(s), may contain anti-detection fixes")
        r_log = _run(["git", "log", f"origin/{branch}", "--oneline", "-5"])
        if r_log.returncode == 0:
            for line in r_log.stdout.strip().splitlines():
                _log(log, f"[upstream]   {line}")
        _log(log, "[upstream]   Before merging, back up hardening first: apply_hardening.py <root> --revert, then git pull, then re-apply")
        # macOS desktop notification (silently ignored on non-macOS)
        _notify(f"MediaCrawler upstream has {behind} new commits", "Xiaohongshu crawler maintenance")
    else:
        _log(log, "[upstream] ✓ Already up to date")


def _log(log_path, msg):
    """Print to both terminal and log file."""
    print(msg)
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except OSError:
        pass


def _notify(message, title):
    """macOS desktop notification, silently ignored on non-macOS."""
    if sys.platform != "darwin":
        return
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{message}" with title "{title}"'],
            capture_output=True, timeout=5,
        )
    except Exception:
        pass


def main():
    root = locate_root(sys.argv)
    validate_root(root)

    log_path = os.path.join(root, "maintenance.log")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    _log(log_path, f"=== {ts} weekly maintenance start ({root}) ===")

    update_stealth(root, log_path)
    check_upstream(root, log_path)

    _log(log_path, "=== Maintenance complete ===")
    _log(log_path, "")


if __name__ == "__main__":
    main()
