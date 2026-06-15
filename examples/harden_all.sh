#!/bin/bash
# examples/harden_all.sh — apply_hardening.py 常用调用示范
#
# 注意：这是演示脚本，不能直接运行（路径需换成你自己的 MediaCrawler 安装路径）。
#       Windows 用户请参考 examples/README.md 里的等价 Python 调用方式。

MC="/path/to/MediaCrawler"  # ← 改成你的 MediaCrawler 安装路径

# ── 1. 先 dry-run 看会改什么，不落盘 ──────────────────────────────────
python scripts/apply_hardening.py "$MC" -p xhs --dry-run

# ── 2. 正式打补丁（默认平台 = xhs）────────────────────────────────────
python scripts/apply_hardening.py "$MC"

# ── 3. 一次加固全部 7 个平台 ───────────────────────────────────────────
python scripts/apply_hardening.py "$MC" -p all

# ── 4. 体检：查看每层加固是否已生效 ──────────────────────────────────
python scripts/apply_hardening.py "$MC" -p all --check

# ── 5. 从备份完整还原（撤销所有改动）─────────────────────────────────
python scripts/apply_hardening.py "$MC" -p xhs --revert

# ── 6. 跨平台周维护（Python 版，Windows/Mac/Linux 均可）──────────────
python scripts/weekly_maintenance.py "$MC"
