# -*- coding: utf-8 -*-
"""
真实锚点回归 —— 直击 apply_hardening 的核心风险面：
「用脆弱正则改写真实第三方源码」会不会 miss 锚点、会不会损坏语法。

两层防线：
  1) 可移植层：内置从真实 MediaCrawler 7 平台采集到的 search 签名变体（2026-06），
     任何环境可跑，锁住「真实世界见过的代码形态」，防上游漂移悄悄打穿锚点。
  2) 真实环境层（可选）：检测到本机真实 MediaCrawler 时，对 7 平台原始 core.py 全量回归；
     别的机器自动跳过，不阻断 CI。

既可 `pytest tests/test_real_anchors.py`，也可 `python3 tests/test_real_anchors.py` 直接跑。
"""
import os
import sys
import ast
import tempfile
import shutil
import subprocess
import importlib.util

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
AH = os.path.join(SCRIPTS, "apply_hardening.py")
_spec = importlib.util.spec_from_file_location("ah", AH)
ah = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ah)

# 从真实 MediaCrawler 7 平台采集到的 search 签名变体（2026-06，已验证命中）
REAL_SIGNATURES = [
    "    async def search(self) -> None:",   # xhs / dy / tieba / zhihu
    "    async def search(self):",            # ks / bili / wb
]

def _find_real_mediacrawler() -> str:
    """定位一份真实 MediaCrawler 用于回归（没有就跳过真实环境层，不影响 CI）。

    优先级：环境变量 MIRAGE_TEST_MEDIACRAWLER > 常见安装位置自动探测。
    （不写死任何个人路径——那既泄漏本机目录结构，对其他贡献者也无用。）
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
                nested = os.path.join(cand, "MediaCrawler")   # 再下探一层
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
    """真实世界见过的每种 search 签名，L2/L4/L5 都必须命中且补丁后 AST 正确。"""
    for sig in REAL_SIGNATURES:
        root = _build_fake_root(_fake_core(sig))
        try:
            r = _apply(root)
            assert r.returncode == 0, f"apply 失败 ({sig}):\n{r.stdout}{r.stderr}"
            out = ah.read(os.path.join(root, "media_platform", "xhs", "core.py"))
            ast.parse(out)                                       # 补丁不损坏语法
            assert "L2 jitter" in out, f"L2 锚点 miss: {sig}"
            assert "L4: human warm-up" in out, f"L4 锚点 miss: {sig}"
            assert "_xhs_stealth_human_activity" in out, f"L5 锚点 miss: {sig}"
        finally:
            shutil.rmtree(root)


def test_real_mediacrawler_7platforms():
    """本机有真实 MediaCrawler 时，对 7 平台原始 core.py 全量回归；没有则跳过。"""
    if not os.path.isdir(REAL_MC):
        print("  (skip) 本机无真实 MediaCrawler，仅跑可移植层")
        return

    def real_core(pdir):
        cur = os.path.join(REAL_MC, "media_platform", pdir, "core.py")
        bak = cur + ah.BAK_SUFFIX
        return bak if os.path.isfile(bak) else cur   # 加固过的平台用 .bak 原版

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
            assert r.returncode == 0, f"{alias} apply 失败:\n{r.stdout}{r.stderr}"
            out = ah.read(os.path.join(root, "media_platform", pdir, "core.py"))
            ast.parse(out)                                       # 真实代码补丁后不损坏
            assert "L4: human warm-up" in out, f"{alias} L4 锚点 miss —— 真实签名不兼容"
        finally:
            shutil.rmtree(root)


if __name__ == "__main__":
    test_real_signature_variants_all_hit()
    print("✓ 真实签名变体全命中（可移植层）")
    test_real_mediacrawler_7platforms()
    print("✓ 真实 MediaCrawler 7 平台回归通过（或已跳过）")
    print("🎉 test_real_anchors 全通过")
