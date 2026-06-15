#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_apply_hardening.py — apply_hardening 幂等性单元测试

运行方式：
  python tests/test_apply_hardening.py

测试覆盖：
  - 对一份最小假 core.py 打补丁后，第二次打补丁零变化（幂等）
  - 验证 MARK 标记确实被注入
  - --dry-run 不落盘（文件内容不变）
"""

import os
import shutil
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_ROOT, "scripts")
sys.path.insert(0, _SCRIPTS)

# apply_hardening 在导入时不做任何副作用，安全 import
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
# 最小假 MediaCrawler 目录结构
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

# core.py 最小有效版本：含 import asyncio / async def search / 固定 sleep 锚点
FAKE_CORE = """\
import asyncio

class XhsCrawler:
    async def search(self):
        await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

    async def get_notes(self):
        await asyncio.sleep(crawl_interval)
"""

def make_fake_mc(tmpdir, platform="xhs"):
    """在 tmpdir 下建最小 MediaCrawler 目录树。"""
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
        "cdp": os.path.join(tools_dir, "cdp_browser.py"),   # 不存在，L1 会跳过
        "stealth": os.path.join(libs_dir, "stealth.min.js"),
        "platform": platform,
    }


# ────────────────────────────────────────────────────────────────────
# 测试：base_config.py 补丁 + 幂等
# ────────────────────────────────────────────────────────────────────
def test_base_config_idempotent():
    print("\n── base_config.py 安全参数 + 幂等 ──")
    with tempfile.TemporaryDirectory() as tmpdir:
        files = make_fake_mc(tmpdir)

        # 第一次打补丁
        ah.patch_base_config(files["base_config"], dry=False)
        content_after_1 = open(files["base_config"]).read()

        # 验证关键参数已被写入
        for key, (val, _) in ah.SAFE_PARAMS.items():
            in_file = f"{key} = {val}" in content_after_1
            check(f"第一次补丁后 {key}={val}", in_file,
                  f"文件内容片段：{content_after_1[:200]}")

        # 第二次打补丁（幂等：文件内容应一字不变）
        ah.patch_base_config(files["base_config"], dry=False)
        content_after_2 = open(files["base_config"]).read()
        check("二次打补丁幂等（内容零变化）",
              content_after_1 == content_after_2,
              "两次结果不一致")


# ────────────────────────────────────────────────────────────────────
# 测试：core.py 补丁 + 幂等 + MARK 标记 + 语法自检
# ────────────────────────────────────────────────────────────────────
def test_core_idempotent():
    print("\n── core.py L2/L4/L5 + 幂等 ──")
    with tempfile.TemporaryDirectory() as tmpdir:
        files = make_fake_mc(tmpdir)

        # 第一次打补丁
        ah.patch_core(files["core"], dry=False, platform="xhs")
        content_after_1 = open(files["core"]).read()

        # 验证 MARK 标记注入
        check("core.py 含 MARK 标记", ah.MARK in content_after_1,
              "未找到 [xhs-stealth] 标记")

        # 验证 L2 抖动
        check("core.py L2 jitter 注入",
              "L2 jitter" in content_after_1)

        # 验证 L4 预热
        check("core.py L4 warm-up 注入",
              "L4: human warm-up" in content_after_1)

        # 验证 Python 语法合法
        import ast
        try:
            ast.parse(content_after_1)
            syntax_ok = True
        except SyntaxError as e:
            syntax_ok = False
        check("core.py 补丁后语法合法", syntax_ok)

        # 第二次打补丁（幂等）
        ah.patch_core(files["core"], dry=False, platform="xhs")
        content_after_2 = open(files["core"]).read()
        check("core.py 二次打补丁幂等（内容零变化）",
              content_after_1 == content_after_2,
              "两次结果不一致")


# ────────────────────────────────────────────────────────────────────
# 测试：dry-run 不落盘
# ────────────────────────────────────────────────────────────────────
def test_dry_run_no_write():
    print("\n── dry-run 不落盘 ──")
    with tempfile.TemporaryDirectory() as tmpdir:
        files = make_fake_mc(tmpdir)
        original_content = open(files["base_config"]).read()

        ah.patch_base_config(files["base_config"], dry=True)
        after_dry = open(files["base_config"]).read()

        check("dry-run 后 base_config 内容不变",
              original_content == after_dry,
              "dry-run 意外写入了文件")


# ────────────────────────────────────────────────────────────────────
# 测试：backup 机制（首次备份，二次不覆盖）
# ────────────────────────────────────────────────────────────────────
def test_backup_idempotent():
    print("\n── backup 机制 ──")
    with tempfile.TemporaryDirectory() as tmpdir:
        files = make_fake_mc(tmpdir)
        path = files["base_config"]
        bak = path + ah.BAK_SUFFIX

        # 打第一次补丁（会触发 backup）
        ah.patch_base_config(path, dry=False)
        check("第一次打补丁后 .bak 存在", os.path.exists(bak))

        # 记录 .bak 修改时间
        mtime1 = os.path.getmtime(bak)

        # 打第二次补丁（幂等，不应触发 backup 覆盖已有 .bak）
        ah.patch_base_config(path, dry=False)
        mtime2 = os.path.getmtime(bak)

        check("二次打补丁不覆盖 .bak（保护最原始版本）",
              mtime1 == mtime2,
              f"mtime1={mtime1} mtime2={mtime2}")


# ────────────────────────────────────────────────────────────────────
# 主入口
# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_base_config_idempotent()
    test_core_idempotent()
    test_dry_run_no_write()
    test_backup_idempotent()

    print(f"\n{'='*40}")
    total = _pass + _fail
    print(f"结果：{_pass}/{total} PASS，{_fail} FAIL")
    if _fail:
        print("FAIL")
        sys.exit(1)
    else:
        print("PASS")
        sys.exit(0)
