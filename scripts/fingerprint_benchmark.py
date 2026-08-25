# -*- coding: utf-8 -*-
"""
fingerprint_benchmark.py — relative baseline score of browser fingerprint before/after hardening (not "evidence", see honest
boundaries below).

⚠️ Honest boundaries (red-team multi-review corrected, stop saying "provable"):
   1. This score only tests **7 basic signals** (webdriver/plugins/UA/languages/webgl-renderer/window/chrome),
      **on about:blank** — Canvas/WebGL pixel fingerprints, font enumeration, CDP `Runtime.Enable` leaks,
      JA3 transport layer and other deep dimensions are **not tested at all**. A low score only means "blocked low-end off-the-shelf
      detection", ≠ really able to fool platform risk control.
   2. `--self-test` uses **MOCK hardcoded fingerprints**, only validates the scoring logic, **not real evidence**.
   3. Hardening L1 relies on `stealth.min.js`, which is a **2023-03 discontinued version**, only blocks off-the-shelf detection.
   → For **real evidence**: use `--detect-url` to open a real detection page (default bot.sannysoft.com) and see with your own eyes,
   or go to CreepJS/BrowserScan.

Positioning: verify_stealth.py is a quick self-check; this script gives relative baseline score + entry to real detection pages. For
real runs, please run manually, AI does not run on behalf.

Usage:
    python fingerprint_benchmark.py --self-test                        # only test scoring logic (MOCK, no browser, not evidence)
    python fingerprint_benchmark.py --stealth ../libs/stealth.min.js   # relative baseline of 7 signals before/after hardening
    (opens window)
    python fingerprint_benchmark.py --detect-url                       # ⭐ real detection page (parse real pass rate + full-page
    screenshot)
    python fingerprint_benchmark.py --botd                             # ⭐ third-party BotD deterministic verdict (bot/botKind)

Evidence strength of three modes: --botd / --detect-url (third-party verdict, real) > local 7-signal BotScore (self-scored, weak)
> --self-test (MOCK, only validates scoring logic, not evidence).
Driver preference: patchright (patches CDP Runtime.Enable leak; injection scripts cannot patch this layer), fallback to playwright
if not installed.

Dependencies: playwright (only needed for real runs; --self-test doesn't need it). BotScore 0~100, higher = more like a bot (only
relative score of 7 basic signals).
"""
import argparse
import asyncio
import json
import os
import sys
import time

# Fingerprint-collecting JS (self-contained, no external detection page dependency; async to check permission consistency)
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

# Scoring model: each dimension hits a "bot feature" with a deduction weight. BotScore = sum of hit weights / total weight * 100.
# Weights are empirical: webdriver/headless-UA are hard features given high weight, soft rendering etc. given low weight.
# After local QA review + final ruling: removed permMismatch which easily false-positived on real browsers, added low-false-positive
# languages;
# webdriver 30→25 with multi-dimension dilution to avoid "single feature decides life or death". All dimensions are low-false-
# positive hard features.
SIGNALS = [
    ("webdriver",  lambda fp: bool(fp.get("webdriver")),                          25, "navigator.webdriver=true (top bot feature)"),
    ("headlessUA", lambda fp: "headless" in str(fp.get("ua", "")).lower(),        18, "UserAgent contains HeadlessChrome"),
    ("plugins",    lambda fp: int(fp.get("plugins", 0)) == 0,                     14, "navigator.plugins is empty"),
    ("languages",  lambda fp: not str(fp.get("languages", "")).strip(),           12, "navigator.languages is empty (common in headless)"),
    ("webglSW",    lambda fp: any(s in str(fp.get("webglRenderer", "")).lower()
                                  for s in ("swiftshader", "llvmpipe", "software")), 11, "WebGL software rendering (no real GPU)"),
    ("chrome",     lambda fp: not fp.get("hasChrome"),                            10, "window.chrome missing (suspected not real Chrome)"),
    ("outerZero",  lambda fp: int(fp.get("outerWidth", 1)) == 0
                              or int(fp.get("outerHeight", 1)) == 0,                   10, "window outer size is 0 (headless)"),
]
MAX_WEIGHT = sum(w for _, _, w, _ in SIGNALS)   # = 100


def _safe(fn, fp):
    try:
        return bool(fn(fp))
    except Exception:
        return False


def score_fingerprint(fp):
    """Return (botscore 0~100, list of hit features [(key,weight,why)])."""
    hits = [(k, w, why) for (k, fn, w, why) in SIGNALS if _safe(fn, fp)]
    raw = sum(w for _, w, _ in hits)
    botscore = round(raw / MAX_WEIGHT * 100)
    return botscore, hits


def risk_level(botscore):
    """Map BotScore to a risk level, to avoid over-interpreting absolute numbers."""
    return "Low" if botscore <= 20 else ("Medium" if botscore <= 50 else "High")


DISCLAIMER = ("This BotScore only tests 7 basic signals, runs on about:blank, is a relative baseline score, **not real evidence** — "
              "Canvas/WebGL pixels, font enumeration, CDP Runtime.Enable leak, JA3 and other deep layers are all untested; "
              "a low score only means it blocked low-end off-the-shelf detection. stealth.min.js is the 2023-03 discontinued version. "
              "For real evidence, use --detect-url to go to a real detection page (CreepJS/BrowserScan) and see with your own eyes.")


def render_report(fp_plain, fp_stealth):
    """Print comparison + return an archivable report dict."""
    bs_p, hits_p = score_fingerprint(fp_plain)
    bs_s, hits_s = score_fingerprint(fp_stealth)

    def block(title, fp, bs, hits):
        print(f"\n  [{title}]  BotScore = {bs}/100")
        print(f"    webdriver={fp.get('webdriver')}  plugins={fp.get('plugins')}  "
              f"chrome={fp.get('hasChrome')}  webglRenderer={fp.get('webglRenderer')}")
        for _, w, why in hits:
            print(f"    ⚠ (+{w}) {why}")
        if not hits:
            print("    ✓ No bot-like features hit")

    block("Control · unhardened", fp_plain, bs_p, hits_p)
    block("Experiment · hardened", fp_stealth, bs_s, hits_s)

    drop = bs_p - bs_s
    print("\n═══ Conclusion (7-signal relative baseline, not real evidence) ═══")
    print(f"  BotScore: {bs_p} → {bs_s}  (dropped {drop} points, lower = more human-like)")
    print(f"  Risk level: Control [{risk_level(bs_p)}] → Experiment [{risk_level(bs_s)}]")
    if drop >= 40:
        print("  ✓ Hardening significantly effective: most bot features erased")
    elif drop > 0:
        print("  ~ Hardening partially effective: residual features remain, check whether stealth.min.js is up to date")
    else:
        print("  ⚠ Hardening no effect: check whether stealth was injected correctly")
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
    async_playwright, _impl = _load_playwright()
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


# --- Self-test mock fingerprints: typical 'bare headless Chromium' and 'hardened real Chrome' ---
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
    """No-browser validation of scoring logic: bare fingerprint should score high, hardened fingerprint low, improvement significant."""
    bs_p, _ = score_fingerprint(MOCK_PLAIN)
    bs_s, _ = score_fingerprint(MOCK_STEALTH)
    assert bs_p >= 80, f"Bare fingerprint BotScore should be ≥80, got {bs_p}"
    assert bs_s <= 15, f"Hardened fingerprint BotScore should be ≤15, got {bs_s}"
    assert bs_p - bs_s >= 60, f"Improvement should be ≥60, got {bs_p - bs_s}"
    rep = render_report(MOCK_PLAIN, MOCK_STEALTH)
    assert rep["improvement"] == bs_p - bs_s
    assert {"botscore", "flags", "fp", "risk_level"} <= set(rep["plain"])
    assert rep["disclaimer"], "Report must carry a disclaimer"
    assert rep["plain"]["risk_level"] == "High" and rep["stealth"]["risk_level"] == "Low"
    assert isinstance(rep["stealth"]["flags"], list)
    # Monotonicity: removing a feature must lower the score
    less = dict(MOCK_PLAIN)
    less["webdriver"] = False
    assert score_fingerprint(less)[0] < bs_p, "Score should drop after removing webdriver"
    print("\n🎉 self-test passed: scoring logic correct (monotonic / bare high hardened low / report structure complete).")
    print("⚠ MOCK fingerprints — this validates the scoring logic only, it is NOT evidence.")
    print("  For real evidence run --detect-url (real detection page) or --botd.")


def _load_playwright():
    """Prefer patchright (a drop-in patched version of Playwright that patches CDP `Runtime.Enable` /
    `Console.enable` leaks — driver-layer leaks that injection scripts like stealth.min.js **cannot patch in principle**).
    Fall back to vanilla playwright if not installed. Returns (async_playwright, implementation name)."""
    try:
        from patchright.async_api import async_playwright
        return async_playwright, "patchright"
    except ImportError:
        pass
    try:
        from playwright.async_api import async_playwright
        return async_playwright, "playwright"
    except ImportError:
        sys.exit("✗ Browser driver not installed. Recommend pip install patchright (patches CDP leaks) "
                 "or pip install playwright; then <driver> install chromium")


# bot.sannysoft.com result table: one td.result per test item, passed=.passed failed=.failed,
# key items also have stable ids (#webdriver-result etc.). This is a detection page where you can get a **real pass rate**.
SANNYSOFT_JS = r"""() => {
  const cells = Array.from(document.querySelectorAll('td.result'));
  const passed = cells.filter(c => c.classList.contains('passed')).length;
  const failed = cells.filter(c => c.classList.contains('failed')).length;
  const pick = (id) => {
    const el = document.querySelector('#' + id);
    return el ? (el.textContent || '').trim().slice(0, 60) : null;
  };
  return {
    passed: passed, failed: failed, total: passed + failed,
    webdriver: pick('webdriver-result'),
    advanced_webdriver: pick('advanced-webdriver-result'),
    chrome: pick('chrome-result'),
    permissions: pick('permissions-result'),
  };
}"""

# FingerprintJS official open-source BotD (MIT): pure client-side automation framework detection, returns {bot, botKind}.
# Deterministic offline verdict, much more reliable than self-scored 7 signals. botKind examples: headless_chrome / selenium / electron.
BOTD_JS = r"""async () => {
  try {
    const Botd = await import('https://openfpcdn.io/botd/v2');
    const botd = await Botd.load();
    const r = await botd.detect();
    return { ok: true, bot: !!r.bot, botKind: r.botKind || '' };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}"""


async def _run_botd(headless, stealth_path):
    """Inject BotD locally for deterministic bot detection (needs network for CDN module, but detection runs locally)."""
    apw, impl = _load_playwright()
    _note = " (CDP leak patched)" if impl == "patchright" else " (install patchright to patch the CDP leak)"
    print(f"  Driver: {impl}{_note}")
    async with apw() as p:
        browser = await p.chromium.launch(headless=headless)
        ctx = await browser.new_context()
        if stealth_path:
            await ctx.add_init_script(path=stealth_path)
        page = await ctx.new_page()
        await page.goto("https://example.com", wait_until="domcontentloaded")
        res = await page.evaluate(BOTD_JS)
        await browser.close()
    if not res.get("ok"):
        print(f"  ⚠ BotD failed to load ({res.get('error')}) — need access to openfpcdn.io")
        return res
    if res["bot"]:
        print(f"  🤖 BotD verdict: **is a bot** (botKind={res['botKind']}) — hardening didn't fool it")
    else:
        print("  ✓ BotD verdict: not a bot")
        print("    (third-party open-source detector — stronger evidence than the local 7-signal score)")
    return res


async def _run_detect(url, stealth_path, headless):
    """Open real detection page (inject stealth): parse the page's **real pass rate** + collect 7 signals + full-page screenshot."""
    async_playwright, impl = _load_playwright()
    _note = " (CDP leak patched)" if impl == "patchright" else " (install patchright to patch the CDP leak)"
    print(f"  Driver: {impl}{_note}")
    shot = os.path.expanduser(f"~/.mirage/detect_{int(time.time())}.png")
    os.makedirs(os.path.dirname(shot), exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        ctx = await browser.new_context()
        if stealth_path:
            await ctx.add_init_script(path=stealth_path)
        page = await ctx.new_page()
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(2500)        # Wait for async detection items to render (fp2 table is filled asynchronously)
        await page.screenshot(path=shot, full_page=True)
        fp = await page.evaluate(EXTENDED_CHECK_JS)
        sanny = None
        if "sannysoft" in url:
            try:
                sanny = await page.evaluate(SANNYSOFT_JS)
            except Exception:
                sanny = None
        if not headless:
            await page.wait_for_timeout(6000)   # Leave time for you to see with your own eyes
        await browser.close()

    if sanny and sanny.get("total"):
        rate = sanny["passed"] / sanny["total"] * 100
        print(f"\n  ⭐ Real pass rate: {sanny['passed']}/{sanny['total']} = {rate:.0f}%")
        print("     (judged by the detection page itself — not a score this tool gives itself)")
        for k, label in (("webdriver", "navigator.webdriver"), ("advanced_webdriver", "advanced webdriver"),
                         ("chrome", "window.chrome"), ("permissions", "permissions")):
            if sanny.get(k):
                print(f"    {label}: {sanny[k]}")
        if rate < 100:
            print(f"    ⚠ {sanny['failed']} item(s) failed — those are the red/yellow cells in the")
            print("       screenshot. Go through them one by one to see what leaked.")
    bs, _ = score_fingerprint(fp)
    print(f"\n  (Reference) local 7-signal BotScore={bs}, webglRenderer={fp.get('webglRenderer')}")
    print(f"  ⭐ Full-page screenshot (deep verdicts such as Canvas/WebGL/fonts are all in it): {shot}")
    print(f"  ⚠ {DISCLAIMER}")
    return {"fp": fp, "sannysoft": sanny, "screenshot": shot}


def main():
    ap = argparse.ArgumentParser(
        description="Relative fingerprint baseline + real detection-page entry "
                    "(run the real ones manually; the local score is not evidence)")
    here = os.path.dirname(os.path.abspath(__file__))
    default_stealth = os.path.normpath(os.path.join(here, "..", "libs", "stealth.min.js"))
    ap.add_argument("--stealth", default=default_stealth, help="path to stealth.min.js")
    ap.add_argument("--headless", action="store_true", help="run headless (default opens window so you can see with your own eyes)")
    ap.add_argument("--self-test", action="store_true", help="only test scoring logic, no browser launched")
    ap.add_argument("--json", default="", help="write relative baseline report to specified JSON path")
    ap.add_argument("--detect-url", nargs="?", const="https://bot.sannysoft.com/", default="",
                    help="go to a real detection page (default bot.sannysoft.com): "
                         "parse its real pass rate + full-page screenshot")
    ap.add_argument("--botd", action="store_true",
                    help="⭐ use FingerprintJS open-source BotD for third-party deterministic bot detection (returns bot/botKind)")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    if args.botd:
        sp = args.stealth if os.path.isfile(args.stealth) else None
        print(f"Using BotD for third-party bot detection (stealth={'injected' if sp else 'none'})……")
        asyncio.run(_run_botd(args.headless, sp))
        return

    if args.detect_url:
        sp = args.stealth if os.path.isfile(args.stealth) else None
        print(f"Opening detection page {args.detect_url} "
              f"(stealth={'injected' if sp else 'none'}) — check the window yourself")
        asyncio.run(_run_detect(args.detect_url, sp, args.headless))
        return

    stealth_path = args.stealth if os.path.isfile(args.stealth) else None
    if not stealth_path:
        print(f"⚠ stealth.min.js not found: {args.stealth} (experiment group will degrade to no injection, comparison meaningless)")
    else:
        print(f"Using stealth: {stealth_path} ({os.path.getsize(stealth_path)//1024}KB)")

    print("Starting browser scoring…… (this is a manually initiated verification)")
    fp_plain, fp_stealth = asyncio.run(_run(stealth_path, args.headless))
    report = render_report(fp_plain, fp_stealth)

    out_path = args.json or os.path.expanduser(f"~/.mirage/benchmark_{int(time.time())}.json")
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n  Relative baseline report saved: {out_path} (remember: 7-signal relative score, not real evidence)")
    except Exception as e:
        print(f"\n  ⚠ Report write failed ({e}), score is still shown above")


if __name__ == "__main__":
    main()
