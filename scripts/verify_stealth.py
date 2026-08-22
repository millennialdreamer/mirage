# -*- coding: utf-8 -*-
"""
verify_stealth.py — fingerprint self-check: after injecting stealth.min.js, read the key
automation fingerprints and judge "human-like / bot-like".

⚠️ This script launches a real browser window; please **run it manually yourself**.
   It is for you to verify the hardening effect, and should not be run by an automation proxy.

Usage:
    python verify_stealth.py --stealth ../libs/stealth.min.js
    python verify_stealth.py --stealth /path/to/stealth.min.js --headless

Dependency: playwright (pip install playwright && playwright install chromium)

Principle: open two contexts with the same browser — one **without injecting** stealth (control group),
one **with injecting** stealth (experimental group), and read fingerprints from each for comparison. If, in the experimental group,
navigator.webdriver changes from true to undefined and plugins changes from empty to non-empty, it means
stealth took effect.
"""

import argparse
import asyncio
import os
import sys

# JS to read key automation fingerprints (self-contained, no external detection page)
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
    """On the given context (optionally inject stealth), open a page and read fingerprints."""
    if stealth_path:
        await context.add_init_script(path=stealth_path)
    page = await context.new_page()
    await page.goto("about:blank")
    fp = await page.evaluate(CHECK_JS)
    await page.close()
    return fp


def verdict(fp):
    """Return a list of robot suspicion points based on fingerprints (empty list = clean)."""
    flags = []
    if fp.get("webdriver"):
        flags.append("navigator.webdriver = true  ← No.1 robot signature")
    if fp.get("plugins", 0) == 0:
        flags.append("navigator.plugins is empty  ← common in headless/automation")
    if not fp.get("hasChrome"):
        flags.append("window.chrome missing  ← suspicion of not being real Chrome")
    return flags


def show(title, fp):
    print(f"\n  [{title}]")
    print(f"    navigator.webdriver : {fp.get('webdriver')}")
    print(f"    navigator.plugins   : {fp.get('plugins')} plugin(s)")
    print(f"    navigator.languages : {fp.get('languages')}")
    print(f"    window.chrome       : {fp.get('hasChrome')}")
    print(f"    permissions API     : {fp.get('permissionsApi')}")
    print(f"    WebGL vendor        : {fp.get('webglVendor')}")
    flags = verdict(fp)
    if flags:
        for f in flags:
            print(f"    ⚠ {f}")
    else:
        print("    ✓ No obvious robot signatures found")
    return flags


async def run(stealth_path, headless):
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        sys.exit("✗ playwright is not installed. Run first: pip install playwright && playwright install chromium")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        # Control group: no injection
        ctx_a = await browser.new_context()
        fp_plain = await probe(ctx_a, None)
        await ctx_a.close()
        # Experimental group: inject stealth
        ctx_b = await browser.new_context()
        fp_stealth = await probe(ctx_b, stealth_path)
        await ctx_b.close()
        await browser.close()
    return fp_plain, fp_stealth


def main():
    ap = argparse.ArgumentParser(description="Fingerprint self-check after injecting stealth (please run manually)")
    here = os.path.dirname(os.path.abspath(__file__))
    default_stealth = os.path.normpath(os.path.join(here, "..", "libs", "stealth.min.js"))
    ap.add_argument("--stealth", default=default_stealth,
                    help=f"Path to stealth.min.js (default {default_stealth})")
    ap.add_argument("--headless", action="store_true",
                    help="Run in headless mode (default has a window so you can see it yourself)")
    args = ap.parse_args()

    if not os.path.isfile(args.stealth):
        print(f"⚠ stealth.min.js not found: {args.stealth}")
        print("  Test group falls back to 'no injection', so the comparison is meaningless.")
        print("  Pass --stealth with the correct path.")
        stealth_path = None
    else:
        stealth_path = args.stealth
        print(f"Using stealth: {stealth_path} ({os.path.getsize(stealth_path)//1024}KB)")

    print("Starting browser self-check... (this is a verification you initiated manually)")
    fp_plain, fp_stealth = asyncio.run(run(stealth_path, args.headless))

    flags_plain = show("Control group · no stealth injected", fp_plain)
    flags_stealth = show("Experimental group · stealth injected", fp_stealth)

    print("\n═══ Conclusion ═══")
    if stealth_path and len(flags_stealth) < len(flags_plain):
        print(f"  ✓ stealth active: robot signatures reduced from {len(flags_plain)} to {len(flags_stealth)}")
    elif stealth_path and not flags_stealth:
        print("  ✓ Experimental group has no robot signatures; stealth is working normally")
    elif not stealth_path:
        print("  ? No stealth.min.js provided; cannot compare")
    else:
        print("  ⚠ Signatures did not decrease after injection; check whether stealth.min.js is loaded correctly")


if __name__ == "__main__":
    main()
