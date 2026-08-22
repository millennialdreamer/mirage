# -*- coding: utf-8 -*-
"""
human_behavior.py — 可复用的"人类行为模拟"工具（贝塞尔鼠标 + 拟人节奏）。

apply_hardening.py 注入进 core.py 的 L5 方法会**直接调用本模块**（单一真相源），
所以改进这里，注入版自动受益。也可手动集成：

    from tools.human_behavior import human_sleep, warmup, simulate_page_activity

    await warmup()                       # 打开页面后先停几秒
    ...
    await simulate_page_activity(page)   # 翻页间隔：贝塞尔移动鼠标 + 滚动 + 阅读停留
    await human_sleep(config.CRAWLER_MAX_SLEEP_SEC)   # 带抖动 + 偶发长停顿的睡眠

设计原则（综合反爬专家评审）：
  - 鼠标**绝不瞬移**。瞬移=直线零轨迹+无限速度，比"不动"更像机器人。
    一律走贝塞尔曲线、分步插值、每步加微噪声、匀加速→匀减速。
  - 时间间隔不只是均匀随机，而是"大多数短 + 偶尔长停顿"，贴近真人对数正态分布。
  - 任何异常都吞掉，绝不打断爬取主流程。
"""

import asyncio
import random


def _bezier_path(x0, y0, x1, y1, steps):
    """生成从 (x0,y0) 到 (x1,y1) 的三次贝塞尔路径点（两个随机控制点 → 自然弧线）。"""
    dx, dy = x1 - x0, y1 - y0
    cx1 = x0 + dx * random.uniform(0.2, 0.4) + random.uniform(-40, 40)
    cy1 = y0 + dy * random.uniform(0.2, 0.4) + random.uniform(-40, 40)
    cx2 = x0 + dx * random.uniform(0.6, 0.8) + random.uniform(-40, 40)
    cy2 = y0 + dy * random.uniform(0.6, 0.8) + random.uniform(-40, 40)
    pts = []
    for i in range(1, steps + 1):
        # 缓入缓出（smoothstep）：把均匀的 i/steps 重映射成"起步慢 → 中段快 → 到点前减速"。
        # ⚠️ 直接用均匀 t 会让整条轨迹近似匀速、端点速度不为零——这是运动学上最典型的
        # 机器人特征（真人受费茨定律支配：加速接近、临近目标显著减速）。做行为建模的风控
        # （reCAPTCHA v3 / 瑞数等）正是查这条速度曲线，所以这一行是拟人轨迹的关键。
        _u = i / steps
        t = _u * _u * (3 - 2 * _u)
        mt = 1 - t
        bx = mt**3 * x0 + 3 * mt**2 * t * cx1 + 3 * mt * t**2 * cx2 + t**3 * x1
        by = mt**3 * y0 + 3 * mt**2 * t * cy1 + 3 * mt * t**2 * cy2 + t**3 * y1
        pts.append((bx, by))
    return pts


async def human_mouse_move(page, x, y, start=(None, None), steps=None):
    """沿贝塞尔曲线把鼠标从 start 移到 (x,y)，分步 + 微噪声 + 步间随机延迟。

    start 缺省时用一个随机起点（首次移动）。返回终点，便于链式调用维护上次位置。
    """
    x0, y0 = start
    if x0 is None:
        x0, y0 = random.randint(100, 1000), random.randint(100, 600)
    steps = steps or random.randint(8, 16)
    for bx, by in _bezier_path(x0, y0, x, y, steps):
        await page.mouse.move(bx + random.uniform(-1.5, 1.5),
                              by + random.uniform(-1.5, 1.5))
        # 步间隔也走右偏分布：真人手速有快有慢、偶有微顿，均匀步时同样是可统计的破绽
        await asyncio.sleep(human_delay(0.019, sigma=0.35, lo=0.5, hi=2.6))
    return (x, y)


def human_delay(base_sec: float, sigma: float = 0.45,
                lo: float = 0.55, hi: float = 3.5) -> float:
    """返回一个**右偏（对数正态）**的时长：中位数 = base_sec，多数略短、偶尔明显长。

    为什么不用 random.uniform：真人的时间间隔天然右偏（大量短间隔 + 少量长尾），
    而均匀分布的直方图是**平顶矩形**——这在统计上一眼假，KS 检验能直接把它和人类区分开。
    以前这里用"85% 短均匀 + 15% 长均匀"近似，直方图是两个矩形，仍可被检出；
    现在直接采样对数正态，形状是真的平滑右偏曲线。

    lo/hi 是相对 base 的软钳位（防极端值），不改变主体形状。
    """
    d = base_sec * random.lognormvariate(0, sigma)
    return max(base_sec * lo, min(base_sec * hi, d))


async def human_sleep(base_sec: float, lo: float = 0.7, hi: float = 1.6) -> None:
    """带右偏抖动的睡眠（对数正态）。lo/hi 为软钳位边界，长尾可超过 hi。

    例：base=6 → 中位 6s，多数 4~9s，偶尔十几秒（真人分心/阅读）。
    """
    await asyncio.sleep(human_delay(base_sec, sigma=0.45, lo=lo * 0.8, hi=hi * 2.2))


async def warmup(min_sec: float = 3.0, max_sec: float = 8.0) -> None:
    """首次动作前的"热身停顿"。真人打开页面会先看几秒，机器人会立刻开搜。"""
    mid = (min_sec + max_sec) / 2                    # 以区间中点为中位数，右偏采样
    await asyncio.sleep(human_delay(mid, sigma=0.40,
                                    lo=min_sec / mid, hi=max_sec * 1.8 / mid))


async def simulate_page_activity(page) -> None:
    """翻页间隔的拟人行为：贝塞尔移动鼠标到 2~4 个点 + 滚动 + 阅读停留 + 偶尔回滚。

    填补"睡眠期页面完全静止"这一强机器人信号，且鼠标走自然弧线而非瞬移。
    任何异常都吞掉，绝不影响主爬取流程。
    """
    try:
        last = (None, None)
        # 向下滚动，像在浏览结果列表
        await page.mouse.wheel(0, random.randint(300, 700))
        await asyncio.sleep(random.uniform(0.4, 1.0))

        # 贝塞尔移动到 2~4 个随机位置（自然弧线，维护上次位置做链式）
        for _ in range(random.randint(2, 4)):
            tx, ty = random.randint(150, 1200), random.randint(120, 700)
            last = await human_mouse_move(page, tx, ty, start=last)
            await asyncio.sleep(random.uniform(0.15, 0.5))

        # 阅读停留：滚到一批内容后停一会（真人在看）
        await asyncio.sleep(random.uniform(0.8, 2.2))

        # 约 40% 概率往回滚一点（自然回看）
        if random.random() < 0.4:
            await page.mouse.wheel(0, -random.randint(80, 250))
            await asyncio.sleep(random.uniform(0.2, 0.6))
    except Exception:
        pass


async def human_hover(page, selector: str) -> None:
    """可选增强：悬停在某个元素上（不点击、不导航，安全）。

    风控看重"悬停→犹豫"的决策链。hover 不会触发跳转，比 click 安全，
    适合手动集成时调用（如悬停在笔记卡片标题上）。selector 由调用方按页面结构提供。
    """
    try:
        await page.hover(selector, timeout=3000)
        await asyncio.sleep(random.uniform(0.3, 1.2))
    except Exception:
        pass
