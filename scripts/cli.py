# -*- coding: utf-8 -*-
"""
mirage —— 统一命令行入口。把一堆 `python scripts/xxx.py` 收拢成 `mirage <子命令>`。

子命令：
  mirage apply <MediaCrawler路径> [-p 平台] [--dry-run|--check|--revert]   打/查/撤 五层加固
  mirage doctor                  环境自检（Python / Playwright / 探测 MediaCrawler）
  mirage verify                  指纹自检（开浏览器，请手动跑）
  mirage benchmark               指纹打分（开浏览器，请手动跑）

装好后（pip install -e .）即可直接 `mirage apply ...`，无需 sys.path hack。
"""
import argparse
import glob
import os
import sys

try:                      # 包语境（pip 安装后）
    from . import apply_hardening
except ImportError:       # 扁平语境（python scripts/cli.py）
    import apply_hardening


def _doctor():
    print("Mirage doctor —— 环境自检")
    ok = sys.version_info >= (3, 9)
    print(f"  Python {sys.version.split()[0]}   {'✓' if ok else '⚠ 建议 3.9+'}")
    try:
        import playwright  # noqa: F401
        print("  Playwright   ✓ 已安装（verify / benchmark 可跑）")
    except ImportError:
        print("  Playwright   ⚠ 未安装 —— 需要时：pip install playwright && playwright install chromium")
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
        print("  MediaCrawler ? 未在常见位置探测到（apply 时手动指定路径即可）")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mirage", description="Mirage 反检测加固工具集（仅供学习研究）")
    sub = parser.add_subparsers(dest="cmd")

    pa = sub.add_parser("apply", help="给 MediaCrawler 打 / 查 / 撤 五层加固")
    pa.add_argument("path", help="MediaCrawler 安装根目录")
    pa.add_argument("--platform", "-p", default="xhs", help="平台 xhs|dy|ks|bili|wb|tieba|zhihu|all")
    pa.add_argument("--dry-run", action="store_true")
    pa.add_argument("--check", action="store_true")
    pa.add_argument("--revert", action="store_true")

    sub.add_parser("doctor", help="环境自检")
    sub.add_parser("verify", help="指纹自检（开浏览器，请手动跑）")
    sub.add_parser("benchmark", help="指纹 benchmark 打分（开浏览器，请手动跑）")
    pc = sub.add_parser("canary", help="离线失效体检（加固是否还在/锚点失配/资源健康）")
    pc.add_argument("path", help="MediaCrawler 安装根目录")
    pc.add_argument("--platform", "-p", default="xhs", help="平台 xhs|dy|ks|bili|wb|tieba|zhihu|all")

    args = parser.parse_args(argv)

    if args.cmd == "apply":
        # 透传给 apply_hardening.main，复用其完整逻辑（不重复实现）
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
    if args.cmd == "doctor":
        return _doctor()
    if args.cmd in ("verify", "benchmark"):
        script = "verify_stealth.py" if args.cmd == "verify" else "fingerprint_benchmark.py"
        print(f"⚠ {args.cmd} 会启动真实浏览器，请你**自己手动**跑（CLI 不代跑，与铁律一致）：")
        print(f"    python scripts/{script}")
        if args.cmd == "benchmark":
            print(f"    python scripts/{script} --self-test   # 只验证评分逻辑（无浏览器）")
        return None
    parser.print_help()
    return None


if __name__ == "__main__":
    main()
