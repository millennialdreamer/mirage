# -*- coding: utf-8 -*-
"""
mirage —— 统一命令行入口。把一堆 `python scripts/xxx.py` 收拢成 `mirage <子命令>`。

子命令：
  mirage apply <MediaCrawler路径> [-p 平台] [--dry-run|--check|--revert]   打/查/撤 五层加固
  mirage doctor                  环境自检（Python / Playwright / 探测 MediaCrawler）
  mirage canary <路径>           离线失效体检（加固是否还在/锚点失配/资源健康）
  mirage radar                   ⭐软封杀预警：从趋势看出"正在被降权"（被封之前）
  mirage guard-install <路径>    装 git hook：pull 后提示加固是否被覆盖
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
        import patchright  # noqa: F401
        print("  patchright   ✓ 已安装（Playwright 补丁版，已补 CDP Runtime.Enable 泄漏）")
    except ImportError:
        try:
            import playwright  # noqa: F401
            print("  Playwright   ✓ 已安装，但 ⚠ 建议改用 patchright：")
            print("               pip install patchright && patchright install chromium")
            print("               （原生 Playwright 启动时自动发 CDP Runtime.Enable，")
            print("                 会留下可被 JS 侦测的痕迹，注入脚本层补不了这一层）")
        except ImportError:
            print("  浏览器驱动   ⚠ 未安装 —— 推荐：pip install patchright && patchright install chromium")
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


# —— guard：给 MediaCrawler 的 git 仓库装 post-merge hook，pull 后提示加固是否被覆盖 ——
# 裁决：默认「提示模式」，只跑只读的 mirage canary + echo 提示，**不静默改第三方源码**（改源码需用户知情）。
_HOOK_MARK = "# Mirage guard"
_POST_MERGE_HOOK = '''#!/bin/bash
# Mirage guard — post-merge hook（由 mirage guard-install 安装）
# pull/merge 后检查加固是否被上游覆盖；丢了只提示、不自动改源码（改源码需你知情）。
REPO="$(git rev-parse --show-toplevel)"
if [ -f "$REPO/config/base_config.py" ] && command -v mirage >/dev/null 2>&1; then
    if ! mirage canary "$REPO" >/dev/null 2>&1; then
        echo "[Mirage] 上游 pull 可能覆盖了反检测加固。重打：mirage apply '$REPO'"
    fi
fi
'''


def _profile(seed, emit):
    """设备画像：一致性 > 单值伪装。所有注入值从同一张画像派生，避免自相矛盾。"""
    try:
        from device_profile import DeviceProfile
    except ImportError:
        from mirage.device_profile import DeviceProfile
    p = DeviceProfile.from_seed(seed)
    print("\n" + p.summary())
    problems = p.check()
    if problems:
        print("\n  ✗ 自洽校验发现矛盾：")
        for x in problems:
            print(f"    - {x}")
    else:
        print("\n  ✓ 自洽校验通过：UA / platform / GPU / 语言 / 时区 互不矛盾")
    if emit:
        path = os.path.abspath(os.path.expanduser(emit))
        with open(path, "w", encoding="utf-8") as f:
            f.write(p.to_init_script())
        print(f"\n  注入脚本已写出：{path}")
        print("  用法：await context.add_init_script(path=<该文件>)  （或 script=文件内容）")
    print("\n  ⚠ 注入层天花板：挡不住 TLS/JA3、worker realm 对拍、toString 审计——"
          "对静态检测有效(约7-8成)，对 CreepJS 主动对拍封顶约 4-5 成。详见 scripts/device_profile.py 头部说明。")
    return 0


def _radar(account, do_reset):
    """软封杀预警面板：看趋势判断当前是否正在被降权。"""
    try:
        from soft_ban_radar import SoftBanRadar
    except ImportError:
        from mirage.soft_ban_radar import SoftBanRadar
    radar = SoftBanRadar(account=account)
    if do_reset:
        radar.reset()
        print(f"✓ 已清空账号「{account}」的基线（换号/换 IP 后旧基线不再适用）")
        return 0
    v = radar.assess()
    icon = {"正常": "✓", "观察": "·", "警戒": "⚠", "危险": "🛑", "数据不足": "?"}.get(v.level, "·")
    print(f"\n{icon} 软封杀雷达 · 账号「{account}」")
    print(f"  等级：{v.level}   风险分：{v.score}/100   观测样本：{v.samples}")
    if v.signals:
        print("  信号：")
        for k, val in v.signals.items():
            print(f"    {k}: {val}")
    print(f"  建议：{v.advice}")
    print("\n  ⚠ 这是趋势启发式判断，不是精确判定；它不替代风控熔断，两者都要有。")
    return 0


def _guard_install(path):
    """给 MediaCrawler 的 git 仓库装 post-merge hook：pull 后提示加固是否被覆盖（不自动改源码）。"""
    import shutil
    import stat
    root = os.path.abspath(os.path.expanduser(path))
    if not os.path.isdir(os.path.join(root, ".git")):
        print(f"✗ {root} 不是 git 仓库（无 .git），无法装 hook")
        return 1
    hooks = os.path.join(root, ".git", "hooks")
    os.makedirs(hooks, exist_ok=True)
    hook = os.path.join(hooks, "post-merge")
    if os.path.isfile(hook) and _HOOK_MARK not in open(hook, encoding="utf-8").read():
        shutil.copy2(hook, hook + ".pre-mirage.bak")
        print("  已备份原有 post-merge → post-merge.pre-mirage.bak")
    with open(hook, "w", encoding="utf-8") as f:
        f.write(_POST_MERGE_HOOK)
    os.chmod(hook, os.stat(hook).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    print(f"✓ Mirage guard 已装：{hook}")
    print("  此后该 MediaCrawler 每次 git pull/merge 后，会自动提示加固是否被覆盖。")
    return 0


def _guard_uninstall(path):
    """卸载 guard hook（有备份则恢复，否则删除）。"""
    import shutil
    root = os.path.abspath(os.path.expanduser(path))
    hook = os.path.join(root, ".git", "hooks", "post-merge")
    if not os.path.isfile(hook) or _HOOK_MARK not in open(hook, encoding="utf-8").read():
        print("  未发现 Mirage guard hook")
        return 0
    bak = hook + ".pre-mirage.bak"
    if os.path.isfile(bak):
        shutil.move(bak, hook)
        print("✓ 已卸载 Mirage guard，恢复原有 post-merge")
    else:
        os.remove(hook)
        print("✓ 已卸载 Mirage guard")
    return 0


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
    pgi = sub.add_parser("guard-install", help="给 MediaCrawler 装 git hook：pull 后提示加固是否被覆盖")
    pgi.add_argument("path", help="MediaCrawler 安装根目录（git 仓库）")
    pgu = sub.add_parser("guard-uninstall", help="卸载 guard hook")
    pgu.add_argument("path", help="MediaCrawler 安装根目录")
    pp = sub.add_parser("profile", help="设备画像：生成自洽指纹画像 + 校验矛盾 + 导出注入脚本")
    pp.add_argument("seed", help="种子（同种子永远得到同一套画像；建议一个账号一个种子）")
    pp.add_argument("--emit", metavar="PATH", default="", help="把注入 JS 写到文件（供 add_init_script 用）")
    pr = sub.add_parser("radar", help="软封杀预警：看当前是否正在被降权（趋势判断）")
    pr.add_argument("--account", default="default", help="账号标识（不同账号分别建基线）")
    pr.add_argument("--reset", action="store_true", help="清空该账号基线（换号/换 IP 后用）")

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
        print(f"⚠ {args.cmd} 会启动真实浏览器，请你**自己手动**跑（CLI 不代跑，与铁律一致）：")
        print(f"    python scripts/{script}")
        if args.cmd == "benchmark":
            print(f"    python scripts/{script} --self-test   # 只验证评分逻辑（无浏览器）")
        return None
    parser.print_help()
    return None


if __name__ == "__main__":
    sys.exit(main())   # 让 guard-install 等靠返回值的子命令退出码生效（None/0→0，1→1）
