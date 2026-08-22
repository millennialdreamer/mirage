# -*- coding: utf-8 -*-
"""
行为层核心不变量回归测试。

这些断言守的是"拟人"这一核心卖点的**统计学与逻辑正确性**——它们都曾是真实 bug：
  - 贝塞尔曾用均匀 t 采样 → 全程近似匀速（运动学上最典型的机器人特征）
  - 时间间隔曾全用 random.uniform → 直方图是平顶矩形，KS 检验一眼识破
  - 点赞校验曾恒返回 True → 没点上也报"已生效"还扣配额
  - 蜜罐命中曾被其它正常信号稀释成"正常"（与"确凿证据"的定性自相矛盾）
一旦有人改坏这些，这里必须红。
"""
import asyncio
import math
import os
import random
import statistics
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import human_behavior as hb  # noqa: E402
from device_profile import DeviceProfile  # noqa: E402
from soft_ban_radar import SoftBanRadar  # noqa: E402


# ── 鼠标轨迹：必须缓入缓出，不能匀速 ──────────────────────────
def test_bezier_is_eased_not_constant_speed():
    random.seed(42)
    pts, prev, dists = hb._bezier_path(0, 0, 1000, 0, 20), (0.0, 0.0), []
    for p in pts:
        dists.append(math.dist(prev, p))
        prev = p
    head = sum(dists[:4]) / 4
    mid = sum(dists[8:12]) / 4
    tail = sum(dists[-4:]) / 4
    assert mid > head * 1.5, f"中段应显著快于起步(缓入)：起步{head:.1f} 中段{mid:.1f}"
    assert mid > tail * 1.5, f"中段应显著快于收尾(缓出)：收尾{tail:.1f} 中段{mid:.1f}"


# ── 时间分布：必须右偏，不能是平顶矩形 ────────────────────────
def _skew(xs):
    m, sd = statistics.mean(xs), statistics.pstdev(xs)
    return sum(((x - m) / sd) ** 3 for x in xs) / len(xs)


def test_delay_distribution_is_right_skewed():
    random.seed(1)
    samples = [hb.human_delay(6.0) for _ in range(8000)]
    assert _skew(samples) > 0.5, "时间间隔必须右偏(真人形态)，不能退回均匀分布"
    assert 5.4 < statistics.median(samples) < 6.6, "中位数应锚在 base 附近"


# ── 软封杀雷达 ────────────────────────────────────────────
def _radar(account):
    return SoftBanRadar(state_path=os.path.join(tempfile.mkdtemp(), "r.json"), account=account)


def test_radar_refuses_to_guess_on_small_sample():
    r = _radar("few")
    for _ in range(5):
        r.observe(ok=True, latency=1.0, completeness=1.0)
    assert r.assess().level == "数据不足", "样本不足时必须明说数据不足，不许瞎猜"


def test_radar_no_false_alarm_on_healthy_stream():
    r = _radar("ok")
    for _ in range(40):
        r.observe(ok=True, latency=1.0, completeness=1.0)
    assert r.assess().level == "正常", "健康流不能误报"


def test_radar_detects_degradation():
    r = _radar("bad")
    for _ in range(40):
        r.observe(ok=True, latency=1.0, completeness=1.0)
    for i in range(20):
        r.observe(ok=(i % 3 != 0), latency=2.8, completeness=0.7, captcha=(i % 5 == 0))
    v = r.assess()
    assert v.level in ("警戒", "危险") and v.should_slow_down()


def test_radar_detects_silent_shrink_alone():
    """只有"返回静默缩水"这一个最隐蔽的降权信号时，也必须能察觉。"""
    r = _radar("shrink")
    for _ in range(40):
        r.observe(ok=True, latency=1.0, completeness=1.0)
    for _ in range(20):
        r.observe(ok=True, latency=1.0, completeness=0.68)
    assert r.assess().level != "正常", "静默缩水是软封杀最典型表现，不能漏"


def test_radar_honeypot_is_conclusive_not_diluted():
    """蜜罐命中在文档里被定性为"确凿证据"，就不能被其它正常信号稀释成"正常"。"""
    r = _radar("hp")
    for _ in range(30):
        r.observe(ok=True, latency=1.0, completeness=1.0)
    r.observe(ok=True, latency=1.0, completeness=1.0, honeypot=True)
    v = r.assess()
    assert v.level in ("警戒", "危险"), "蜜罐是确凿证据，必须≥警戒"


def test_radar_accounts_are_isolated():
    path = os.path.join(tempfile.mkdtemp(), "multi.json")
    a = SoftBanRadar(state_path=path, account="A")
    b = SoftBanRadar(state_path=path, account="B")
    for _ in range(20):
        a.observe(ok=False, captcha=True)
    assert b.assess().samples == 0, "账号基线必须互相隔离"


# ── 设备画像 ──────────────────────────────────────────────
def test_profile_is_deterministic_and_unique():
    assert DeviceProfile.from_seed("s1").to_dict() == DeviceProfile.from_seed("s1").to_dict()
    assert DeviceProfile.from_seed("s1").noise_seed != DeviceProfile.from_seed("s2").noise_seed


def test_generated_profiles_are_always_self_consistent():
    """生成器绝不能产出自相矛盾的画像——局部真整体假比不改更危险。"""
    for i in range(120):
        p = DeviceProfile.from_seed(f"seed-{i}")
        assert not p.check(), f"seed-{i} 产出了矛盾画像：{p.check()}"


def test_consistency_checker_catches_contradictions():
    base = DeviceProfile.from_seed("seed-0").to_dict()
    win = next(DeviceProfile.from_seed(f"s{i}") for i in range(50)
               if "Windows" in DeviceProfile.from_seed(f"s{i}").os)
    for override in ({"webgl_renderer": "ANGLE (Apple, Apple M2, Metal)"},
                     {"platform": "MacIntel"}, {"languages": []}, {"cores": 128}):
        broken = DeviceProfile(**{**win.to_dict(), **override})
        assert broken.check(), f"校验器漏掉了矛盾：{override}"
    assert base  # 保留引用，避免 lint 误报


def test_init_script_covers_all_canvas_exits():
    js = DeviceProfile.from_seed("js").to_init_script()
    for must in ("getImageData", "toDataURL", "toBlob", "getParameter", "hardwareConcurrency"):
        assert must in js, f"注入脚本缺少 {must}（canvas 三出口只拦一个会被对拍抓出）"


# ── 验证码钩子：安全默认不可退化 ───────────────────────────
class _FakePage:
    class _M:
        async def move(self, *a, **k): pass
        async def wheel(self, *a): pass
    mouse = _M()


def _loop(on_captcha=None, dry_run=False, danger_after=True):
    from mirage_loop import MirageLoop

    async def _ret(v):
        return v
    lp = MirageLoop(_FakePage(), dry_run=dry_run, on_captcha=on_captcha)
    lp.radar = None
    lp._danger = lambda: _ret(danger_after)
    return lp


def test_captcha_hook_safe_defaults():
    assert asyncio.run(_loop(None)._handle_captcha()) is False, "无回调必须维持停手"
    assert asyncio.run(_loop(lambda p: False)._handle_captcha()) is False

    def boom(p):
        raise RuntimeError("打码服务挂了")
    assert asyncio.run(_loop(boom)._handle_captcha()) is False, "回调抛错不能拖垮主循环"


def test_captcha_hook_not_triggered_in_dry_run():
    calls = []
    lp = _loop(lambda p: calls.append(1) or True, dry_run=True)
    assert asyncio.run(lp._handle_captcha()) is False and not calls


def test_captcha_hook_does_not_trust_callback_blindly():
    """回调声称已解决，但复检风控信号仍在 → 仍然停手。"""
    assert asyncio.run(_loop(lambda p: True, danger_after=True)._handle_captcha()) is False


def test_captcha_hook_resumes_only_when_signal_cleared():
    assert asyncio.run(_loop(lambda p: True, danger_after=False)._handle_captcha()) is True
