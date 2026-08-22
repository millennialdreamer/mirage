# -*- coding: utf-8 -*-
"""
One-click switch MediaCrawler "safe / normal / fast" profiles

Usage:
    python config/safe_profile.py            # no args -> show current status
    python config/safe_profile.py safe       # switch to safe profile (most stable, slowest)
    python config/safe_profile.py normal     # switch to normal profile (balanced)
    python config/safe_profile.py fast       # switch to fast profile (fast, easily triggers risk control)

On first switch, the original config is automatically backed up to config/base_config.py.bak.
"""

import os
import re
import shutil
import sys

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "base_config.py")
BACKUP_PATH = CONFIG_PATH + ".bak"

PROFILES = {
    "safe":   {"CRAWLER_MAX_SLEEP_SEC": 6, "CRAWLER_MAX_NOTES_COUNT": 8,  "MAX_CONCURRENCY_NUM": 1},
    "normal": {"CRAWLER_MAX_SLEEP_SEC": 3, "CRAWLER_MAX_NOTES_COUNT": 15, "MAX_CONCURRENCY_NUM": 1},
    "fast":   {"CRAWLER_MAX_SLEEP_SEC": 1, "CRAWLER_MAX_NOTES_COUNT": 30, "MAX_CONCURRENCY_NUM": 3},
}


def read_current() -> dict:
    """Parse current values from base_config.py."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        text = f.read()
    out = {}
    for key in ("CRAWLER_MAX_SLEEP_SEC", "CRAWLER_MAX_NOTES_COUNT", "MAX_CONCURRENCY_NUM"):
        m = re.search(rf"^{key}\s*=\s*(\d+)", text, re.MULTILINE)
        out[key] = int(m.group(1)) if m else None
    return out


def apply_profile(name: str) -> None:
    """Write the specified profile's values back to base_config.py."""
    if name not in PROFILES:
        sys.exit(f"Unknown profile: {name}. Options: {', '.join(PROFILES)}")

    if not os.path.exists(BACKUP_PATH):
        shutil.copy2(CONFIG_PATH, BACKUP_PATH)
        print(f"✓ Original config backed up → {BACKUP_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    for key, value in PROFILES[name].items():
        text, n = re.subn(
            rf"^({key}\s*=\s*)\d+",
            rf"\g<1>{value}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if n == 0:
            print(f"⚠ {key} not found, skipping")

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"✓ Switched to '{name}' profile")


def print_status(current: dict) -> None:
    """Show current profile + estimated crawl rate."""
    # Infer current profile (any mismatch counts as 'custom')
    matched = next(
        (name for name, vals in PROFILES.items() if all(current.get(k) == v for k, v in vals.items())),
        "custom",
    )

    sleep_sec = current.get("CRAWLER_MAX_SLEEP_SEC") or 0
    avg_jitter = sleep_sec * 1.15  # average of 0.7x~1.6x
    notes_per_run = current.get("CRAWLER_MAX_NOTES_COUNT") or 0
    # about 2 sleeps per note (pagination + detail fetch), conservative estimate
    estimated_seconds = notes_per_run * avg_jitter * 2

    print("=" * 50)
    print(f" Current profile: {matched}")
    print("-" * 50)
    print(f" CRAWLER_MAX_SLEEP_SEC     = {current['CRAWLER_MAX_SLEEP_SEC']}  (actual jitter ~{sleep_sec*0.7:.1f}s to {sleep_sec*1.6:.1f}s)")
    print(f" CRAWLER_MAX_NOTES_COUNT   = {current['CRAWLER_MAX_NOTES_COUNT']}  (per-run max)")
    print(f" MAX_CONCURRENCY_NUM       = {current['MAX_CONCURRENCY_NUM']}  (concurrency)")
    print("-" * 50)
    if notes_per_run:
        print(f" Estimated time to crawl {notes_per_run} notes: ~{estimated_seconds:.0f}s ({estimated_seconds/60:.1f} min)")
        per_100 = (100 / notes_per_run) * estimated_seconds
        print(f" Estimated time to crawl 100 notes: ~{per_100/60:.1f} min")
    print("=" * 50)
    print(" Switch profile: python config/safe_profile.py [safe|normal|fast]")
    if os.path.exists(BACKUP_PATH):
        print(f" Restore: cp {BACKUP_PATH} {CONFIG_PATH}")


def main():
    if len(sys.argv) >= 2:
        apply_profile(sys.argv[1])
    print_status(read_current())


if __name__ == "__main__":
    main()
