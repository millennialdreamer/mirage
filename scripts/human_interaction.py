# -*- coding: utf-8 -*-
"""
human_interaction.py — Mirage 互动引擎：在各平台页面上"像真人一样"识别并点击
（点赞 / 关注 / 收藏 / 评论）。目前深度验证平台：小红书(xhs)。
其余平台(dy/bili等)选择器为语义化合理猜测，**需按实际页面核对调整**。

⚠️ 三条安全铁律（写进代码，不靠自觉）：
  1. **dry_run 默认 True** —— 默认只把鼠标贝塞尔移动到位、打印将做什么，但**不真点**。
     只有显式 `XhsInteractor(page, dry_run=False)` 才会真正互动。
  2. 每个动作先问 `policy.can(action)` —— 超每日上限/未过冷却就跳过。
  3. 互动有**真实对外后果**（真给陌生人点赞/关注/评论），**只用小号**，AI 绝不自己实跑。

设计：识别层(多重 fallback 选择器) → 就绪检查 → 贝塞尔移动+hover+真实 click → 验证生效。
鼠标轨迹复用 human_behavior 的贝塞尔（绝不瞬移）。
"""

import asyncio
import random

try:                                              # scripts/ 下直接跑
    from human_behavior import human_mouse_move, human_sleep
except ImportError:
    try:                                          # 部署到 MediaCrawler/tools/ 后
        from tools.human_behavior import human_mouse_move, human_sleep
    except ImportError:                           # pip 安装后的 mirage 包语境
        from mirage.human_behavior import human_mouse_move, human_sleep


# 多平台元素 fallback 选择器。结构：{平台: {元素: [选择器列表]}}
# 顺序 = 尝试顺序：稳定语义属性 → role/文本 → class 兜底。
# ⚠️ xhs 已在实际页面验证；dy / bili 为语义化合理猜测，**需按实际页面核对调整**。
SELECTORS = {
    # -----------------------------------------------------------------------
    # 小红书 (xhs) —— 已实际页面验证
    # -----------------------------------------------------------------------
    "xhs": {
        "note_card":    ["section.note-item", "a[href*='/explore/']", "[data-type='note']"],
        "like":         ["[aria-label*='赞']", "[aria-label*='like']",
                         "span.like-wrapper", ".interact-container .like-active, .interact-container .like"],
        "collect":      ["[aria-label*='收藏']", "span.collect-wrapper", ".collect"],
        "follow":       ["button:has-text('关注'):not(:has-text('已关注'))",
                         "[aria-label='关注']", ".follow-button:not(.followed)"],
        "comment_box":  ["[contenteditable='true']", "textarea[placeholder*='评论']",
                         "div.comment-input"],
        "comment_send": ["button:has-text('发送')", "button:has-text('发布')", ".submit"],
    },

    # -----------------------------------------------------------------------
    # 抖音 (dy) —— ⚠️ 语义化猜测，需按实际页面核对调整
    # 抖音网页版(douyin.com)DOM结构随版本更新频繁，以下为通用语义属性优先策略
    # -----------------------------------------------------------------------
    "dy": {
        "note_card":    ["[data-e2e='feed-active-video']", ".video-feed-item",
                         "[data-testid='video-item']"],
        "like":         # 点赞：aria-label 最稳定，其次 data-e2e，class 兜底
                        ["[aria-label*='点赞']", "[aria-label*='like']",
                         "[data-e2e='like-icon']", ".like-button",
                         "button:has-text('赞')"],  # ⚠️ 需核对
        "follow":       # 关注：text-content 最语义化，未关注状态排除"已关注"
                        ["button:has-text('关注'):not(:has-text('已关注'))",
                         "[data-e2e='follow-button']", "[aria-label='关注']",
                         ".follow-button:not(.disabled)"],  # ⚠️ 需核对
        "comment_box":  ["[data-e2e='comment-input']", "[contenteditable='true']",
                         "textarea[placeholder*='评论']", ".comment-input-inner"],
        "comment_send": ["button:has-text('发送')", "[data-e2e='comment-send']",
                         "button:has-text('发布')"],
    },

    # -----------------------------------------------------------------------
    # B站 (bili) —— ⚠️ 语义化猜测，需按实际页面核对调整
    # B站(bilibili.com)网页版 wbi 签名较简单，DOM 相对稳定但仍需核对
    # -----------------------------------------------------------------------
    "bili": {
        "note_card":    [".bili-video-card", ".video-card", "[data-report='click']"],
        "like":         # B站点赞在播放页工具栏，通常有 aria-label
                        ["[aria-label*='点赞']", "[aria-label*='like']",
                         ".video-like", ".like.on, .like",
                         "button.like-btn"],  # ⚠️ 需核对
        "follow":       # B站关注在UP主头像旁，未关注为"关注"按钮
                        ["button:has-text('关注'):not(:has-text('已关注'))",
                         ".follow-btn:not(.be-follow-btn--followed)",
                         "[aria-label='关注']", ".b-btn--follow"],  # ⚠️ 需核对
        "comment_box":  ["#comment-box", "textarea[placeholder*='发一条友善的评论']",
                         "[contenteditable='true']", ".comment-send input"],
        "comment_send": ["button:has-text('发布')", ".comment-submit",
                         "button:has-text('发送')"],
    },
}


class XhsInteractor:
    """多平台拟人互动器。持有一个 Playwright page。

    向后兼容：不传 platform 参数时默认 'xhs'，行为与旧版完全一致。

    参数：
        page:     Playwright Page 对象
        policy:   互动配额策略（可选）
        dry_run:  默认 True，只演示不真点；显式传 False 才真实互动
        platform: 平台代码，支持 'xhs'/'dy'/'bili'（默认 'xhs'）
    """

    def __init__(self, page, policy=None, dry_run=True, platform="xhs"):
        self.page = page
        self.policy = policy
        self.dry_run = dry_run          # 默认只演示不真点
        self.platform = platform        # 平台选择器分支
        self._mouse = (None, None)      # 维护上次鼠标位置，贝塞尔链式更连贯
        # 从嵌套 SELECTORS 中取对应平台，fallback 到 xhs
        self._selectors = SELECTORS.get(platform, SELECTORS["xhs"])

    # ---- 识别层：多重 fallback ----
    async def _resolve(self, key):
        """按当前平台 SELECTORS[key] 顺序找第一个可见元素，找不到返回 None。"""
        for sel in self._selectors.get(key, []):
            try:
                loc = self.page.locator(sel).first
                if await loc.count() and await loc.is_visible():
                    return loc
            except Exception:
                continue
        return None

    # ---- 就绪检查：滚动到视口 + 可见 + 未被遮挡 ----
    async def _ready(self, loc):
        try:
            await loc.scroll_into_view_if_needed(timeout=3000)
            await loc.wait_for(state="visible", timeout=3000)
            await loc.click(trial=True, timeout=1500)   # 无副作用试点；被遮挡会抛
            return True
        except Exception:
            return False

    # ---- 点击层：贝塞尔移动 → hover 犹豫 →（dry-run? 停手 : 真点）----
    async def _human_click(self, loc, label=""):
        box = await loc.bounding_box()
        if not box:
            return False
        tx = box["x"] + box["width"] / 2 + random.uniform(-3, 3)
        ty = box["y"] + box["height"] / 2 + random.uniform(-3, 3)
        # 贝塞尔曲线移动到目标（非瞬移），维护上次位置做链式
        self._mouse = await human_mouse_move(self.page, tx, ty, start=self._mouse)
        await asyncio.sleep(random.uniform(0.15, 0.5))   # 点前 hover 犹豫，像真人
        if self.dry_run:
            print(f"  [dry-run] 将点「{label}」@({tx:.0f},{ty:.0f})——已移动到位，不真点")
            return False
        # 真实合成点击（mousedown→停顿→mouseup）
        await self.page.mouse.down()
        await asyncio.sleep(random.uniform(0.05, 0.09))
        await self.page.mouse.up()
        return True

    async def _attr(self, loc, name):
        try:
            return await loc.get_attribute(name)
        except Exception:
            return None

    # 不同平台用不同属性表达"已赞/已收藏/已关注"：小红书多用 class（.like-active 之类）+
    # aria-label 文案变化，少数用 aria-pressed。只查单一属性会在拿不到时误判成"成功"。
    VERIFY_ATTRS = ("aria-pressed", "class", "aria-label", "aria-selected")

    async def _state_snapshot(self, loc):
        """对可能反映状态的多个属性取快照，用于点击前后对比。"""
        snap = {}
        for name in self.VERIFY_ATTRS:
            snap[name] = await self._attr(loc, name)
        return snap

    # ---- 动作层：每个都先过配额、再就绪、再拟人点、再验证 ----
    async def _do(self, key, label):
        if self.policy and not self.policy.can(key):
            print(f"  「{label}」已达上限或在冷却，跳过")
            return False
        loc = await self._resolve(key)
        if not loc:
            print(f"  没找到「{label}」按钮（选择器需按实际页面调，见 SELECTORS）")
            return False
        if not await self._ready(loc):
            print(f"  「{label}」不可点（被遮挡/不可见）")
            return False
        before = await self._state_snapshot(loc)
        clicked = await self._human_click(loc, label)
        if not clicked:                              # dry-run 或没点成
            return False
        await human_sleep(0.6, 0.5, 1.2)             # 点后自然短停
        after = await self._state_snapshot(loc)

        # 三态诚实判定（旧实现：单查 aria-pressed，小红书赞根本没这属性 → before=None
        # → 恒判"已生效"，没点上也报成功还扣配额，校验层形同虚设）。
        verifiable = any(v is not None for v in before.values())
        changed = any(before[k] != after[k] for k in before)
        if not verifiable:
            state = "已点击（该按钮无可校验属性，是否生效未知）"
        elif changed:
            state = "已生效"
        else:
            state = "未见状态变化（可能没点上）"

        # 配额：只要真实点击已派发就计数（宁可多算——少算会让实际互动超过配额上限，
        # 反而抬高封号风险；这与本工具"宁可慢"的立场一致）。
        if self.policy:
            self.policy.record(key)
        print(f"  {'✓' if changed else '·'} 「{label}」{state}")
        return clicked

    async def like_note(self):
        return await self._do("like", "点赞")

    async def collect_note(self):
        return await self._do("collect", "收藏")

    async def follow_user(self):
        return await self._do("follow", "关注")

    async def comment_note(self, text: str):
        """评论 —— 最敏感（内容风控：重复/广告词/带链接最易判违规）。逐字输入更像人。"""
        if self.policy and not self.policy.can("comment"):
            print("  「评论」已达上限或在冷却，跳过")
            return False
        box = await self._resolve("comment_box")
        if not box:
            print("  没找到评论框")
            return False
        if not await self._ready(box):
            return False
        await self._human_click(box, "评论框")
        if self.dry_run:
            print(f"  [dry-run] 将逐字输入评论：{text!r}（不真发）")
            return False
        await box.click()
        for ch in text:                              # 逐字 + 随机延迟，像真人打字
            await self.page.keyboard.type(ch)
            await asyncio.sleep(random.uniform(0.06, 0.22))
        await human_sleep(1.0, 0.6, 1.5)             # 发前停顿（像在检查）
        send = await self._resolve("comment_send")
        if send and await self._human_click(send, "发送评论"):
            if self.policy:
                self.policy.record("comment")
            print("  ✓ 评论已发")
            return True
        return False
