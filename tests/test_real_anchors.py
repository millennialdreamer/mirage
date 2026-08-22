# -*- coding: utf-8 -*-
"""
Real anchor regression — directly targets apply_hardening's core risk surface:
will rewriting real third-party source with fragile regex miss anchors or break syntax?

Two lines of defense:
  1) Portable layer: built-in search signature variants collected from real MediaCrawler 7 platforms (2026-06),
     runnable in any environment, locks down the "code shapes seen in the real world"
     to prevent upstream drift from silently breaking anchors.
  2) Real environment layer (optional): when a local real MediaCrawler is detected,
     full regression against the original core.py of 7 platforms;
     other machines skip automatically, no CI blockage.

Run via `pytest tests/test_real_anchors.py`, or directly via `python3 tests/test_real_anchors.py`.
"""
import ast
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
AH = os.path.join(SCRIPTS, "apply_hardening.py")
_spec = importlib.util.spec_from_file_location("ah", AH)
ah = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ah)

# search signature variants collected from real MediaCrawler 7 platforms (2026-06, verified to hit)
REAL_SIGNATURES = [
    "    async def search(self) -> None:",   # xhs / dy / tieba / zhihu
    "    async def search(self):",            # ks / bili / wb
]

def _find_real_mediacrawler() -> str:
    """Locate a real MediaCrawler for regression (skip the real-environment layer if absent, no CI impact).

    Priority: env var MIRAGE_TEST_MEDIACRAWLER > common install location auto-detection.
    (No hard-coded personal paths — that would leak local directory structure and is useless to other contributors.)
    """
    env = os.environ.get("MIRAGE_TEST_MEDIACRAWLER", "").strip()
    if env and os.path.isdir(env):
        return env
    home = os.path.expanduser("~")
    for base in (os.path.join(home, "Documents"), home, os.path.join(home, "projects")):
        if not os.path.isdir(base):
            continue
        try:
            for entry in os.listdir(base):
                cand = os.path.join(base, entry)
                if entry == "MediaCrawler" and os.path.isfile(
                        os.path.join(cand, "config", "base_config.py")):
                    return cand
                nested = os.path.join(cand, "MediaCrawler")   # probe one level deeper
                if os.path.isdir(cand) and os.path.isfile(
                        os.path.join(nested, "config", "base_config.py")):
                    return nested
        except OSError:
            continue
    return ""


REAL_MC = _find_real_mediacrawler()
PLATS = {"xhs": "xhs", "dy": "douyin", "ks": "kuaishou", "bili": "bilibili",
         "wb": "weibo", "tieba": "tieba", "zhihu": "zhihu"}


def _fake_core(signature):
    return (
        "import asyncio\n\n"
        "class Crawler:\n"
        f"{signature}\n"
        '        """search docstring"""\n'
        "        await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)\n"
        "        await asyncio.sleep(crawl_interval)\n\n"
        "    async def other(self):\n"
        "        pass\n"
    )


def _build_fake_root(core_src, pdir="xhs"):
    root = tempfile.mkdtemp()
    for d in (["config"], ["media_platform", pdir], ["tools"], ["libs"]):
        os.makedirs(os.path.join(root, *d))
    ah.write(os.path.join(root, "config", "base_config.py"),
        "CRAWLER_MAX_SLEEP_SEC = 1\nCRAWLER_MAX_NOTES_COUNT = 20\nMAX_CONCURRENCY_NUM = 3\n"
        "ENABLE_CDP_MODE = False\nCDP_CONNECT_EXISTING = False\nHEADLESS = True\nSAVE_LOGIN_STATE = False\n")
    ah.write(os.path.join(root, "media_platform", pdir, "core.py"), core_src)
    ah.write(os.path.join(root, "tools", "cdp_browser.py"),
        "class CDPBrowserManager:\n    async def launch(self):\n"
        "        browser_context = object()\n        return browser_context\n")
    ah.write(os.path.join(root, "libs", "stealth.min.js"), "// webdriver\n" + "x" * 1200)
    return root


def _apply(root, alias="xhs"):
    return subprocess.run([sys.executable, AH, root, "-p", alias], capture_output=True, text=True)


def test_real_signature_variants_all_hit():
    """Every search signature shape seen in the real world must hit L2/L4/L5, and the patched source must remain valid AST."""
    for sig in REAL_SIGNATURES:
        root = _build_fake_root(_fake_core(sig))
        try:
            r = _apply(root)
            assert r.returncode == 0, f"apply failed ({sig}):\n{r.stdout}{r.stderr}"
            out = ah.read(os.path.join(root, "media_platform", "xhs", "core.py"))
            ast.parse(out)                                       # patch must not break syntax
            assert "L2 jitter" in out, f"L2 anchor miss: {sig}"
            assert "L4: human warm-up" in out, f"L4 anchor miss: {sig}"
            assert "_xhs_stealth_human_activity" in out, f"L5 anchor miss: {sig}"
        finally:
            shutil.rmtree(root)


def test_real_mediacrawler_7platforms():
    """When a real MediaCrawler exists locally, run full regression on the original core.py of 7 platforms; otherwise skip."""
    if not os.path.isdir(REAL_MC):
        print("  (skip) no local real MediaCrawler, portable layer only")
        return

    def real_core(pdir):
        cur = os.path.join(REAL_MC, "media_platform", pdir, "core.py")
        bak = cur + ah.BAK_SUFFIX
        return bak if os.path.isfile(bak) else cur   # hardened platforms use the .bak original

    def real_file(rel):
        cur = os.path.join(REAL_MC, rel)
        bak = cur + ah.BAK_SUFFIX
        return bak if os.path.isfile(bak) else cur

    for alias, pdir in PLATS.items():
        rc = real_core(pdir)
        root = tempfile.mkdtemp()
        try:
            for d in (["config"], ["media_platform", pdir], ["tools"], ["libs"]):
                os.makedirs(os.path.join(root, *d))
            shutil.copy2(real_file("config/base_config.py"), os.path.join(root, "config", "base_config.py"))
            shutil.copy2(rc, os.path.join(root, "media_platform", pdir, "core.py"))
            cdp = real_file("tools/cdp_browser.py")
            if os.path.isfile(cdp):
                shutil.copy2(cdp, os.path.join(root, "tools", "cdp_browser.py"))
            ah.write(os.path.join(root, "libs", "stealth.min.js"), "// webdriver\n" + "x" * 1200)
            r = _apply(root, alias)
            assert r.returncode == 0, f"{alias} apply failed:\n{r.stdout}{r.stderr}"
            out = ah.read(os.path.join(root, "media_platform", pdir, "core.py"))
            ast.parse(out)                                       # real code must not break after patch
            assert "L4: human warm-up" in out, f"{alias} L4 anchor miss -- real signature incompatible"
        finally:
            shutil.rmtree(root)


if __name__ == "__main__":
    test_real_signature_variants_all_hit()
    print("✓ real signature variants all hit (portable layer)")
    test_real_mediacrawler_7platforms()
    print("✓ real MediaCrawler 7-platform regression passed (or skipped)")
    print("🎉 test_real_anchors all passed")
