#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_apply_hardening.py — apply_hardening idempotency unit tests

Run:
  python tests/test_apply_hardening.py

Coverage:
  - After patching a minimal fake core.py, a second patch changes nothing (idempotent)
  - Verify the MARK marker is actually injected
  - --dry-run does not write to disk (file content unchanged)
"""

import os
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_ROOT, "scripts")
sys.path.insert(0, _SCRIPTS)

# apply_hardening has no side effects on import, safe to import
import apply_hardening as ah

_pass = 0
_fail = 0


def check(name, cond, detail=""):
    global _pass, _fail
    if cond:
        print(f"  PASS  {name}")
        _pass += 1
    else:
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))
        _fail += 1


# ────────────────────────────────────────────────────────────────────
# Minimal fake MediaCrawler directory structure
# ────────────────────────────────────────────────────────────────────
FAKE_BASE_CONFIG = """\
# fake base_config.py
CRAWLER_MAX_SLEEP_SEC = 3
CRAWLER_MAX_NOTES_COUNT = 50
MAX_CONCURRENCY_NUM = 3
ENABLE_CDP_MODE = False
CDP_CONNECT_EXISTING = False
HEADLESS = True
SAVE_LOGIN_STATE = False
"""

# core.py minimal valid version: includes import asyncio / async def search / fixed sleep anchor
FAKE_CORE = """\
import asyncio

class XhsCrawler:
    async def search(self):
        await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

    async def get_notes(self):
        await asyncio.sleep(crawl_interval)
"""

def make_fake_mc(tmpdir, platform="xhs"):
    """Build a minimal MediaCrawler directory tree under tmpdir."""
    pdir = ah.PLATFORMS[platform][0]
    cfg_dir = os.path.join(tmpdir, "config")
    media_dir = os.path.join(tmpdir, "media_platform", pdir)
    tools_dir = os.path.join(tmpdir, "tools")
    libs_dir = os.path.join(tmpdir, "libs")
    for d in [cfg_dir, media_dir, tools_dir, libs_dir]:
        os.makedirs(d, exist_ok=True)
    base_cfg = os.path.join(cfg_dir, "base_config.py")
    core = os.path.join(media_dir, "core.py")
    with open(base_cfg, "w") as f:
        f.write(FAKE_BASE_CONFIG)
    with open(core, "w") as f:
        f.write(FAKE_CORE)
    return {
        "base_config": base_cfg,
        "core": core,
        "cdp": os.path.join(tools_dir, "cdp_browser.py"),   # does not exist, L1 will skip
        "stealth": os.path.join(libs_dir, "stealth.min.js"),
        "platform": platform,
    }


# ────────────────────────────────────────────────────────────────────
# Test: base_config.py patch + idempotency
# ────────────────────────────────────────────────────────────────────
def test_base_config_idempotent():
    print("\n── base_config.py safe parameters + idempotency ──")
    with tempfile.TemporaryDirectory() as tmpdir:
        files = make_fake_mc(tmpdir)

        # first patch
        ah.patch_base_config(files["base_config"], dry=False)
        content_after_1 = open(files["base_config"]).read()

        # verify key params have been written
        for key, (val, _) in ah.SAFE_PARAMS.items():
            in_file = f"{key} = {val}" in content_after_1
            check(f"after first patch {key}={val}", in_file,
                  f"file content snippet: {content_after_1[:200]}")

        # second patch (idempotent: file content should be byte-for-byte unchanged)
        ah.patch_base_config(files["base_config"], dry=False)
        content_after_2 = open(files["base_config"]).read()
        check("second patch idempotent (content unchanged)",
              content_after_1 == content_after_2,
              "two results differ")


# ────────────────────────────────────────────────────────────────────
# Test: core.py patch + idempotency + MARK marker + syntax self-check
# ────────────────────────────────────────────────────────────────────
def test_core_idempotent():
    print("\n── core.py L2/L4/L5 + idempotency ──")
    with tempfile.TemporaryDirectory() as tmpdir:
        files = make_fake_mc(tmpdir)

        # first patch
        ah.patch_core(files["core"], dry=False, platform="xhs")
        content_after_1 = open(files["core"]).read()

        # verify MARK marker injection
        check("core.py contains MARK marker", ah.MARK in content_after_1,
              "MARK [xhs-stealth] marker not found")

        # verify L2 jitter
        check("core.py L2 jitter injection",
              "L2 jitter" in content_after_1)

        # verify L4 warm-up
        check("core.py L4 warm-up injection",
              "L4: human warm-up" in content_after_1)

        # verify Python syntax is valid
        import ast
        try:
            ast.parse(content_after_1)
            syntax_ok = True
        except SyntaxError:
            syntax_ok = False
        check("core.py syntax valid after patch", syntax_ok)

        # second patch (idempotent)
        ah.patch_core(files["core"], dry=False, platform="xhs")
        content_after_2 = open(files["core"]).read()
        check("core.py second patch idempotent (content unchanged)",
              content_after_1 == content_after_2,
              "two results differ")


# ────────────────────────────────────────────────────────────────────
# Test: dry-run writes nothing to disk
# ────────────────────────────────────────────────────────────────────
def test_dry_run_no_write():
    print("\n── dry-run writes nothing to disk ──")
    with tempfile.TemporaryDirectory() as tmpdir:
        files = make_fake_mc(tmpdir)
        original_content = open(files["base_config"]).read()

        ah.patch_base_config(files["base_config"], dry=True)
        after_dry = open(files["base_config"]).read()

        check("after dry-run base_config content unchanged",
              original_content == after_dry,
              "dry-run unexpectedly wrote to file")


# ────────────────────────────────────────────────────────────────────
# Test: backup mechanism (first backup, second does not overwrite)
# ────────────────────────────────────────────────────────────────────
def test_backup_idempotent():
    print("\n── backup mechanism ──")
    with tempfile.TemporaryDirectory() as tmpdir:
        files = make_fake_mc(tmpdir)
        path = files["base_config"]
        bak = path + ah.BAK_SUFFIX

        # apply first patch (triggers backup)
        ah.patch_base_config(path, dry=False)
        check(".bak exists after first patch", os.path.exists(bak))

        # record .bak mtime
        mtime1 = os.path.getmtime(bak)

        # apply second patch (idempotent, should not trigger backup overwriting existing .bak)
        ah.patch_base_config(path, dry=False)
        mtime2 = os.path.getmtime(bak)

        check("second patch does not overwrite .bak (protects the original version)",
              mtime1 == mtime2,
              f"mtime1={mtime1} mtime2={mtime2}")


# ────────────────────────────────────────────────────────────────────
# Main entry
# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_base_config_idempotent()
    test_core_idempotent()
    test_dry_run_no_write()
    test_backup_idempotent()

    print(f"\n{'='*40}")
    total = _pass + _fail
    print(f"Result: {_pass}/{total} PASS, {_fail} FAIL")
    if _fail:
        print("FAIL")
        sys.exit(1)
    else:
        print("PASS")
        sys.exit(0)
