# -*- coding: utf-8 -*-
"""
mirage_loop.py — Mirage 终极版「拟人刷号」主循环。

不是"狂点循环"，是模拟真人刷小红书：**大量浏览 + 少量克制互动 + 自然停顿**。
让整个 session 的行为分布像真人，而非高频点击——这才是真正的 0 封控之道。

⚠️ 默认 dry-run（只演示不真点）。每轮先做风控熔断检查。只用小号。AI 绝不自己实跑。

编排：human_behavior(浏览) + human_interaction(互动) + interaction_policy(配额)。
"""

import asyncio
import random
import time

try:
    from human_behavior import human_sleep, simulate_page_activity, warmup
    from human_interaction import XhsInteractor
    from interaction_policy import Policy
except ImportError:
    try:
        from tools.human_behavior import human_sleep, simulate_page_activity, warmup
        from tools.human_interaction import XhsInteractor
        from tools.interaction_policy import Policy
    except ImportError:                           # pip 安装后的 mirage 包语境
        from mirage.human_behavior import human_sleep, simulate_page_activity, warmup
        from mirage.human_interaction import XhsInteractor
        from mirage.interaction_policy import Policy

try:
    from _logging import get_logger  # 库模块日志（别裸 print）
except ImportError:                               # 部署/包语境兜底：退化成标准库 logger
    import logging as _logging_mod

    def get_logger(name: str = "mirage.loop"):
        _logging_mod.basicConfig(level=_logging_mod.INFO,
                                 format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        return _logging_mod.getLogger(name)

log = get_logger("mirage.loop")

# 风控信号：用**完整短语**（笔记正文几乎不会出现），优先在弹窗里查，大幅降低误判。
# 反例：单个"验证码"三字可能出现在笔记正文里 → 会误熔断，所以不用单词。
DANGER_PHRASES = ["操作过于频繁", "操作太频繁", "频繁操作请", "完成安全验证",
                  "账号存在异常", "账号出现异常", "系统检测到异常", "请完成验证",
                  "拖动滑块", "滑动验证", "你的账号已被", "账号已被封", "请重新登录"]
DANGER_DIALOG_SEL = ["[role=dialog]", ".reds-dialog", ".verify-dialog",
                     ".captcha-container", "[class*=captcha]", "[class*=verify]"]


class MirageLoop:
    def __init__(self, page, dry_run=True, interact_prob=0.15,
                 conservative=False, max_minutes=30,
                 platform_tz="Asia/Shanghai"):
        """
        platform_tz — 目标平台所在时区（IANA 名称），透传给 Policy。
            海外操作国内平台时填 "Asia/Shanghai"（看的是平台活跃时段不是操作者本地时间）。
        """
        self.page = page
        self.policy = Policy(conservative=conservative, platform_tz=platform_tz)
        self.actor = XhsInteractor(page, policy=self.policy, dry_run=dry_run)
        self.interact_prob = interact_prob          # 看到一条笔记→互动的概率（多数只看）
        self.max_seconds = max_minutes * 60
        self.dry_run = dry_run

    async def _danger(self):
        """检测风控信号。先看弹窗(最准)，再退到整页完整短语匹配。熔断优先级最高。"""
        # 1) 风控弹窗 / 验证遮罩——最可靠的信号
        try:
            for sel in DANGER_DIALOG_SEL:
                d = self.page.locator(sel).first
                if await d.count() and await d.is_visible():
                    txt = (await d.inner_text())[:1000]
                    if any(p in txt for p in DANGER_PHRASES) or "验证" in txt or "安全" in txt:
                        return True
        except Exception:
            pass
        # 2) 整页只匹配**完整短语**（单个"验证码"二字不算，避免笔记正文误判）
        try:
            body = (await self.page.inner_text("body"))[:5000]
            return any(p in body for p in DANGER_PHRASES)
        except Exception:
            return False

    async def _visible_cards(self):
        """识别当前可视区的笔记卡片（多重 fallback，用当前平台的选择器）。"""
        for sel in self.actor._selectors.get("note_card", []):
            try:
                loc = self.page.locator(sel)
                n = await loc.count()
                if n:
                    return [loc.nth(i) for i in range(min(n, 12))]
            except Exception:
                continue
        return []

    async def _decide_and_act(self, card):
        """对一条笔记：多数只看；点进去看的也不一定互动（真人看完常划走）。"""
        # 一段决策：受本轮"心情"调制的互动倾向，绝大多数只是滑过
        if random.random() > self.interact_prob * getattr(self, "_mood", 1.0):
            return False
        # 点进详情，阅读停留（长尾：多数 2.5~6s，偶尔看很久 8~20s）
        try:
            await self.actor._human_click(card, "笔记卡片")
            dwell = random.uniform(2.5, 6.0) if random.random() > 0.2 else random.uniform(8.0, 20.0)
            await asyncio.sleep(dwell)
        except Exception:
            pass
        acted = False
        # 二段决策："真看够才赞"——看完只有约 45% 觉得值得互动，
        # 把有限的每日配额留给真正想互动的优质内容（精准 > 频率）
        if random.random() < 0.45:
            roll = random.random()
            if roll < 0.70:
                acted = await self.actor.like_note()      # 点赞占多数
            elif roll < 0.90:
                acted = await self.actor.collect_note()
            else:
                acted = await self.actor.follow_user()    # 关注最敏感 → 最少
        # 看完返回信息流
        try:
            await self.page.go_back()
            await human_sleep(1.0, 0.6, 1.4)
        except Exception:
            pass
        return acted

    async def run(self):
        log.info(f"=== Mirage 刷号循环启动 ({'DRY-RUN 演示' if self.dry_run else '真实互动'}) ===")
        if not self.dry_run:
            log.warning("真实互动模式：会真的给人点赞/关注。确认用的是小号！")
        await warmup()
        start = time.time()
        rounds = 0
        while True:
            # —— 熔断：最高优先级 ——
            if await self._danger():
                log.warning("检测到风控信号（验证码/限流/异常），立即停止")
                break
            if self.policy.exhausted():
                log.info("今日互动预算全部用尽，收工")
                break
            if time.time() - start > self.max_seconds:
                log.info("到达运行时长上限，收工")
                break

            # —— 时段感知：深夜直接歇 ——
            slot_mult = self.policy.interact_prob_multiplier()
            if slot_mult == 0.0:
                # 深夜（平台时间 2~6 点），真人极少，暂停一段再检查
                slot = self.policy.current_slot()
                log.info(f"当前平台时段【{slot}】，不适合互动，暂停 600s 后再检查")
                await asyncio.sleep(600)   # 10 分钟后重新判断时段
                continue

            # —— 浏览：滚动 + 贝塞尔鼠标 + 阅读停留 ——
            await simulate_page_activity(self.page)

            # 本轮"心情"：兴趣有起伏，互动概率随轮波动（真人不是恒定 15%）
            # 同时叠加时段系数：夜间/平稳期降低互动意愿
            self._mood = random.uniform(0.5, 1.6) * slot_mult

            # —— 处理随机 2~4 条笔记；每条都**重新识别**(避免 go_back 后旧引用失效) ——
            for _ in range(random.randint(2, 4)):
                if await self._danger():
                    break
                cards = await self._visible_cards()
                if not cards:
                    break
                await self._decide_and_act(random.choice(cards))  # 随机选，不按固定序
                await human_sleep(4.0, 0.7, 1.6)    # 互动/浏览之间的自然间隔

            rounds += 1
            log.info(f"第 {rounds} 轮完成 | 时段[{self.policy.current_slot()}×{slot_mult:.1f}] | 今日 {self.policy.summary()}")
            await human_sleep(6.0, 0.7, 1.5)        # 轮间停顿

            # —— 偶尔"走神"长停（真人会分心去做别的）——
            if random.random() < 0.15:
                pause = random.uniform(20, 90)
                log.debug(f"走神 {pause:.0f}s")
                await asyncio.sleep(pause)

        log.info(f"=== 结束：共 {rounds} 轮，今日 {self.policy.summary()} ===")
