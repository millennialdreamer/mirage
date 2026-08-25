#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_hardening.py — installs "five-layer anti-detection hardening" into MediaCrawler in one shot.

Design iron rules (also why it is "mature"):
  1. Back up any file to <file>.xhs-stealth.bak before modifying it (first time only; never overwrite an existing backup).
  2. All injected code is wrapped with the `# [xhs-stealth]` marker — naturally idempotent: skip already patched files.
  3. When an anchor is not found (different MediaCrawler version/structure), degrade gracefully + print manual guidance,
     never blindly modify and corrupt the target file syntax.

Usage:
  python apply_hardening.py /path/to/MediaCrawler            # patch
  python apply_hardening.py /path/to/MediaCrawler --dry-run  # show what would change, do not write to disk
  python apply_hardening.py /path/to/MediaCrawler --check    # health check: each hardening layer status
  python apply_hardening.py /path/to/MediaCrawler --revert   # fully restore from .bak

Five layers of protection:
  L1 stealth.min.js auto-injection   -> hide navigator.webdriver and other automation fingerprints
  L2 random jitter sleep             -> remove the machine trait of fixed rhythm
  L3 batch limit + safe defaults      -> reduce single exposure, force real browser/single concurrency
  L4 start-up warm-up                 -> linger a few seconds before entering search, like a real user viewing the page
  L5 mouse + scroll simulation (best-effort layer)  -> fill the robot signal of "frozen page during sleep"
"""

import argparse
import os
import re
import shutil
import sys
import urllib.request

MARK = "[xhs-stealth]"          # idempotent marker
BAK_SUFFIX = ".xhs-stealth.bak"  # backup suffix
STEALTH_URL = (
    "https://raw.githubusercontent.com/berstend/puppeteer-extra/master/"
    "packages/puppeteer-extra-plugin-stealth/evasions/_utils/stealth.min.js"
)

# terminal coloring (auto-disabled without a tty)
_C = sys.stdout.isatty()
def _g(s): return f"\033[32m{s}\033[0m" if _C else s   # green
def _y(s): return f"\033[33m{s}\033[0m" if _C else s   # yellow
def _r(s): return f"\033[31m{s}\033[0m" if _C else s   # red
def _b(s): return f"\033[1m{s}\033[0m" if _C else s    # bold


# ════════════════════════════════════════════════════════════════════
# basic IO
# ════════════════════════════════════════════════════════════════════
def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, text):
    """Atomic write: write a temporary file in the same directory, fsync, then os.replace atomic replace.
    Avoid leaving a half-written corrupted target file if interrupted mid-write (crash/disk full/power loss).
    Assumes path is a regular file (true for MediaCrawler source); does not handle symlinks."""
    import tempfile
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(path):
            try:
                shutil.copystat(path, tmp)   # try to preserve original permissions/timestamps
            except OSError:
                pass                          # ignore unsupported filesystem quirks and do not block writing
        os.replace(tmp, path)            # atomic replace on the same filesystem
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def backup(path, dry):
    """Back up before first modification; never overwrite an existing backup (protect the most original version)."""
    bak = path + BAK_SUFFIX
    if os.path.exists(bak):
        return
    if dry:
        print(f"    {_y('[dry]')} will back up -> {os.path.basename(bak)}")
        return
    shutil.copy2(path, bak)
    print(f"    {_g('✓')} backed up -> {os.path.basename(bak)}")


def write_py_safe(path, text):
    """The only safe write path for patching .py sources: atomic write + post-write
    ast.parse self-check. If the syntax is broken, immediately roll back from .bak and
    exit — never leave the user with a corrupted source file.
    Precondition: backup(path) was already called (all three patch_* honor backup-then-rewrite)."""
    import ast
    write(path, text)                       # atomic write to disk
    try:
        ast.parse(read(path))
    except SyntaxError as e:
        bak = path + BAK_SUFFIX
        if os.path.isfile(bak):
            write(path, read(bak))   # roll back atomically too, so an interrupted rollback can't corrupt again
            sys.exit(_r(f"✗ {os.path.basename(path)} has a syntax error after patching; rolled back from backup: {e}"))
        sys.exit(_r(f"✗ {os.path.basename(path)} has a syntax error after patching and there is no .bak to roll back to: {e}"))


# ════════════════════════════════════════════════════════════════════
# Locating and validating
# ════════════════════════════════════════════════════════════════════
# Platforms supported by MediaCrawler: alias -> (directory name, display name, anti-crawl strength)
PLATFORMS = {
    "xhs":   ("xhs",      "Xiaohongshu", "medium"),
    "dy":    ("douyin",   "Douyin",      "very high"),
    "ks":    ("kuaishou", "Kuaishou",    "high"),
    "bili":  ("bilibili", "Bilibili",    "medium-low"),
    "wb":    ("weibo",    "Weibo",       "medium"),
    "tieba": ("tieba",    "Tieba",       "low"),
    "zhihu": ("zhihu",    "Zhihu",       "medium"),
}


def locate(root, platform="xhs"):
    """Confirm root is a MediaCrawler install and return the key file paths for the given platform."""
    pdir = PLATFORMS.get(platform, (platform, platform, "?"))[0]
    files = {
        "base_config": os.path.join(root, "config", "base_config.py"),
        "core": os.path.join(root, "media_platform", pdir, "core.py"),
        "cdp": os.path.join(root, "tools", "cdp_browser.py"),
        "stealth": os.path.join(root, "libs", "stealth.min.js"),
        "platform": platform,
    }
    if not os.path.isfile(files["base_config"]):
        sys.exit(_r(f"✗ {root} is not a MediaCrawler install (config/base_config.py missing)"))
    if not os.path.isfile(files["core"]):
        sys.exit(_r(f"✗ core.py not found for platform {platform}: media_platform/{pdir}/core.py"))
    return files


# ════════════════════════════════════════════════════════════════════
# L3 — base_config.py safe parameters
# ════════════════════════════════════════════════════════════════════
# Target parameters: key -> (target value, why)
SAFE_PARAMS = {
    "CRAWLER_MAX_SLEEP_SEC":   ("6",    "slow the base interval to 6s (4.2~9.6s after jitter)"),
    "CRAWLER_MAX_NOTES_COUNT": ("8",    "cap a single crawl at 8 items"),
    "MAX_CONCURRENCY_NUM":     ("1",    "force single concurrency — closest to a real person"),
    "ENABLE_CDP_MODE":         ("True", "use real Chrome (CDP), the strongest anti-detection"),
    "CDP_CONNECT_EXISTING":    ("True", "reuse the browser you are already logged into"),
    "HEADLESS":                ("False","disable headless mode (headless is the easiest to spot)"),
    "SAVE_LOGIN_STATE":        ("True", "keep the login session — closest to a real person"),
}


def patch_base_config(path, dry):
    """Regex-replace a few key parameters with safe values. Pure value replacement -> naturally idempotent."""
    print(_b("\n[L3] base_config.py safe parameters"))
    text = read(path)
    changed = False
    for key, (target, why) in SAFE_PARAMS.items():
        # Take the first non-whitespace segment as the value (number/True/False/no-space string); keep trailing .* as-is (including end-of-line comments).
        # No longer use [^\n#]+? —— avoid truncating values containing '#' (e.g. in strings) as comments.
        pat = re.compile(rf"^({re.escape(key)}\s*=\s*)(\S+)(.*)$", re.MULTILINE)
        m = pat.search(text)
        if not m:
            print(f"    {_y('⚠')} not found {key}, skipping")
            continue
        cur = m.group(2).strip()
        if cur == target:
            print(f"    {_g('·')} {key} is already {target}")
            continue
        if not changed and not dry:
            backup(path, dry)
        changed = True
        text = pat.sub(rf"\g<1>{target}\g<3>", text, count=1)
        print(f"    {_g('✓') if not dry else _y('[dry]')} {key}: {cur} -> {target}  ({why})")
    if changed and not dry:
        write_py_safe(path, text)
    if not changed:
        print(f"    {_g('all already secure')}")


# ════════════════════════════════════════════════════════════════════
# L1 — cdp_browser.py auto-inject stealth
# ════════════════════════════════════════════════════════════════════
STEALTH_METHOD = '''
    async def _auto_inject_stealth(self):
        # [xhs-stealth] L1: resolve stealth.min.js by absolute path and inject it
        import os as _os
        _root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        _path = _os.path.join(_root, "libs", "stealth.min.js")
        if hasattr(self, "add_stealth_script"):
            await self.add_stealth_script(_path)
        elif getattr(self, "browser_context", None):
            await self.browser_context.add_init_script(path=_path)
'''


def patch_cdp_browser(path, dry):
    """Inject _auto_inject_stealth into CDP manager and call before each return browser_context."""
    print(_b("\n[L1] cdp_browser.py auto-inject stealth.min.js"))
    if not os.path.isfile(path):
        print(f"    {_y('⚠')} no tools/cdp_browser.py (CDP mode may be disabled), skipping L1")
        return
    text = read(path)

    if MARK in text:
        print(f"    {_g('·')} already contains {MARK} injection, skipping (idempotent)")
        return

    # Anchor: where `return browser_context` is returned (two paths: CDP launch / existing connection)
    ret_pat = re.compile(r"^(\s*)return browser_context\s*$", re.MULTILINE)
    rets = list(ret_pat.finditer(text))
    if not rets:
        print(f"    {_y('⚠')} `return browser_context` anchor not found —— this version has a different structure")
        print("      please manually call stealth injection once after CDP startup (see docs/anti-detection.md)")
        return

    backup(path, dry)
    # Insert call before each return
    def _inject_call(m):
        indent = m.group(1)
        return f"{indent}await self._auto_inject_stealth()  # {MARK}\n{indent}return browser_context"
    new = ret_pat.sub(_inject_call, text)

    # Append method inside the CDP manager class: locate the class first, then insert at the top of the class body (line after the class line)
    # This avoids injecting the method into wrong scope due to "first async def at module level or another class",
    # and also avoids inserting between a method's decorator and def, which would break syntax
    cls = (re.search(r"^class\s+\w*CDP\w*[^\n]*:", new, re.MULTILINE)
           or re.search(r"^class\s+\w+[^\n]*:", new, re.MULTILINE))
    if cls:
        line_end = new.find("\n", cls.end())
        idx = (line_end + 1) if line_end != -1 else len(new)
        new = new[:idx] + STEALTH_METHOD.lstrip("\n") + "\n" + new[idx:]
    else:
        print(f"    {_y('⚠')} class definition anchor not found, only inserted call —— please manually add _auto_inject_stealth")

    if dry:
        print(f"    {_y('[dry]')} will inject _auto_inject_stealth + {len(rets)} call sites")
    else:
        write_py_safe(path, new)
        print(f"    {_g('✓')} injected method + {len(rets)} call sites")


# ════════════════════════════════════════════════════════════════════
# L2 / L4 / L5 — core.py
# ════════════════════════════════════════════════════════════════════
WARMUP_BLOCK = '''        # [xhs-stealth] L4: human warm-up — pause on the page before the first search
        import random as _rnd, asyncio as _aio
        _warm = max(2.5, min(16.0, 5.5 * _rnd.lognormvariate(0, 0.40)))  # right-skewed, non-uniform
        await _aio.sleep(_warm)
'''

HUMAN_METHOD = '''
    async def _xhs_stealth_human_activity(self):
        # [xhs-stealth] L5: human-like scroll + bezier mouse move
        # Prefer deployed tools/human_behavior.py (single source of truth, mouse moves along Bezier curves instead of teleporting)
        try:
            page = getattr(self, "context_page", None)
            if page is None:
                return
            try:
                from tools.human_behavior import simulate_page_activity
                await simulate_page_activity(page)
                return
            except Exception:
                pass
            # Fallback: minimal inline version when module is missing (still moves in steps, not teleporting)
            import random as _rnd, asyncio as _aio
            await page.mouse.wheel(0, _rnd.randint(300, 700))
            await _aio.sleep(_rnd.uniform(0.4, 1.0))
            _x, _y = _rnd.randint(200, 900), _rnd.randint(200, 500)
            for _i in range(1, 11):
                _u = _i / 10
                _t = _u * _u * (3 - 2 * _u)      # ease in/out, avoid linear uniform speed (uniform = bot)
                await page.mouse.move(_x * _t + _rnd.uniform(-2, 2),
                                      _y * _t + _rnd.uniform(-2, 2))
                await _aio.sleep(0.019 * _rnd.lognormvariate(0, 0.35))
        except Exception:
            pass
'''


def _ensure_import_random(text):
    """Ensure import random at top of core.py; if missing, add a line after the existing import section."""
    if re.search(r"^import random\b", text, re.MULTILINE):
        return text, False
    m = re.search(r"^import asyncio\b.*$", text, re.MULTILINE)
    if m:
        idx = m.end()
        return text[:idx] + f"\nimport random  # {MARK}" + text[idx:], True
    # Fallback 1: insert after the last top-level import/from line (never insert before shebang or # coding declaration)
    imports = list(re.finditer(r"^(?:import|from)\s+\S+.*$", text, re.MULTILINE))
    if imports:
        idx = imports[-1].end()
        return text[:idx] + f"\nimport random  # {MARK}" + text[idx:], True
    # Fallback 2: no imports —— insert before the first non-empty, non-comment line
    lines = text.split("\n")
    insert_at = 0
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s and not s.startswith("#"):
            insert_at = i
            break
    lines.insert(insert_at, f"import random  # {MARK}")
    return "\n".join(lines), True


def patch_core(path, dry, platform="xhs"):
    """core.py: L2 jitter (stable) + L4 warm-up (best effort) + L5 mouse simulation (best effort). Anchor is platform-agnostic."""
    pdir = PLATFORMS.get(platform, (platform,))[0]
    print(_b(f"\n[L2/L4/L5] media_platform/{pdir}/core.py"))
    text = read(path)
    orig = text
    did_any = False

    # —— ensure import random ——
    text, added = _ensure_import_random(text)
    if added:
        did_any = True
        print(f"    {_g('✓') if not dry else _y('[dry]')} added import random")

    # -- L2: change fixed sleep to jitter (overrides CRAWLER_MAX_SLEEP_SEC and crawl_interval) --
    sleep_pat = re.compile(
        r"^(\s*)await asyncio\.sleep\(\s*(config\.CRAWLER_MAX_SLEEP_SEC|crawl_interval)\s*\)\s*(?:#.*)?$",
        re.MULTILINE,
    )
    def _jitter(m):
        indent, expr = m.group(1), m.group(2)
        # Use log-normal (right-skewed) rather than uniform: human intervals are "many short + a few long-tail",
        # uniform's histogram is a flat-top rectangle; the KS test can identify it directly. lognormvariate(0,σ) median=1,
        # so expr * lognormvariate(0,0.45) has the original interval as its median, but the shape is a true right-skewed curve.
        return (f"{indent}await asyncio.sleep({expr} * "
                f"random.lognormvariate(0, 0.45))  # {MARK} L2 jitter")
    n_sleep = len(sleep_pat.findall(text))
    if n_sleep:
        text = sleep_pat.sub(_jitter, text)
        did_any = True
        print(f"    {_g('✓') if not dry else _y('[dry]')} L2: {n_sleep} fixed sleep -> random jitter")
    elif "L2 jitter" in text:
        print(f"    {_g('·')} L2 jitter already present (idempotent skip)")
    else:
        print(f"    {_y('⚠')} fixed sleep anchor not found -- this version may have been rewritten, skipping L2")

    # -- L4: startup warm-up -- anchor: start of async def search method body (platform-independent, compatible with or without -> None) --
    if "L4: human warm-up" in text:
        print(f"    {_g('·')} L4 warm-up already present (idempotent skip)")
    else:
        search_def = re.search(
            r"^    async def search\(self\)(?:\s*->\s*[^\n:]+)?\s*:[^\n]*\n",
            text, re.MULTILINE,
        )
        if search_def:
            idx = search_def.end()
            # Skip an immediately following single-line docstring (if any), so the warm-up is inserted after it, preserving the docstring
            doc = re.match(r'\s*(?:"""[^\n]*"""|\'\'\'[^\n]*\'\'\')\n', text[idx:])
            if doc:
                idx += doc.end()
            block = WARMUP_BLOCK if WARMUP_BLOCK.endswith("\n") else WARMUP_BLOCK + "\n"
            text = text[:idx] + block + text[idx:]
            did_any = True
            print(f"    {_g('✓') if not dry else _y('[dry]')} L4: inject startup warm-up")
        else:
            print(f"    {_y('⚠')} async def search anchor not found, skipping L4 (can be added manually)")

    # -- L5: mouse simulation method + call before pagination jitter sleep -- best-effort layer --
    if "_xhs_stealth_human_activity" in text:
        print(f"    {_g('·')} L5 mouse simulation already present (idempotent skip)")
    else:
        injected_method = False
        # Method definition: insert before the next sibling method **after** the search method (platform-independent;
        # original get_creators_and_notes is Xiaohongshu-specific, not generic)
        sdef = re.search(r"^    async def search\(self\)", text, re.MULTILINE)
        if sdef:
            nd = re.search(r"^    (?:async )?def ", text[sdef.end():], re.MULTILINE)
            if nd:
                idx = sdef.end() + nd.start()
                text = text[:idx] + HUMAN_METHOD.lstrip("\n") + "\n" + text[idx:]
                injected_method = True
        # Call site: only before the first L2 jitter inside the search() method body.
        # Avoid "the first L2 jitter is in another function" causing the call to be injected into the wrong function.
        call_indent, call_global_start = None, None
        search_m = re.search(r"^    async def search\(", text, re.MULTILINE)
        if search_m:
            rest = text[search_m.end():]
            next_def = re.search(r"^    (?:async )?def ", rest, re.MULTILINE)
            seg_end = search_m.end() + (next_def.start() if next_def else len(rest))
            seg = text[search_m.end():seg_end]
            # Relaxed: only match the sleep line + L2 jitter marker, do not lock to a specific distribution function name
            # (matches both the new lognormvariate form and the already-deployed old uniform form)
            cm = re.search(r"^(\s*)await asyncio\.sleep\([^\n]*L2 jitter",
                           seg, re.MULTILINE)
            if cm:
                call_indent = cm.group(1)
                call_global_start = search_m.end() + cm.start()
        if injected_method and call_global_start is not None:
            call_line = f"{call_indent}await self._xhs_stealth_human_activity()  # {MARK} L5\n"
            text = text[:call_global_start] + call_line + text[call_global_start:]
            did_any = True
            print(f"    {_g('✓') if not dry else _y('[dry]')} L5: inject mouse simulation method + call")
        elif injected_method:
            print(f"    {_g('✓') if not dry else _y('[dry]')} L5: method injected, but call anchor not found (method can be called manually)")
        else:
            print(f"    {_y('⚠')} L5 injection anchor not found, skipping (best-effort layer, does not affect L1-L4)")

    if did_any and text != orig:
        if not dry:
            backup(path, dry)
            write_py_safe(path, text)   # atomic write + AST self-check + failure rollback (unified entry)
            print(f"    {_g('✓ syntax self-check passed')}")
    elif not did_any:
        print(f"    {_g('core.py needs no changes or is already fully hardened')}")


# ════════════════════════════════════════════════════════════════════
# stealth.min.js existence
# ════════════════════════════════════════════════════════════════════
def ensure_stealth_js(path, dry):
    print(_b("\n[resource] libs/stealth.min.js"))
    if os.path.isfile(path) and os.path.getsize(path) > 1000:
        print(f"    {_g('·')} already exists ({os.path.getsize(path)//1024}KB)")
        return
    if dry:
        print(f"    {_y('[dry]')} missing, will download from upstream")
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        print("    downloading …")
        with urllib.request.urlopen(STEALTH_URL, timeout=30) as resp:
            data = resp.read()
        if b"webdriver" not in data:
            print(f"    {_y('⚠')} downloaded content looks wrong, nothing written. Place stealth.min.js manually.")
            return
        with open(path, "wb") as f:
            f.write(data)
        print(f"    {_g('✓')} downloaded ({len(data)//1024}KB)")
    except Exception as e:
        print(f"    {_y('⚠')} download failed ({e}). MediaCrawler usually ships its own copy — safe to ignore.")


# ════════════════════════════════════════════════════════════════════
# Deploy helper modules (safe_profile.py / human_behavior.py)
# ════════════════════════════════════════════════════════════════════
def deploy_modules(root, dry):
    print(_b("\n[deploy] helper scripts -> target config/ and tools/"))
    here = os.path.dirname(os.path.abspath(__file__))
    plan = [
        ("safe_profile.py", os.path.join(root, "config", "safe_profile.py")),
        ("human_behavior.py", os.path.join(root, "tools", "human_behavior.py")),
    ]
    for name, dst in plan:
        src = os.path.join(here, name)
        if not os.path.isfile(src):
            continue
        if os.path.isfile(dst):
            print(f"    {_g('·')} {name} already deployed")
            continue
        if dry:
            print(f"    {_y('[dry]')} would deploy {name} -> {os.path.relpath(dst, root)}")
            continue
        shutil.copy2(src, dst)
        print(f"    {_g('✓')} deployed {name}")


# ════════════════════════════════════════════════════════════════════
# check / revert
# ════════════════════════════════════════════════════════════════════
def do_check(files):
    print(_b("\n═══ Hardening health check ═══"))
    def status(path, needle, label):
        if not os.path.isfile(path):
            print(f"  {_y('?')} {label}: file does not exist")
            return
        print(f"  {_g('✓') if needle in read(path) else _r('✗')} {label}")
    bc = read(files["base_config"])
    ok_params = all(re.search(rf"^{k}\s*=\s*{re.escape(v)}\b", bc, re.MULTILINE)
                    for k, (v, _) in SAFE_PARAMS.items())
    print(f"  {_g('✓') if ok_params else _r('✗')} L3 base_config safe parameters")
    status(files["core"], "L2 jitter", "L2 jittered sleep")
    status(files["core"], "L4: human warm-up", "L4 startup warm-up")
    status(files["core"], "_xhs_stealth_human_activity", "L5 mouse simulation")
    if os.path.isfile(files["cdp"]):
        status(files["cdp"], MARK, "L1 stealth auto-injection")
    sj = files["stealth"]
    print(f"  {_g('✓') if os.path.isfile(sj) else _r('✗')} stealth.min.js resource")


def do_revert(files, root):
    print(_b("\n═══ Revert from .bak ═══"))
    restored = 0
    for p in list(files.values()) + [
        os.path.join(root, "config", "safe_profile.py"),
        os.path.join(root, "tools", "human_behavior.py"),
    ]:
        bak = p + BAK_SUFFIX
        if os.path.isfile(bak):
            shutil.copy2(bak, p)
            print(f"  {_g('✓')} restored {os.path.basename(p)}")
            restored += 1
    if restored == 0:
        print(f"  {_y('No .xhs-stealth.bak backup found')}")
    else:
        print(f"  {_g(f'Restored {restored} file(s)')} (.bak kept, so you can revert again)")


# ════════════════════════════════════════════════════════════════════
# canary — offline decay check
# ════════════════════════════════════════════════════════════════════
def do_canary(files):
    """Offline decay check: is the hardening still there / did an anchor drift / are the resources healthy?
    Sends no network traffic and opens no browser (for the fingerprint layer — webdriver/BotScore —
    run verify/benchmark manually).
    Returns the number of decayed items (0 = healthy)."""
    print(_b("\n═══ Canary decay check (offline, no requests sent) ═══"))
    issues = []
    core_txt = read(files["core"]) if os.path.isfile(files["core"]) else ""
    bc_txt = read(files["base_config"]) if os.path.isfile(files["base_config"]) else ""

    # 1) are the hardening markers still there (an upstream pull or a manual edit can wipe them)
    if "L2 jitter" in core_txt and "L4: human warm-up" in core_txt:
        print(f"  {_g('✓')} core.py five-layer hardening markers in place")
    else:
        issues.append("core.py hardening markers missing (likely overwritten by an upstream pull) "
                      "→ run `mirage apply` to re-apply")

    # 2) are the base_config parameters still at their safe values
    bad = [k for k, (v, _) in SAFE_PARAMS.items()
           if not re.search(rf"^{k}\s*=\s*{re.escape(v)}\b", bc_txt, re.MULTILINE)]
    if not bad:
        print(f"  {_g('✓')} base_config safe parameters intact")
    else:
        issues.append(f"base_config safe parameters reverted: {', '.join(bad)} → run `mirage apply` to re-apply")

    # 3) stealth.min.js healthy (exists + big enough + contains the webdriver keyword)
    sj = files["stealth"]
    healthy = os.path.isfile(sj) and os.path.getsize(sj) > 1000
    if healthy:
        try:
            with open(sj, "rb") as f:
                healthy = b"webdriver" in f.read()
        except OSError:
            healthy = False
    if healthy:
        print(f"  {_g('✓')} stealth.min.js healthy ({os.path.getsize(sj)//1024}KB)")
    else:
        issues.append("stealth.min.js missing/corrupt → run weekly_maintenance to refresh it")

    # 4) upstream structure drift: is the 'async def search' anchor still there (an upstream refactor breaks it)
    if core_txt:
        if re.search(r"^    async def search\(self\)", core_txt, re.MULTILINE):
            print(f"  {_g('✓')} upstream search anchor structure unchanged")
        else:
            issues.append("core.py no longer has the 'async def search(self)' anchor (upstream likely refactored) "
                          "→ hardening anchors may have drifted; check by hand")

    print()
    if issues:
        print(_r(f"  ⚠ Found {len(issues)} sign(s) of decay:"))
        for it in issues:
            print(f"    - {it}")
    else:
        print(_g("  ✓ Offline-layer hardening healthy, no signs of decay"))
    print(_y("  The fingerprint layer (webdriver/BotScore) cannot be tested offline — run these yourself periodically:"))
    print(_y("    python scripts/verify_stealth.py   |   python scripts/fingerprint_benchmark.py"))
    return len(issues)


# ════════════════════════════════════════════════════════════════════
def main(argv=None):
    ap = argparse.ArgumentParser(description="Apply five-layer anti-detection hardening to MediaCrawler (multi-platform)")
    ap.add_argument("path", help="MediaCrawler installation root directory")
    ap.add_argument("--platform", "-p", default="xhs",
                    help="platform: xhs|dy|ks|bili|wb|tieba|zhihu|all (default xhs)")
    ap.add_argument("--dry-run", action="store_true", help="only print the changes that would be made, write nothing")
    ap.add_argument("--check", action="store_true", help="health check: report the status of each hardening layer")
    ap.add_argument("--revert", action="store_true", help="fully restore from .bak")
    ap.add_argument("--canary", action="store_true",
                    help="offline decay check: hardening still present / anchor drift / resource health (no browser)")
    args = ap.parse_args(argv)

    root = os.path.abspath(os.path.expanduser(args.path))
    if args.platform != "all" and args.platform not in PLATFORMS:
        sys.exit(_r(f"✗ unknown platform {args.platform}. Choices: {', '.join(PLATFORMS)} or all"))
    targets = list(PLATFORMS) if args.platform == "all" else [args.platform]

    if args.canary:
        total = 0
        for plat in targets:
            print(_b(f"\n━━━ Canary {PLATFORMS[plat][1]}({plat}) ━━━"))
            total += do_canary(locate(root, plat))
        sys.exit(1 if total else 0)

    for plat in targets:
        files = locate(root, plat)
        _, pname, level = PLATFORMS[plat]
        if args.check:
            print(_b(f"\n━━━ {pname}({plat}) · anti-crawl strength: {level} ━━━"))
            do_check(files)
            continue
        if args.revert:
            print(_b(f"\n━━━ Revert {pname}({plat}) ━━━"))
            do_revert(files, root)
            continue
        print(_b(f"\n━━━ Harden {pname}({plat}) · anti-crawl strength: {level} ━━━"))
        if args.dry_run:
            print(_y("(dry-run: the changes below are not actually written to disk)"))
        patch_base_config(files["base_config"], args.dry_run)
        patch_cdp_browser(files["cdp"], args.dry_run)
        patch_core(files["core"], args.dry_run, plat)
        ensure_stealth_js(files["stealth"], args.dry_run)
        deploy_modules(root, args.dry_run)
        if level in ("very high", "high") and not args.dry_run:
            print(_y(f"  ⚠ {pname} anti-crawl is {level}: raise CRAWLER_MAX_SLEEP_SEC further and keep volume smaller"))

    print(_b("\n═══ Done ═══"))
    print("  Health check: python apply_hardening.py <path> -p all --check")
    print("  Revert:       python apply_hardening.py <path> -p <platform> --revert")
    if not args.dry_run and not args.check and not args.revert:
        print(_y("  ⚠ Always trial-run on a throwaway account first; never point a scraper at your main account"))


if __name__ == "__main__":
    main()
