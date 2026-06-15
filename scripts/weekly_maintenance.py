#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
weekly_maintenance.py — MediaCrawler 每周自动维护（跨平台 Python 版）

功能与 weekly_maintenance.sh 完全一致，但 Windows/Mac/Linux 均可运行：
  1. 从上游拉最新 stealth.min.js（反检测指纹库会随浏览器更新而过时）
  2. 检查上游 MediaCrawler 是否有新提交（仅提醒，不自动合并）

用法：
  python scripts/weekly_maintenance.py /path/to/MediaCrawler
  python scripts/weekly_maintenance.py          # 部署到 tools/ 下时自动推断根目录

建议挂到定时任务（每周一凌晨 3 点）：
  # Mac/Linux cron：
  0 3 * * 1 python /path/to/weekly_maintenance.py /path/to/MediaCrawler
  # Windows 任务计划程序：同样的命令
"""

import os
import subprocess
import sys
import urllib.request
from datetime import datetime

STEALTH_URL = (
    "https://raw.githubusercontent.com/berstend/puppeteer-extra/master/"
    "packages/puppeteer-extra-plugin-stealth/evasions/_utils/stealth.min.js"
)


def locate_root(argv):
    """定位 MediaCrawler 根目录：优先用命令行参数，否则推断（假设脚本在 tools/ 下）。"""
    if len(argv) > 1:
        return os.path.abspath(argv[1])
    # 无参数：假设本脚本部署在 <root>/tools/ 下，取上级目录
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, ".."))


def validate_root(root):
    """确认是 MediaCrawler 安装。"""
    marker = os.path.join(root, "config", "base_config.py")
    if not os.path.isfile(marker):
        print(f"✗ {root} 不像 MediaCrawler 安装（缺 config/base_config.py）")
        print("  用法：python weekly_maintenance.py /path/to/MediaCrawler")
        sys.exit(1)


def update_stealth(root, log):
    """下载最新 stealth.min.js，校验后原子覆盖。"""
    dst = os.path.join(root, "libs", "stealth.min.js")
    tmp = dst + ".tmp"
    _log(log, "[stealth] 从上游下载…")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        with urllib.request.urlopen(STEALTH_URL, timeout=30) as resp:
            data = resp.read()
        # 校验：非空且含 stealth 特征串，才覆盖
        if len(data) > 1000 and b"webdriver" in data:
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, dst)   # 原子替换，防中断损坏
            _log(log, f"[stealth] ✓ 更新成功 ({len(data)} bytes)")
        else:
            _log(log, "[stealth] ⚠ 下载内容异常，保留原版本")
            if os.path.exists(tmp):
                os.remove(tmp)
    except Exception as e:
        _log(log, f"[stealth] ⚠ 下载失败（{e}），保留原版本")
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def check_upstream(root, log):
    """检查上游是否有新提交，仅提醒不自动合并。"""
    _log(log, "[upstream] 检查 GitHub 最新状态…")
    git_dir = os.path.join(root, ".git")
    if not os.path.isdir(git_dir):
        _log(log, "[upstream] ⚠ 非 git 仓库，跳过")
        return

    def _run(cmd):
        return subprocess.run(
            cmd, capture_output=True, text=True, cwd=root
        )

    # fetch origin
    r = _run(["git", "fetch", "origin", "--quiet"])
    if r.returncode != 0:
        _log(log, f"[upstream] ⚠ git fetch 失败：{r.stderr.strip()}")
        return

    # 当前分支名
    r_branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    branch = r_branch.stdout.strip() if r_branch.returncode == 0 else "main"

    # 落后提交数
    r_count = _run(["git", "rev-list", f"HEAD..origin/{branch}", "--count"])
    try:
        behind = int(r_count.stdout.strip())
    except ValueError:
        behind = 0

    if behind > 0:
        _log(log, f"[upstream] ⚠ 上游有 {behind} 个新提交，可能含反检测修复")
        r_log = _run(["git", "log", f"origin/{branch}", "--oneline", "-5"])
        if r_log.returncode == 0:
            for line in r_log.stdout.strip().splitlines():
                _log(log, f"[upstream]   {line}")
        _log(log, "[upstream]   合并前先备份加固：apply_hardening.py <root> --revert 后再 git pull 再重打")
        # macOS 桌面通知（非 macOS 自动忽略）
        _notify(f"MediaCrawler 上游有 {behind} 个新提交", "小红书爬虫维护")
    else:
        _log(log, "[upstream] ✓ 已是最新")


def _log(log_path, msg):
    """同时打印到终端和日志文件。"""
    print(msg)
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except OSError:
        pass


def _notify(message, title):
    """macOS 桌面通知，非 macOS 静默忽略。"""
    if sys.platform != "darwin":
        return
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{message}" with title "{title}"'],
            capture_output=True, timeout=5,
        )
    except Exception:
        pass


def main():
    root = locate_root(sys.argv)
    validate_root(root)

    log_path = os.path.join(root, "maintenance.log")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    _log(log_path, f"=== {ts} 周维护开始 ({root}) ===")

    update_stealth(root, log_path)
    check_upstream(root, log_path)

    _log(log_path, "=== 维护完成 ===")
    _log(log_path, "")


if __name__ == "__main__":
    main()
