#!/bin/bash
# examples/harden_all.sh — common invocations for apply_hardening.py
#
# Note: this is a demo script and cannot be run directly (replace the path with your own MediaCrawler install path).
#       Windows users: see examples/README.md for equivalent Python calls.

MC="/path/to/MediaCrawler"  # ← change to your MediaCrawler install path

# ── 1. dry-run first to see what will change, no writes to disk ──────────────────────────────────
python scripts/apply_hardening.py "$MC" -p xhs --dry-run

# ── 2. apply patches for real (default platform = xhs) ────────────────────────────────────
python scripts/apply_hardening.py "$MC"

# ── 3. harden all 7 platforms at once ───────────────────────────────────────────
python scripts/apply_hardening.py "$MC" -p all

# ── 4. health check: see whether each hardening layer is active ──────────────────────────────────
python scripts/apply_hardening.py "$MC" -p all --check

# ── 5. fully restore from backup (undo all changes) ─────────────────────────────────
python scripts/apply_hardening.py "$MC" -p xhs --revert

# ── 6. cross-platform weekly maintenance (Python version, works on Windows/Mac/Linux) ──────────────
python scripts/weekly_maintenance.py "$MC"
