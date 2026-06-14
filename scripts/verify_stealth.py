# -*- coding: utf-8 -*-
"""
verify_stealth.py — 指纹自检：注入 stealth.min.js 后，读取关键自动化指纹，
判断"像真人 / 像机器人"。

⚠️ 本脚本会启动一个真实浏览器窗口，请**自己手动运行**。
   它是给你验证加固效果用的，不应由自动化代理代跑。

用法：
    python verify_stealth.py --stealth ../libs/stealth.min.js
    python verify_stealth.py --stealth /path/to/stealth.min.js --headless

依赖：playwright（pip install playwright && playwright install chromium）

原理：用同一个浏览器开两个上下文 —— 一个**不注入** stealth（对照组），
一个**注入** stealth（实验组），各读一遍指纹做对比。如果实验组的
navigator.webdriver 从 true 变 undefined、plugins 从空变非空，就说明
stealth 生效了。
"""

import argparse
import asyncio
import os
import sys

# 读取关键自动化指纹的 JS（自包含，不依赖任何外部检测页）
CHECK_JS = r"""() => {
  const out = {
    webdriver: navigator.webdriver,
    plugins: navigator.plugins ? navigator.plugins.length : 0,
    languages: (navigator.languages || []).join(','),
    hasChrome: !!window.chrome,
    permissionsApi: typeof navigator.permissions,
  };
  try {
    const gl = document.createElement('canvas').getContext('webgl');
    const ext = gl.getExtension('WEBGL_debug_renderer_info');
    out.webglVendor = gl.getParameter(ext.UNMASKED_VENDOR_WEBGL);
  } catch (e) {
    out.webglVendor = 'n/a';
  }
  return out;
}"""


async def probe(context, stealth_path):
    """在给定 context 上（可选注入 stealth）开页读指纹。"""
    if stealth_path:
        await context.add_init_script(path=stealth_path)
    page = await context.new_page()
    await page.goto("about:blank")
    fp = await page.evaluate(CHECK_JS)
    await page.close()
    return fp


def verdict(fp):
    """根据指纹给出机器人嫌疑点列表（空列表 = 干净）。"""
    flags = []
    if fp.get("webdriver"):
        flags.append("navigator.webdriver = true  ← 头号机器人特征")
    if fp.get("plugins", 0) == 0:
        flags.append("navigator.plugins 为空  ← 无头/自动化常见")
    if not fp.get("hasChrome"):
        flags.append("window.chrome 缺失  ← 非真实 Chrome 嫌疑")
    return flags


def show(title, fp):
    print(f"\n  【{title}】")
    print(f"    navigator.webdriver : {fp.get('webdriver')}")
    print(f"    navigator.plugins   : {fp.get('plugins')} 个")
    print(f"    navigator.languages : {fp.get('languages')}")
    print(f"    window.chrome       : {fp.get('hasChrome')}")
    print(f"    permissions API     : {fp.get('permissionsApi')}")
    print(f"    WebGL vendor        : {fp.get('webglVendor')}")
    flags = verdict(fp)
    if flags:
        for f in flags:
            print(f"    ⚠ {f}")
    else:
        print(f"    ✓ 未发现明显机器人特征")
    return flags


async def run(stealth_path, headless):
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        sys.exit("✗ 未安装 playwright。先跑：pip install playwright && playwright install chromium")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        # 对照组：不注入
        ctx_a = await browser.new_context()
        fp_plain = await probe(ctx_a, None)
        await ctx_a.close()
        # 实验组：注入 stealth
        ctx_b = await browser.new_context()
        fp_stealth = await probe(ctx_b, stealth_path)
        await ctx_b.close()
        await browser.close()
    return fp_plain, fp_stealth


def main():
    ap = argparse.ArgumentParser(description="注入 stealth 后的指纹自检（请手动运行）")
    here = os.path.dirname(os.path.abspath(__file__))
    default_stealth = os.path.normpath(os.path.join(here, "..", "libs", "stealth.min.js"))
    ap.add_argument("--stealth", default=default_stealth,
                    help=f"stealth.min.js 路径（默认 {default_stealth}）")
    ap.add_argument("--headless", action="store_true",
                    help="无头模式运行（默认有窗口，便于你亲眼看）")
    args = ap.parse_args()

    if not os.path.isfile(args.stealth):
        print(f"⚠ 找不到 stealth.min.js：{args.stealth}")
        print("  实验组将退化为'不注入'，对比将无意义。请用 --stealth 指定正确路径。")
        stealth_path = None
    else:
        stealth_path = args.stealth
        print(f"使用 stealth：{stealth_path}（{os.path.getsize(stealth_path)//1024}KB）")

    print("启动浏览器自检中……（这是你手动发起的验证）")
    fp_plain, fp_stealth = asyncio.run(run(stealth_path, args.headless))

    flags_plain = show("对照组 · 未注入 stealth", fp_plain)
    flags_stealth = show("实验组 · 已注入 stealth", fp_stealth)

    print("\n═══ 结论 ═══")
    if stealth_path and len(flags_stealth) < len(flags_plain):
        print(f"  ✓ stealth 生效：机器人特征从 {len(flags_plain)} 项降到 {len(flags_stealth)} 项")
    elif stealth_path and not flags_stealth:
        print("  ✓ 实验组无机器人特征，stealth 工作正常")
    elif not stealth_path:
        print("  ? 未提供 stealth.min.js，无法对比")
    else:
        print("  ⚠ 注入后特征未减少，请检查 stealth.min.js 是否正确加载")


if __name__ == "__main__":
    main()
