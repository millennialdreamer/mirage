# -*- coding: utf-8 -*-
"""
一键切换 MediaCrawler 的"安全档 / 常规档 / 激进档"

用法:
    python config/safe_profile.py            # 不带参数 → 只显示当前状态
    python config/safe_profile.py safe       # 切到安全档(最稳,最慢)
    python config/safe_profile.py normal     # 切到常规档(平衡)
    python config/safe_profile.py fast       # 切到激进档(快,容易被风控)

首次切档时会自动把原配置备份到 config/base_config.py.bak。
"""

import os
import re
import sys
import shutil

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "base_config.py")
BACKUP_PATH = CONFIG_PATH + ".bak"

PROFILES = {
    "safe":   {"CRAWLER_MAX_SLEEP_SEC": 6, "CRAWLER_MAX_NOTES_COUNT": 8,  "MAX_CONCURRENCY_NUM": 1},
    "normal": {"CRAWLER_MAX_SLEEP_SEC": 3, "CRAWLER_MAX_NOTES_COUNT": 15, "MAX_CONCURRENCY_NUM": 1},
    "fast":   {"CRAWLER_MAX_SLEEP_SEC": 1, "CRAWLER_MAX_NOTES_COUNT": 30, "MAX_CONCURRENCY_NUM": 3},
}


def read_current() -> dict:
    """从 base_config.py 解析当前数值。"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        text = f.read()
    out = {}
    for key in ("CRAWLER_MAX_SLEEP_SEC", "CRAWLER_MAX_NOTES_COUNT", "MAX_CONCURRENCY_NUM"):
        m = re.search(rf"^{key}\s*=\s*(\d+)", text, re.MULTILINE)
        out[key] = int(m.group(1)) if m else None
    return out


def apply_profile(name: str) -> None:
    """把指定档位的值写回 base_config.py。"""
    if name not in PROFILES:
        sys.exit(f"未知档位: {name}。可选: {', '.join(PROFILES)}")

    if not os.path.exists(BACKUP_PATH):
        shutil.copy2(CONFIG_PATH, BACKUP_PATH)
        print(f"✓ 原配置已备份 → {BACKUP_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    for key, value in PROFILES[name].items():
        text, n = re.subn(
            rf"^({key}\s*=\s*)\d+",
            rf"\g<1>{value}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if n == 0:
            print(f"⚠ 没找到 {key},跳过")

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"✓ 已切换到「{name}」档")


def print_status(current: dict) -> None:
    """显示当前档位 + 估算抓取速率。"""
    # 推断当前是哪档(任何一项不匹配都算 "custom")
    matched = next(
        (name for name, vals in PROFILES.items() if all(current.get(k) == v for k, v in vals.items())),
        "custom",
    )

    sleep_sec = current.get("CRAWLER_MAX_SLEEP_SEC") or 0
    avg_jitter = sleep_sec * 1.15  # 0.7x~1.6x 的平均值
    notes_per_run = current.get("CRAWLER_MAX_NOTES_COUNT") or 0
    # 每条笔记约 2 次 sleep(翻页 + 取详情),保守估
    estimated_seconds = notes_per_run * avg_jitter * 2

    print("=" * 50)
    print(f" 当前档位: {matched}")
    print("-" * 50)
    print(f" CRAWLER_MAX_SLEEP_SEC     = {current['CRAWLER_MAX_SLEEP_SEC']}  (实际抖动 ~{sleep_sec*0.7:.1f}s 到 {sleep_sec*1.6:.1f}s)")
    print(f" CRAWLER_MAX_NOTES_COUNT   = {current['CRAWLER_MAX_NOTES_COUNT']}  (单次抓取上限)")
    print(f" MAX_CONCURRENCY_NUM       = {current['MAX_CONCURRENCY_NUM']}  (并发数)")
    print("-" * 50)
    if notes_per_run:
        print(f" 估算抓 {notes_per_run} 条耗时: ~{estimated_seconds:.0f}s ({estimated_seconds/60:.1f} 分钟)")
        per_100 = (100 / notes_per_run) * estimated_seconds
        print(f" 估算抓 100 条耗时: ~{per_100/60:.1f} 分钟")
    print("=" * 50)
    print(" 切档:  python config/safe_profile.py [safe|normal|fast]")
    if os.path.exists(BACKUP_PATH):
        print(f" 恢复:  cp {BACKUP_PATH} {CONFIG_PATH}")


def main():
    if len(sys.argv) >= 2:
        apply_profile(sys.argv[1])
    print_status(read_current())


if __name__ == "__main__":
    main()
