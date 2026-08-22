#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_hardening.py — 一键给 MediaCrawler 安装打入"五层反检测加固"。

设计铁律（这也是它"成熟"的原因）：
  1. 改任何文件前先备份到 <file>.xhs-stealth.bak（仅首次，不覆盖已有备份）。
  2. 所有注入代码用 `# [xhs-stealth]` 标记包裹 —— 天然幂等：打过补丁就跳过。
  3. 锚点找不到（MediaCrawler 版本结构不同）时，优雅降级 + 打印手动指引，
     绝不瞎改导致目标文件语法损坏。

用法：
  python apply_hardening.py /path/to/MediaCrawler            # 打补丁
  python apply_hardening.py /path/to/MediaCrawler --dry-run  # 只看会改什么，不落盘
  python apply_hardening.py /path/to/MediaCrawler --check    # 体检：每层加固状态
  python apply_hardening.py /path/to/MediaCrawler --revert   # 从 .bak 完整还原

五层防护：
  L1 stealth.min.js 自动注入   -> 隐藏 navigator.webdriver 等自动化指纹
  L2 随机抖动睡眠              -> 消除固定节拍这一机器特征
  L3 批次限制 + 安全默认参数    -> 降低单次曝光，强制真浏览器/单并发
  L4 启动预热                  -> 进搜索前先停留几秒，像真人看页面
  L5 鼠标 + 滚动模拟（尽力层）  -> 填补"睡眠期页面冻死"这一机器人信号
"""

import argparse
import os
import re
import shutil
import sys
import urllib.request

MARK = "[xhs-stealth]"          # 幂等标记
BAK_SUFFIX = ".xhs-stealth.bak"  # 备份后缀
STEALTH_URL = (
    "https://raw.githubusercontent.com/berstend/puppeteer-extra/master/"
    "packages/puppeteer-extra-plugin-stealth/evasions/_utils/stealth.min.js"
)

# 终端着色（无 tty 时自动关闭）
_C = sys.stdout.isatty()
def _g(s): return f"\033[32m{s}\033[0m" if _C else s   # green
def _y(s): return f"\033[33m{s}\033[0m" if _C else s   # yellow
def _r(s): return f"\033[31m{s}\033[0m" if _C else s   # red
def _b(s): return f"\033[1m{s}\033[0m" if _C else s    # bold


# ════════════════════════════════════════════════════════════════════
# 基础 IO
# ════════════════════════════════════════════════════════════════════
def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, text):
    """原子写：先写同目录临时文件、fsync，再 os.replace 原子替换。
    避免写到一半被中断（崩溃/磁盘满/断电）而留下半截损坏的目标文件。
    假设 path 是普通文件（MediaCrawler 源码均如此）；不处理符号链接。"""
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
                shutil.copystat(path, tmp)   # 尽量保留原权限/时间戳
            except OSError:
                pass                          # 异常文件系统不支持则忽略，不阻断写入
        os.replace(tmp, path)            # 同一文件系统上原子替换
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def backup(path, dry):
    """首次改动前备份；已存在备份则不覆盖（保护最原始版本）。"""
    bak = path + BAK_SUFFIX
    if os.path.exists(bak):
        return
    if dry:
        print(f"    {_y('[dry]')} 将备份 -> {os.path.basename(bak)}")
        return
    shutil.copy2(path, bak)
    print(f"    {_g('✓')} 已备份 -> {os.path.basename(bak)}")


def write_py_safe(path, text):
    """给 .py 源码打补丁的唯一安全落盘口：原子写 + 写后 ast.parse 语法自检；
    一旦语法损坏，立即从 .bak 回滚并退出，绝不把损坏的源码留给用户。
    前提：调用前已 backup(path)（三个 patch_* 都遵守先备份后改写）。"""
    import ast
    write(path, text)                       # 原子落盘
    try:
        ast.parse(read(path))
    except SyntaxError as e:
        bak = path + BAK_SUFFIX
        if os.path.isfile(bak):
            write(path, read(bak))   # 回滚也走原子写，避免回滚中断再次损坏
            sys.exit(_r(f"✗ {os.path.basename(path)} 补丁后语法错误，已从备份回滚：{e}"))
        sys.exit(_r(f"✗ {os.path.basename(path)} 补丁后语法错误，且无 .bak 可回滚：{e}"))


# ════════════════════════════════════════════════════════════════════
# 定位与校验
# ════════════════════════════════════════════════════════════════════
# MediaCrawler 支持的平台：别名 -> (目录名, 中文名, 反爬强度)
PLATFORMS = {
    "xhs":   ("xhs",      "小红书", "中"),
    "dy":    ("douyin",   "抖音",   "极高"),
    "ks":    ("kuaishou", "快手",   "高"),
    "bili":  ("bilibili", "B站",    "中低"),
    "wb":    ("weibo",    "微博",   "中"),
    "tieba": ("tieba",    "贴吧",   "低"),
    "zhihu": ("zhihu",    "知乎",   "中"),
}


def locate(root, platform="xhs"):
    """确认 root 是 MediaCrawler 安装，返回指定平台的关键文件路径。"""
    pdir = PLATFORMS.get(platform, (platform, platform, "?"))[0]
    files = {
        "base_config": os.path.join(root, "config", "base_config.py"),
        "core": os.path.join(root, "media_platform", pdir, "core.py"),
        "cdp": os.path.join(root, "tools", "cdp_browser.py"),
        "stealth": os.path.join(root, "libs", "stealth.min.js"),
        "platform": platform,
    }
    if not os.path.isfile(files["base_config"]):
        sys.exit(_r(f"✗ {root} 不是 MediaCrawler 安装（缺 config/base_config.py）"))
    if not os.path.isfile(files["core"]):
        sys.exit(_r(f"✗ 找不到 {platform} 平台的 core.py：media_platform/{pdir}/core.py"))
    return files


# ════════════════════════════════════════════════════════════════════
# L3 — base_config.py 安全参数
# ════════════════════════════════════════════════════════════════════
# 目标参数：键 -> (目标值, 中文说明)
SAFE_PARAMS = {
    "CRAWLER_MAX_SLEEP_SEC":   ("6",    "基础间隔放慢到 6s（抖动后实际 4.2~9.6s）"),
    "CRAWLER_MAX_NOTES_COUNT": ("8",    "单次抓取上限降到 8 条"),
    "MAX_CONCURRENCY_NUM":     ("1",    "强制单并发，最像真人"),
    "ENABLE_CDP_MODE":         ("True", "用真 Chrome（CDP），反检测最强"),
    "CDP_CONNECT_EXISTING":    ("True", "复用你已登录的浏览器"),
    "HEADLESS":                ("False","禁用无头模式（无头最易被识别）"),
    "SAVE_LOGIN_STATE":        ("True", "保留登录态，最像真人"),
}


def patch_base_config(path, dry):
    """正则把若干关键参数改成安全值。纯值替换 -> 天然幂等。"""
    print(_b("\n[L3] base_config.py 安全参数"))
    text = read(path)
    changed = False
    for key, (target, why) in SAFE_PARAMS.items():
        # 值取第一段非空白（数字/True/False/无空格串），尾部 .* 原样保留（含行尾注释）。
        # 不再用 [^\n#]+? —— 避免值中含 '#'（如字符串里）被误当注释截断。
        pat = re.compile(rf"^({re.escape(key)}\s*=\s*)(\S+)(.*)$", re.MULTILINE)
        m = pat.search(text)
        if not m:
            print(f"    {_y('⚠')} 没找到 {key}，跳过")
            continue
        cur = m.group(2).strip()
        if cur == target:
            print(f"    {_g('·')} {key} 已是 {target}")
            continue
        if not changed and not dry:
            backup(path, dry)
        changed = True
        text = pat.sub(rf"\g<1>{target}\g<3>", text, count=1)
        print(f"    {_g('✓') if not dry else _y('[dry]')} {key}: {cur} -> {target}  （{why}）")
    if changed and not dry:
        write_py_safe(path, text)
    if not changed:
        print(f"    {_g('全部已是安全值')}")


# ════════════════════════════════════════════════════════════════════
# L1 — cdp_browser.py 自动注入 stealth
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
    """给 CDP 管理器注入 _auto_inject_stealth，并在每个 return browser_context 前调用。"""
    print(_b("\n[L1] cdp_browser.py 自动注入 stealth.min.js"))
    if not os.path.isfile(path):
        print(f"    {_y('⚠')} 没有 tools/cdp_browser.py（可能未启用 CDP 模式），跳过 L1")
        return
    text = read(path)

    if MARK in text:
        print(f"    {_g('·')} 已含 {MARK} 注入，跳过（幂等）")
        return

    # 锚点：返回 browser_context 的地方（CDP 启动 / 连接已存在 两条路径）
    ret_pat = re.compile(r"^(\s*)return browser_context\s*$", re.MULTILINE)
    rets = list(ret_pat.finditer(text))
    if not rets:
        print(f"    {_y('⚠')} 没找到 `return browser_context` 锚点 —— 此版本结构不同")
        print("      请手动在 CDP 启动后调用一次 stealth 注入（见 docs/anti-detection.md）")
        return

    backup(path, dry)
    # 在每个 return 前插入调用
    def _inject_call(m):
        indent = m.group(1)
        return f"{indent}await self._auto_inject_stealth()  # {MARK}\n{indent}return browser_context"
    new = ret_pat.sub(_inject_call, text)

    # 在【CDP 管理类内部】追加方法：先定位类，再插在类体顶部（class 行的下一行）。
    # 这样不会因"第一个 async def 在模块级或别的类"而把方法注入到错误作用域，
    # 也不会插在某方法的装饰器与 def 之间拆坏语法。
    cls = (re.search(r"^class\s+\w*CDP\w*[^\n]*:", new, re.MULTILINE)
           or re.search(r"^class\s+\w+[^\n]*:", new, re.MULTILINE))
    if cls:
        line_end = new.find("\n", cls.end())
        idx = (line_end + 1) if line_end != -1 else len(new)
        new = new[:idx] + STEALTH_METHOD.lstrip("\n") + "\n" + new[idx:]
    else:
        print(f"    {_y('⚠')} 没找到类定义锚点，仅插入了调用 —— 请手动补 _auto_inject_stealth")

    if dry:
        print(f"    {_y('[dry]')} 将注入 _auto_inject_stealth + {len(rets)} 处调用")
    else:
        write_py_safe(path, new)
        print(f"    {_g('✓')} 已注入方法 + {len(rets)} 处调用")


# ════════════════════════════════════════════════════════════════════
# L2 / L4 / L5 — core.py
# ════════════════════════════════════════════════════════════════════
WARMUP_BLOCK = '''        # [xhs-stealth] L4: human warm-up — pause on the page before the first search
        import random as _rnd, asyncio as _aio
        _warm = max(2.5, min(16.0, 5.5 * _rnd.lognormvariate(0, 0.40)))  # 右偏,非均匀
        await _aio.sleep(_warm)
'''

HUMAN_METHOD = '''
    async def _xhs_stealth_human_activity(self):
        # [xhs-stealth] L5: human-like scroll + bezier mouse move
        # 优先用部署好的 tools/human_behavior.py（单一真相源，鼠标走贝塞尔曲线而非瞬移）
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
            # 兜底：模块缺失时的最小内联版（仍走分步移动而非瞬移）
            import random as _rnd, asyncio as _aio
            await page.mouse.wheel(0, _rnd.randint(300, 700))
            await _aio.sleep(_rnd.uniform(0.4, 1.0))
            _x, _y = _rnd.randint(200, 900), _rnd.randint(200, 500)
            for _i in range(1, 11):
                _u = _i / 10
                _t = _u * _u * (3 - 2 * _u)      # 缓入缓出，避免直线匀速(匀速=机器人)
                await page.mouse.move(_x * _t + _rnd.uniform(-2, 2),
                                      _y * _t + _rnd.uniform(-2, 2))
                await _aio.sleep(0.019 * _rnd.lognormvariate(0, 0.35))
        except Exception:
            pass
'''


def _ensure_import_random(text):
    """确保 core.py 顶部有 import random；没有则在已有 import 区之后补一行。"""
    if re.search(r"^import random\b", text, re.MULTILINE):
        return text, False
    m = re.search(r"^import asyncio\b.*$", text, re.MULTILINE)
    if m:
        idx = m.end()
        return text[:idx] + f"\nimport random  # {MARK}" + text[idx:], True
    # 兜底1：插在最后一个顶格 import/from 行之后（绝不插到 shebang 或 # coding 声明之前）
    imports = list(re.finditer(r"^(?:import|from)\s+\S+.*$", text, re.MULTILINE))
    if imports:
        idx = imports[-1].end()
        return text[:idx] + f"\nimport random  # {MARK}" + text[idx:], True
    # 兜底2：无任何 import —— 插在第一个非空、非注释行之前
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
    """core.py：L2 抖动（稳）+ L4 预热（尽力）+ L5 鼠标模拟（尽力）。锚点平台无关。"""
    pdir = PLATFORMS.get(platform, (platform,))[0]
    print(_b(f"\n[L2/L4/L5] media_platform/{pdir}/core.py"))
    text = read(path)
    orig = text
    did_any = False

    # —— 确保 import random ——
    text, added = _ensure_import_random(text)
    if added:
        did_any = True
        print(f"    {_g('✓') if not dry else _y('[dry]')} 补上 import random")

    # —— L2: 把固定 sleep 改成抖动（覆盖 CRAWLER_MAX_SLEEP_SEC 和 crawl_interval）——
    sleep_pat = re.compile(
        r"^(\s*)await asyncio\.sleep\(\s*(config\.CRAWLER_MAX_SLEEP_SEC|crawl_interval)\s*\)\s*(?:#.*)?$",
        re.MULTILINE,
    )
    def _jitter(m):
        indent, expr = m.group(1), m.group(2)
        # 用对数正态（右偏）而非 uniform：真人间隔是"大量短 + 少量长尾"，
        # uniform 的直方图是平顶矩形，KS 检验能直接识别。lognormvariate(0,σ) 中位数=1，
        # 故 expr * lognormvariate(0,0.45) 的中位数就是原间隔，但形状是真的右偏曲线。
        return (f"{indent}await asyncio.sleep({expr} * "
                f"random.lognormvariate(0, 0.45))  # {MARK} L2 jitter")
    n_sleep = len(sleep_pat.findall(text))
    if n_sleep:
        text = sleep_pat.sub(_jitter, text)
        did_any = True
        print(f"    {_g('✓') if not dry else _y('[dry]')} L2: {n_sleep} 处固定 sleep -> 随机抖动")
    elif "L2 jitter" in text:
        print(f"    {_g('·')} L2 抖动已存在（幂等跳过）")
    else:
        print(f"    {_y('⚠')} 没找到固定 sleep 锚点 —— 此版本可能已改写，跳过 L2")

    # —— L4: 启动预热 —— 锚点：async def search 方法体开头（平台无关，兼容有无 -> None）——
    if "L4: human warm-up" in text:
        print(f"    {_g('·')} L4 预热已存在（幂等跳过）")
    else:
        search_def = re.search(
            r"^    async def search\(self\)(?:\s*->\s*[^\n:]+)?\s*:[^\n]*\n",
            text, re.MULTILINE,
        )
        if search_def:
            idx = search_def.end()
            # 跳过紧随的单行 docstring（若有），让预热插在它之后，保留 docstring
            doc = re.match(r'\s*(?:"""[^\n]*"""|\'\'\'[^\n]*\'\'\')\n', text[idx:])
            if doc:
                idx += doc.end()
            block = WARMUP_BLOCK if WARMUP_BLOCK.endswith("\n") else WARMUP_BLOCK + "\n"
            text = text[:idx] + block + text[idx:]
            did_any = True
            print(f"    {_g('✓') if not dry else _y('[dry]')} L4: 注入启动预热")
        else:
            print(f"    {_y('⚠')} 没找到 async def search 锚点，跳过 L4（可手动加）")

    # —— L5: 鼠标模拟方法 + 在翻页抖动 sleep 前调用 —— 尽力层 ——
    if "_xhs_stealth_human_activity" in text:
        print(f"    {_g('·')} L5 鼠标模拟已存在（幂等跳过）")
    else:
        injected_method = False
        # 方法定义：插在 search 方法**之后**的下一个同级方法前（平台无关；
        # 原 get_creators_and_notes 是小红书特有，不通用）
        sdef = re.search(r"^    async def search\(self\)", text, re.MULTILINE)
        if sdef:
            nd = re.search(r"^    (?:async )?def ", text[sdef.end():], re.MULTILINE)
            if nd:
                idx = sdef.end() + nd.start()
                text = text[:idx] + HUMAN_METHOD.lstrip("\n") + "\n" + text[idx:]
                injected_method = True
        # 调用点：限定在 search() 方法体内的第一处 L2 jitter 前。
        # 避免"第一个 L2 jitter 在别的函数"导致调用被注入到错误函数里。
        call_indent, call_global_start = None, None
        search_m = re.search(r"^    async def search\(", text, re.MULTILINE)
        if search_m:
            rest = text[search_m.end():]
            next_def = re.search(r"^    (?:async )?def ", rest, re.MULTILINE)
            seg_end = search_m.end() + (next_def.start() if next_def else len(rest))
            seg = text[search_m.end():seg_end]
            # 放宽：只认 sleep 行 + L2 jitter 标记，不锁定具体分布函数名
            # （既匹配新的 lognormvariate 形式，也兼容已部署的老 uniform 形式）
            cm = re.search(r"^(\s*)await asyncio\.sleep\([^\n]*L2 jitter",
                           seg, re.MULTILINE)
            if cm:
                call_indent = cm.group(1)
                call_global_start = search_m.end() + cm.start()
        if injected_method and call_global_start is not None:
            call_line = f"{call_indent}await self._xhs_stealth_human_activity()  # {MARK} L5\n"
            text = text[:call_global_start] + call_line + text[call_global_start:]
            did_any = True
            print(f"    {_g('✓') if not dry else _y('[dry]')} L5: 注入鼠标模拟方法 + 调用")
        elif injected_method:
            print(f"    {_g('✓') if not dry else _y('[dry]')} L5: 注入了方法，但没找到调用锚点（方法可被手动调用）")
        else:
            print(f"    {_y('⚠')} 没找到 L5 注入锚点，跳过（尽力层，不影响 L1-L4）")

    if did_any and text != orig:
        if not dry:
            backup(path, dry)
            write_py_safe(path, text)   # 原子写 + AST 自检 + 失败回滚（统一入口）
            print(f"    {_g('✓ 语法自检通过')}")
    elif not did_any:
        print(f"    {_g('core.py 无需改动或已全部加固')}")


# ════════════════════════════════════════════════════════════════════
# stealth.min.js 存在性
# ════════════════════════════════════════════════════════════════════
def ensure_stealth_js(path, dry):
    print(_b("\n[资源] libs/stealth.min.js"))
    if os.path.isfile(path) and os.path.getsize(path) > 1000:
        print(f"    {_g('·')} 已存在（{os.path.getsize(path)//1024}KB）")
        return
    if dry:
        print(f"    {_y('[dry]')} 缺失，将从上游下载")
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        print("    下载中 …")
        with urllib.request.urlopen(STEALTH_URL, timeout=30) as resp:
            data = resp.read()
        if b"webdriver" not in data:
            print(f"    {_y('⚠')} 下载内容异常，未写入。请手动放置 stealth.min.js")
            return
        with open(path, "wb") as f:
            f.write(data)
        print(f"    {_g('✓')} 已下载（{len(data)//1024}KB）")
    except Exception as e:
        print(f"    {_y('⚠')} 下载失败（{e}）。MediaCrawler 通常自带，可忽略")


# ════════════════════════════════════════════════════════════════════
# 部署辅助模块（safe_profile.py / human_behavior.py）
# ════════════════════════════════════════════════════════════════════
def deploy_modules(root, dry):
    print(_b("\n[部署] 辅助脚本 -> 目标 config/ 与 tools/"))
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
            print(f"    {_g('·')} {name} 已部署")
            continue
        if dry:
            print(f"    {_y('[dry]')} 将部署 {name} -> {os.path.relpath(dst, root)}")
            continue
        shutil.copy2(src, dst)
        print(f"    {_g('✓')} 部署 {name}")


# ════════════════════════════════════════════════════════════════════
# check / revert
# ════════════════════════════════════════════════════════════════════
def do_check(files):
    print(_b("\n═══ 加固体检 ═══"))
    def status(path, needle, label):
        if not os.path.isfile(path):
            print(f"  {_y('?')} {label}: 文件不存在")
            return
        print(f"  {_g('✓') if needle in read(path) else _r('✗')} {label}")
    bc = read(files["base_config"])
    ok_params = all(re.search(rf"^{k}\s*=\s*{re.escape(v)}\b", bc, re.MULTILINE)
                    for k, (v, _) in SAFE_PARAMS.items())
    print(f"  {_g('✓') if ok_params else _r('✗')} L3 base_config 安全参数")
    status(files["core"], "L2 jitter", "L2 抖动睡眠")
    status(files["core"], "L4: human warm-up", "L4 启动预热")
    status(files["core"], "_xhs_stealth_human_activity", "L5 鼠标模拟")
    if os.path.isfile(files["cdp"]):
        status(files["cdp"], MARK, "L1 stealth 自动注入")
    sj = files["stealth"]
    print(f"  {_g('✓') if os.path.isfile(sj) else _r('✗')} stealth.min.js 资源")


def do_revert(files, root):
    print(_b("\n═══ 从 .bak 还原 ═══"))
    restored = 0
    for p in list(files.values()) + [
        os.path.join(root, "config", "safe_profile.py"),
        os.path.join(root, "tools", "human_behavior.py"),
    ]:
        bak = p + BAK_SUFFIX
        if os.path.isfile(bak):
            shutil.copy2(bak, p)
            print(f"  {_g('✓')} 还原 {os.path.basename(p)}")
            restored += 1
    if restored == 0:
        print(f"  {_y('没有找到任何 .xhs-stealth.bak 备份')}")
    else:
        print(f"  {_g(f'共还原 {restored} 个文件')}（.bak 已保留，可重复还原）")


# ════════════════════════════════════════════════════════════════════
# canary — 离线失效体检
# ════════════════════════════════════════════════════════════════════
def do_canary(files):
    """离线失效体检：加固是否还在 / 锚点是否失配 / 资源是否健康。
    全程不发网络、不开浏览器（指纹层 webdriver/BotScore 请手动跑 verify/benchmark）。
    返回失效项数（0 = 健康）。"""
    print(_b("\n═══ Canary 失效体检（离线，不发请求）═══"))
    issues = []
    core_txt = read(files["core"]) if os.path.isfile(files["core"]) else ""
    bc_txt = read(files["base_config"]) if os.path.isfile(files["base_config"]) else ""

    # 1) 加固标记还在吗（被上游 pull 覆盖 / 手改会丢）
    if "L2 jitter" in core_txt and "L4: human warm-up" in core_txt:
        print(f"  {_g('✓')} core.py 五层加固标记在位")
    else:
        issues.append("core.py 加固标记缺失（疑被上游 pull 覆盖）→ 跑 `mirage apply` 重打")

    # 2) base_config 安全参数还是安全值吗
    bad = [k for k, (v, _) in SAFE_PARAMS.items()
           if not re.search(rf"^{k}\s*=\s*{re.escape(v)}\b", bc_txt, re.MULTILINE)]
    if not bad:
        print(f"  {_g('✓')} base_config 安全参数完好")
    else:
        issues.append(f"base_config 安全参数被改回：{', '.join(bad)} → 跑 `mirage apply` 重打")

    # 3) stealth.min.js 健康（存在 + 体积 + 含 webdriver 关键字）
    sj = files["stealth"]
    healthy = os.path.isfile(sj) and os.path.getsize(sj) > 1000
    if healthy:
        try:
            with open(sj, "rb") as f:
                healthy = b"webdriver" in f.read()
        except OSError:
            healthy = False
    if healthy:
        print(f"  {_g('✓')} stealth.min.js 健康（{os.path.getsize(sj)//1024}KB）")
    else:
        issues.append("stealth.min.js 缺失/损坏 → 跑 weekly_maintenance 更新")

    # 4) 上游结构变更检测：'async def search' 锚点是否还在（上游重构会失配）
    if core_txt:
        if re.search(r"^    async def search\(self\)", core_txt, re.MULTILINE):
            print(f"  {_g('✓')} 上游 search 锚点结构未变")
        else:
            issues.append("core.py 已无 'async def search(self)' 锚点（上游疑重构）→ 加固锚点可能失配，需人工核对")

    print()
    if issues:
        print(_r(f"  ⚠ 发现 {len(issues)} 项失效迹象："))
        for it in issues:
            print(f"    - {it}")
    else:
        print(_g("  ✓ 离线层加固健康，无失效迹象"))
    print(_y("  指纹层（webdriver/BotScore）非离线可测，建议定期手动跑："))
    print(_y("    python scripts/verify_stealth.py   |   python scripts/fingerprint_benchmark.py"))
    return len(issues)


# ════════════════════════════════════════════════════════════════════
def main(argv=None):
    ap = argparse.ArgumentParser(description="给 MediaCrawler 打入五层反检测加固（多平台）")
    ap.add_argument("path", help="MediaCrawler 安装根目录")
    ap.add_argument("--platform", "-p", default="xhs",
                    help="平台：xhs|dy|ks|bili|wb|tieba|zhihu|all（默认 xhs）")
    ap.add_argument("--dry-run", action="store_true", help="只打印将做的改动，不落盘")
    ap.add_argument("--check", action="store_true", help="体检：报告每层加固状态")
    ap.add_argument("--revert", action="store_true", help="从 .bak 完整还原")
    ap.add_argument("--canary", action="store_true", help="离线失效体检：加固是否还在/锚点失配/资源健康（不开浏览器）")
    args = ap.parse_args(argv)

    root = os.path.abspath(os.path.expanduser(args.path))
    if args.platform != "all" and args.platform not in PLATFORMS:
        sys.exit(_r(f"✗ 未知平台 {args.platform}。可选：{', '.join(PLATFORMS)} 或 all"))
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
            print(_b(f"\n━━━ {pname}({plat}) · 反爬强度:{level} ━━━"))
            do_check(files)
            continue
        if args.revert:
            print(_b(f"\n━━━ 还原 {pname}({plat}) ━━━"))
            do_revert(files, root)
            continue
        print(_b(f"\n━━━ 加固 {pname}({plat}) · 反爬强度:{level} ━━━"))
        if args.dry_run:
            print(_y("（dry-run：以下改动不会真正落盘）"))
        patch_base_config(files["base_config"], args.dry_run)
        patch_cdp_browser(files["cdp"], args.dry_run)
        patch_core(files["core"], args.dry_run, plat)
        ensure_stealth_js(files["stealth"], args.dry_run)
        deploy_modules(root, args.dry_run)
        if level in ("极高", "高") and not args.dry_run:
            print(_y(f"  ⚠ {pname} 反爬{level}：建议把 CRAWLER_MAX_SLEEP_SEC 再调大、量更小"))

    print(_b("\n═══ 完成 ═══"))
    print("  体检： python apply_hardening.py <path> -p all --check")
    print("  还原： python apply_hardening.py <path> -p <平台> --revert")
    if not args.dry_run and not args.check and not args.revert:
        print(_y("  ⚠ 务必先用小号试跑，主号永不碰爬虫"))


if __name__ == "__main__":
    main()
