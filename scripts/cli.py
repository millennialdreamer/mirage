# -*- coding: utf-8 -*-
"""
mirage —— unified CLI entry. Consolidates a bunch of `python scripts/xxx.py` into `mirage <subcommand>`.

Subcommands:
  mirage apply <MediaCrawler path> [-p platform] [--dry-run|--check|--revert]   apply / check / revert five-layer hardening
  mirage doctor                  environment self-check (Python / Playwright / probe MediaCrawler)
  mirage canary <path>           offline health check (hardening still present / anchor mismatch / resource health)
  mirage radar                   ⭐ soft-ban early warning: spot "being deprioritized" from trends (before ban)
  mirage guard-install <path>    install git hook: after pull, prompt if hardening was overwritten
  mirage verify                  fingerprint self-check (opens browser, run manually)
  mirage benchmark               fingerprint scoring (opens browser, run manually)

After installing (pip install -e .) you can directly `mirage apply ...`, no sys.path hack.
"""
import argparse
import glob
import os
import sys

try:                      # package context (after pip install)
    from . import apply_hardening
except ImportError:       # flat context (python scripts/cli.py)
    import apply_hardening


def _doctor():
    print("Mirage doctor —— environment self-check")
    ok = sys.version_info >= (3, 9)
    print(f"  Python {sys.version.split()[0]}   {'✓' if ok else '⚠ recommend 3.9+'}")
    try:
        import patchright  # noqa: F401
        print("  patchright   ✓ installed (Playwright patched build, CDP Runtime.Enable leak patched)")
    except ImportError:
        try:
            import playwright  # noqa: F401
            print("  Playwright   ✓ installed, but ⚠ recommend switching to patchright:")
            print("               pip install patchright && patchright install chromium")
            print("               (native Playwright sends CDP Runtime.Enable automatically at startup,")
            print("                 leaving traces detectable by JS; the injection script layer cannot patch this layer)")
        except ImportError:
            print("  Browser driver ⚠ not installed — recommended: pip install patchright && patchright install chromium")
    found = []
    for base in (os.path.expanduser("~/Documents"), os.path.expanduser("~")):
        try:
            found += glob.glob(os.path.join(base, "*", "MediaCrawler", "config", "base_config.py"))
            found += glob.glob(os.path.join(base, "MediaCrawler", "config", "base_config.py"))
        except Exception:
            pass
    if found:
        for f in sorted(set(found))[:5]:
            print(f"  MediaCrawler ✓ {os.path.dirname(os.path.dirname(f))}")
    else:
        print("  MediaCrawler ? not detected in common locations (specify path manually when applying)")


# —— guard: install a post-merge hook in MediaCrawler's git repo; after pull, warn if hardening was overwritten ——
# Decision: default "prompt mode" — only run read-only mirage canary + echo prompt, **never silently modify third-party source**
# (source changes require user awareness).
_HOOK_MARK = "# Mirage guard"
_POST_MERGE_HOOK = '''#!/bin/bash
# Mirage guard — post-merge hook (installed by mirage guard-install)
# After pull/merge, check if hardening was overwritten by upstream; if lost, only warn — do not auto-modify source (source changes
# require your awareness).
REPO="$(git rev-parse --show-toplevel)"
if [ -f "$REPO/config/base_config.py" ] && command -v mirage >/dev/null 2>&1; then
    if ! mirage canary "$REPO" >/dev/null 2>&1; then
        echo "[Mirage] Upstream pull may have overwritten anti-detection hardening. Re-apply: mirage apply '$REPO'"
    fi
fi
'''


def _profile(seed, emit):
    """Device profile: consistency > single-value disguise. All injected values derive from one profile to avoid self-contradiction."""
    try:
        from device_profile import DeviceProfile
    except ImportError:
        from mirage.device_profile import DeviceProfile
    p = DeviceProfile.from_seed(seed)
    print("\n" + p.summary())
    problems = p.check()
    if problems:
        print("\n  ✗ self-consistency check found contradictions:")
        for x in problems:
            print(f"    - {x}")
    else:
        print("\n  ✓ self-consistency check passed: UA / platform / GPU / language / timezone do not contradict each other")
    if emit:
        path = os.path.abspath(os.path.expanduser(emit))
        with open(path, "w", encoding="utf-8") as f:
            f.write(p.to_init_script())
        print(f"\n  Injection script written to: {path}")
        print("  Usage: await context.add_init_script(path=<that file>)  (or script=file content)")
    print("\n  ⚠ Injection-layer ceiling: cannot stop TLS/JA3, worker realm cross-check, toString audit —"
          " effective against static detection (~70-80%), caps at ~40-50% against CreepJS active cross-check. See header of scripts/device_profile.py.")
    return 0


def _radar(account, do_reset):
    """Soft-ban early warning panel: use trends to judge whether currently being deprioritized."""
    try:
        from soft_ban_radar import SoftBanRadar
    except ImportError:
        from mirage.soft_ban_radar import SoftBanRadar
    radar = SoftBanRadar(account=account)
    if do_reset:
        radar.reset()
        print(f"✓ Cleared baseline for account \"{account}\" (old baseline no longer applies after changing account/IP)")
        return 0
    v = radar.assess()
    icon = {"normal": "✓", "watch": "·", "warning": "⚠", "danger": "🛑", "insufficient data": "?"}.get(v.level, "·")
    print(f"\n{icon} Soft-ban radar · account \"{account}\"")
    print(f"  Level: {v.level}   Risk score: {v.score}/100   Samples: {v.samples}")
    if v.signals:
        print("  Signals:")
        for k, val in v.signals.items():
            print(f"    {k}: {val}")
    print(f"  Advice: {v.advice}")
    print("\n  ⚠ This is a heuristic trend judgment, not an exact determination; it does not replace risk-control circuit breaker — both are needed.")
    return 0


def _guard_install(path):
    """Install a post-merge hook in MediaCrawler's git repo: after pull, prompt if hardening was overwritten (does not auto-modify source)."""
    import shutil
    import stat
    root = os.path.abspath(os.path.expanduser(path))
    if not os.path.isdir(os.path.join(root, ".git")):
        print(f"✗ {root} is not a git repo (no .git), cannot install hook")
        return 1
    hooks = os.path.join(root, ".git", "hooks")
    os.makedirs(hooks, exist_ok=True)
    hook = os.path.join(hooks, "post-merge")
    if os.path.isfile(hook) and _HOOK_MARK not in open(hook, encoding="utf-8").read():
        shutil.copy2(hook, hook + ".pre-mirage.bak")
        print("  Backed up existing post-merge → post-merge.pre-mirage.bak")
    with open(hook, "w", encoding="utf-8") as f:
        f.write(_POST_MERGE_HOOK)
    os.chmod(hook, os.stat(hook).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    print(f"✓ Mirage guard installed: {hook}")
    print("  From now on, after each git pull/merge in this MediaCrawler, it will automatically prompt if hardening was overwritten.")
    return 0


def _guard_uninstall(path):
    """Uninstall guard hook (restore backup if present, otherwise delete)."""
    import shutil
    root = os.path.abspath(os.path.expanduser(path))
    hook = os.path.join(root, ".git", "hooks", "post-merge")
    if not os.path.isfile(hook) or _HOOK_MARK not in open(hook, encoding="utf-8").read():
        print("  No Mirage guard hook found")
        return 0
    bak = hook + ".pre-mirage.bak"
    if os.path.isfile(bak):
        shutil.move(bak, hook)
        print("✓ Uninstalled Mirage guard, restored original post-merge")
    else:
        os.remove(hook)
        print("✓ Uninstalled Mirage guard")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mirage", description="Mirage anti-detection hardening toolkit (for study/research only)")
    sub = parser.add_subparsers(dest="cmd")

    pa = sub.add_parser("apply", help="Apply / check / revert five-layer hardening for MediaCrawler")
    pa.add_argument("path", help="MediaCrawler installation root directory")
    pa.add_argument("--platform", "-p", default="xhs", help="platform xhs|dy|ks|bili|wb|tieba|zhihu|all")
    pa.add_argument("--dry-run", action="store_true")
    pa.add_argument("--check", action="store_true")
    pa.add_argument("--revert", action="store_true")

    sub.add_parser("doctor", help="environment self-check")
    sub.add_parser("verify", help="fingerprint self-check (opens browser, run manually)")
    sub.add_parser("benchmark", help="fingerprint benchmark scoring (opens browser, run manually)")
    pc = sub.add_parser("canary", help="offline health check (hardening present / anchor mismatch / resource health)")
    pc.add_argument("path", help="MediaCrawler installation root directory")
    pc.add_argument("--platform", "-p", default="xhs", help="platform xhs|dy|ks|bili|wb|tieba|zhihu|all")
    pgi = sub.add_parser("guard-install", help="Install git hook for MediaCrawler: after pull, prompt if hardening was overwritten")
    pgi.add_argument("path", help="MediaCrawler installation root directory (git repo)")
    pgu = sub.add_parser("guard-uninstall", help="uninstall guard hook")
    pgu.add_argument("path", help="MediaCrawler installation root directory")
    pp = sub.add_parser("profile", help="Device profile: generate self-consistent fingerprint profile + validate contradictions + export injection script")
    pp.add_argument("seed", help="seed (same seed always yields same profile; one seed per account recommended)")
    pp.add_argument("--emit", metavar="PATH", default="", help="write injection JS to file (for add_init_script)")
    pr = sub.add_parser("radar", help="soft-ban early warning: see whether currently being deprioritized (trend judgment)")
    pr.add_argument("--account", default="default", help="account identifier (separate baseline per account)")
    pr.add_argument("--reset", action="store_true", help="clear baseline for this account (use after changing account/IP)")

    args = parser.parse_args(argv)

    if args.cmd == "apply":
        # Pass through to apply_hardening.main, reuse its full logic (no duplicate implementation)
        passthru = [args.path, "-p", args.platform]
        if args.dry_run:
            passthru.append("--dry-run")
        if args.check:
            passthru.append("--check")
        if args.revert:
            passthru.append("--revert")
        return apply_hardening.main(passthru)
    if args.cmd == "canary":
        return apply_hardening.main([args.path, "-p", args.platform, "--canary"])
    if args.cmd == "profile":
        return _profile(args.seed, args.emit)
    if args.cmd == "radar":
        return _radar(args.account, args.reset)
    if args.cmd == "guard-install":
        return _guard_install(args.path)
    if args.cmd == "guard-uninstall":
        return _guard_uninstall(args.path)
    if args.cmd == "doctor":
        return _doctor()
    if args.cmd in ("verify", "benchmark"):
        script = "verify_stealth.py" if args.cmd == "verify" else "fingerprint_benchmark.py"
        print(f"⚠ {args.cmd} will launch a real browser; please run it **manually yourself** (CLI does not run it for you, consistent with the iron rule):")
        print(f"    python scripts/{script}")
        if args.cmd == "benchmark":
            print(f"    python scripts/{script} --self-test   # only validates scoring logic (no browser)")
        return None
    parser.print_help()
    return None


if __name__ == "__main__":
    sys.exit(main())   # let exit codes of subcommands like guard-install take effect (None/0→0, 1→1)
