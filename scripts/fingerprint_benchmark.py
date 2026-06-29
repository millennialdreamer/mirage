# -*- coding: utf-8 -*-
"""
fingerprint_benchmark.py — 可证明的拟人：给"加固前 vs 加固后"的浏览器指纹打分，
产出可存档、可对比、可写进 README 的**证据报告**，把"我说像人"变成"数据说像人"。

定位：verify_stealth.py 是"自检（特征在不在）"；本脚本是"benchmark（有多像人 + 出分 + 存档）"。

⚠️ 真实跑分会启动浏览器 —— 请 boss **自己手动跑**，AI 不代跑（与 verify_stealth 同一铁律）。
   评分逻辑无需浏览器即可自测：  python fingerprint_benchmark.py --self-test

用法：
    python fingerprint_benchmark.py --stealth ../libs/stealth.min.js      # 手动跑真分（开窗口）
    python fingerprint_benchmark.py --stealth ../libs/stealth.min.js --headless
    python fingerprint_benchmark.py --self-test                            # 只测评分逻辑(无浏览器)

依赖：playwright（仅真跑分需要；--self-test 不需要）

BotScore：0~100，越高越像机器人。加固应把分数显著拉低；报告记录降幅作为证据。
"""
import argparse
import asyncio
import json
import os
import sys
import time

# 采集指纹的 JS（自包含、不依赖外部检测页；async 以便查权限一致性）
EXTENDED_CHECK_JS = r"""() => {
  const out = {
    webdriver: navigator.webdriver,
    plugins: navigator.plugins ? navigator.plugins.length : 0,
    languages: (navigator.languages || []).join(','),
    hasChrome: !!window.chrome,
    permissionsApi: typeof navigator.permissions,
    ua: navigator.userAgent,
    platform: navigator.platform,
    hardwareConcurrency: navigator.hardwareConcurrency || 0,
    outerWidth: window.outerWidth,
    outerHeight: window.outerHeight,
  };
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    const ext = gl.getExtension('WEBGL_debug_renderer_info');
    out.webglVendor = gl.getParameter(ext.UNMASKED_VENDOR_WEBGL);
    out.webglRenderer = gl.getParameter(ext.UNMASKED_RENDERER_WEBGL);
  } catch (e) {
    out.webglVendor = 'n/a'; out.webglRenderer = 'n/a';
  }
  return out;
}"""

# 评分模型：每个维度命中"机器人特征"的扣分权重。BotScore = 命中权重和 / 总权重 * 100。
# 权重是经验判断：webdriver/headless-UA 是硬特征给高权重，软渲染等给低权重。
# 经国产 QA 审 + 终审裁决：移除了易在真人浏览器误报的 permMismatch，补入低误报的 languages；
# webdriver 30→25 配合多维度稀释，避免"单特征定生死"。全部维度均为低误报硬特征。
SIGNALS = [
    ("webdriver",  lambda fp: bool(fp.get("webdriver")),                          25, "navigator.webdriver=true（头号机器人特征）"),
    ("headlessUA", lambda fp: "headless" in str(fp.get("ua", "")).lower(),        18, "UserAgent 含 HeadlessChrome"),
    ("plugins",    lambda fp: int(fp.get("plugins", 0)) == 0,                     14, "navigator.plugins 为空"),
    ("languages",  lambda fp: not str(fp.get("languages", "")).strip(),           12, "navigator.languages 为空（无头常见）"),
    ("webglSW",    lambda fp: any(s in str(fp.get("webglRenderer", "")).lower()
                                  for s in ("swiftshader", "llvmpipe", "software")), 11, "WebGL 软渲染（无真实 GPU）"),
    ("chrome",     lambda fp: not fp.get("hasChrome"),                            10, "window.chrome 缺失（非真实 Chrome 嫌疑）"),
    ("outerZero",  lambda fp: int(fp.get("outerWidth", 1)) == 0 or int(fp.get("outerHeight", 1)) == 0, 10, "窗口外尺寸为 0（无头特征）"),
]
MAX_WEIGHT = sum(w for _, _, w, _ in SIGNALS)   # = 100


def _safe(fn, fp):
    try:
        return bool(fn(fp))
    except Exception:
        return False


def score_fingerprint(fp):
    """返回 (botscore 0~100, 命中的特征列表[(key,weight,why)])。"""
    hits = [(k, w, why) for (k, fn, w, why) in SIGNALS if _safe(fn, fp)]
    raw = sum(w for _, w, _ in hits)
    botscore = round(raw / MAX_WEIGHT * 100)
    return botscore, hits


def risk_level(botscore):
    """把 BotScore 映射成风险等级，避免对绝对数字过度解读。"""
    return "低" if botscore <= 20 else ("中" if botscore <= 50 else "高")


DISCLAIMER = ("本 BotScore 仅覆盖 7 个基础指纹维度，是相对基准分，不等于真实平台风控判定"
              "（真实维度更多、逻辑更复杂）；stealth 后现实预期约 5~30 分，0 分是理想化结果。")


def render_report(fp_plain, fp_stealth):
    """打印对比 + 返回可存档的报告 dict。"""
    bs_p, hits_p = score_fingerprint(fp_plain)
    bs_s, hits_s = score_fingerprint(fp_stealth)

    def block(title, fp, bs, hits):
        print(f"\n  【{title}】 BotScore = {bs}/100")
        print(f"    webdriver={fp.get('webdriver')}  plugins={fp.get('plugins')}  "
              f"chrome={fp.get('hasChrome')}  webglRenderer={fp.get('webglRenderer')}")
        for _, w, why in hits:
            print(f"    ⚠ (+{w}) {why}")
        if not hits:
            print("    ✓ 未命中任何机器人特征")

    block("对照组 · 未加固", fp_plain, bs_p, hits_p)
    block("实验组 · 已加固", fp_stealth, bs_s, hits_s)

    drop = bs_p - bs_s
    print("\n═══ 结论（证据）═══")
    print(f"  BotScore：{bs_p} → {bs_s}  （降低 {drop} 分，越低越像真人）")
    print(f"  风险等级：对照组【{risk_level(bs_p)}】→ 实验组【{risk_level(bs_s)}】")
    if drop >= 40:
        print("  ✓ 加固显著有效：抹掉了大部分机器人特征")
    elif drop > 0:
        print("  ~ 加固部分有效：仍有残留特征，建议核对 stealth.min.js 是否最新")
    else:
        print("  ⚠ 加固未见效：请检查 stealth 是否正确注入")
    print(f"  ⚠ {DISCLAIMER}")

    return {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "plain":   {"botscore": bs_p, "risk_level": risk_level(bs_p), "flags": [k for k, _, _ in hits_p], "fp": fp_plain},
        "stealth": {"botscore": bs_s, "risk_level": risk_level(bs_s), "flags": [k for k, _, _ in hits_s], "fp": fp_stealth},
        "improvement": drop,
        "max_weight": MAX_WEIGHT,
        "disclaimer": DISCLAIMER,
    }


async def _probe(context, stealth_path):
    if stealth_path:
        await context.add_init_script(path=stealth_path)
    page = await context.new_page()
    await page.goto("about:blank")
    fp = await page.evaluate(EXTENDED_CHECK_JS)
    await page.close()
    return fp


async def _run(stealth_path, headless):
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        sys.exit("✗ 未安装 playwright。先跑：pip install playwright && playwright install chromium")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        ctx_a = await browser.new_context()
        fp_plain = await _probe(ctx_a, None)
        await ctx_a.close()
        ctx_b = await browser.new_context()
        fp_stealth = await _probe(ctx_b, stealth_path)
        await ctx_b.close()
        await browser.close()
    return fp_plain, fp_stealth


# —— 自测用 mock 指纹：典型「裸 headless Chromium」与「加固后真 Chrome」——
MOCK_PLAIN = {
    "webdriver": True, "plugins": 0, "hasChrome": False, "languages": "",
    "ua": "Mozilla/5.0 ... HeadlessChrome/120.0 ...", "webglRenderer": "Google SwiftShader",
    "outerWidth": 0, "outerHeight": 0,
}
MOCK_STEALTH = {
    "webdriver": False, "plugins": 3, "hasChrome": True, "languages": "zh-CN,zh,en",
    "ua": "Mozilla/5.0 ... Chrome/120.0 Safari/537.36", "webglRenderer": "Apple M2",
    "outerWidth": 1280, "outerHeight": 800,
}


def self_test():
    """无浏览器验证评分逻辑：裸指纹应高分、加固指纹应低分、改善显著。"""
    bs_p, _ = score_fingerprint(MOCK_PLAIN)
    bs_s, _ = score_fingerprint(MOCK_STEALTH)
    assert bs_p >= 80, f"裸指纹 BotScore 应 ≥80，实际 {bs_p}"
    assert bs_s <= 15, f"加固指纹 BotScore 应 ≤15，实际 {bs_s}"
    assert bs_p - bs_s >= 60, f"改善应 ≥60，实际 {bs_p - bs_s}"
    rep = render_report(MOCK_PLAIN, MOCK_STEALTH)
    assert rep["improvement"] == bs_p - bs_s
    assert {"botscore", "flags", "fp", "risk_level"} <= set(rep["plain"])
    assert rep["disclaimer"], "报告必须带免责声明"
    assert rep["plain"]["risk_level"] == "高" and rep["stealth"]["risk_level"] == "低"
    assert isinstance(rep["stealth"]["flags"], list)
    # 单调性：去掉一个特征，分数必须下降
    less = dict(MOCK_PLAIN)
    less["webdriver"] = False
    assert score_fingerprint(less)[0] < bs_p, "去掉 webdriver 后分应下降"
    print("\n🎉 self-test 通过：评分单调、裸高加固低、改善显著、报告结构完整")


def main():
    ap = argparse.ArgumentParser(description="指纹 benchmark：加固前后 BotScore 对比（真跑请手动）")
    here = os.path.dirname(os.path.abspath(__file__))
    default_stealth = os.path.normpath(os.path.join(here, "..", "libs", "stealth.min.js"))
    ap.add_argument("--stealth", default=default_stealth, help="stealth.min.js 路径")
    ap.add_argument("--headless", action="store_true", help="无头运行（默认开窗口便于亲眼看）")
    ap.add_argument("--self-test", action="store_true", help="只测评分逻辑，不启动浏览器")
    ap.add_argument("--json", default="", help="把证据报告写到指定 JSON 路径")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    stealth_path = args.stealth if os.path.isfile(args.stealth) else None
    if not stealth_path:
        print(f"⚠ 找不到 stealth.min.js：{args.stealth}（实验组将退化为不注入，对比无意义）")
    else:
        print(f"使用 stealth：{stealth_path}（{os.path.getsize(stealth_path)//1024}KB）")

    print("启动浏览器跑分中……（这是你手动发起的验证）")
    fp_plain, fp_stealth = asyncio.run(_run(stealth_path, args.headless))
    report = render_report(fp_plain, fp_stealth)

    out_path = args.json or os.path.expanduser(f"~/.mirage/benchmark_{int(time.time())}.json")
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n  证据报告已存：{out_path}")
    except Exception as e:
        print(f"\n  ⚠ 报告写盘失败（{e}），分数仍见上方")


if __name__ == "__main__":
    main()
