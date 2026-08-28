# -*- coding: utf-8 -*-
"""
i18n guards — the source is English, but a handful of strings are **data, not prose**.

Mirage targets Chinese-language platforms. A few literals in this codebase are the exact
bytes those platforms emit: risk-control dialog wording, aria-labels, API error messages.
They read like leftovers from an incomplete translation, so sooner or later someone
(human or model) will "finish the job" and translate them.

That failure is silent and expensive:

  - Translate DANGER_PHRASES  -> the circuit breaker never matches again, and the loop
                                 keeps interacting all the way into a ban.
  - Translate SELECTORS       -> every selector matches nothing; the interactor reports
                                 "button not found" forever and looks merely broken.
  - Translate error patterns  -> non-retryable failures get retried, hammering a platform
                                 that has already said no.

None of those break a normal test run, which is exactly why they need a test of their own.
The in-code DO-NOT-TRANSLATE comments state the rule; this file enforces it.
"""
import os
import re
import sys

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


def _src(name):
    with open(os.path.join(SCRIPTS, name), encoding="utf-8") as f:
        return f.read()


def test_danger_phrases_stay_chinese():
    """Risk-control circuit breaker: phrases must stay as the platforms render them."""
    import mirage_loop

    required = ["操作过于频繁", "完成安全验证", "拖动滑块", "请重新登录", "账号已被封"]
    missing = [p for p in required if p not in mirage_loop.DANGER_PHRASES]
    assert not missing, (
        f"DANGER_PHRASES lost its Chinese literals: {missing}. These are the exact strings "
        "the platforms show in risk-control dialogs — translating them silently disables "
        "the circuit breaker. See the DO-NOT-TRANSLATE note in scripts/mirage_loop.py."
    )
    # Every phrase must be a full sentence fragment, not a single word: bare words like
    # "验证" occur in ordinary note text and would trip the breaker on false positives.
    too_short = [p for p in mirage_loop.DANGER_PHRASES if len(p) < 4]
    assert not too_short, f"DANGER_PHRASES entries too short (false-positive risk): {too_short}"


def test_selectors_stay_chinese():
    """Interaction selectors: aria-label / button text on Chinese-language sites.

    Checked per platform *and* per element, deliberately. A flat "is 赞 anywhere in
    SELECTORS" check passes even after Xiaohongshu's like selector is translated, because
    the character also appears in Douyin's 点赞 — so the loose version of this test waves
    through exactly the regression it exists to catch.
    """
    import human_interaction

    # platform -> element -> one CJK substring at least one of its selectors must contain
    required = {
        "xhs": {"like": "赞", "collect": "收藏", "follow": "关注", "comment_box": "评论"},
        "dy": {"like": "赞", "follow": "关注", "comment_box": "评论"},
        "bili": {"like": "赞", "follow": "关注", "comment_box": "评论"},
    }
    missing = []
    for plat, elements in required.items():
        sels = human_interaction.SELECTORS.get(plat)
        assert sels, f"SELECTORS lost the whole {plat!r} platform"
        for key, needle in elements.items():
            candidates = sels.get(key, [])
            if not any(needle in s for s in candidates):
                missing.append(f"{plat}.{key} (no selector containing {needle!r}): {candidates}")
    assert not missing, (
        "SELECTORS lost its Chinese literals:\n  " + "\n  ".join(missing) +
        "\nThese are the rendered aria-label and button text on the target sites — a "
        "translated selector matches nothing and the interactor just reports "
        "'button not found' forever. See the DO-NOT-TRANSLATE note in "
        "scripts/human_interaction.py."
    )


def test_non_retryable_patterns_stay_chinese():
    """Error classification: literal API error strings decide retry vs. give up."""
    import network_resilience

    pats = network_resilience._NOT_RETRYABLE_PATTERNS
    missing = [s for s in ("验证码", "账号异常") if s not in pats]
    assert not missing, (
        f"_NOT_RETRYABLE_PATTERNS lost its Chinese literals: {missing}. Translating them "
        "makes hard failures look retryable, so the client hammers a platform that already "
        "said no."
    )


def test_patch_markers_are_stable():
    """Patch markers are a wire format: deployed installs are matched against these bytes."""
    import apply_hardening

    assert apply_hardening.MARK == "[xhs-stealth]", (
        f"MARK changed to {apply_hardening.MARK!r}. Idempotency checks and `mirage canary` on "
        "already-deployed installs match this literal; changing it makes existing hardening "
        "invisible and re-patches on top of itself."
    )
    assert apply_hardening.BAK_SUFFIX == ".xhs-stealth.bak", (
        f"BAK_SUFFIX changed to {apply_hardening.BAK_SUFFIX!r}. --revert locates backups by "
        "this suffix; changing it strands every backup already on disk."
    )


def test_l5_injected_symbol_is_stable():
    """The injected helper name is matched by --check/--canary on deployed installs."""
    src = _src("apply_hardening.py")
    assert "_xhs_stealth_human_activity" in src, (
        "The L5 injected method name changed. do_check/do_canary grep deployed sources for "
        "this exact symbol; renaming it reports healthy installs as unhardened."
    )


def test_radar_levels_match_their_consumers():
    """Level strings are compared, not just printed — definition and consumers must agree.

    This is the bug that actually happened twice during the English conversion: the level
    strings were translated while the `in (...)` guards reading them were not, so automatic
    slowdown silently stopped firing while every test stayed green.
    """
    from soft_ban_radar import Verdict

    for level, slow, stop in [
        ("normal", False, False),
        ("watch", True, False),
        ("warning", True, False),
        ("danger", True, True),
        ("insufficient data", False, False),
    ]:
        v = Verdict(level=level, score=0, advice="")
        assert v.should_slow_down() is slow, f"level {level!r}: should_slow_down != {slow}"
        assert v.should_stop() is stop, f"level {level!r}: should_stop != {stop}"

    # The CLI prints an icon per level; a level with no icon means the two drifted apart.
    cli = _src("cli.py")
    icons = re.search(r'icon = \{(.*?)\}\.get', cli, re.S)
    assert icons, "could not find the radar icon map in cli.py"
    for level in ("normal", "watch", "warning", "danger", "insufficient data"):
        assert f'"{level}"' in icons.group(1), (
            f"cli.py has no icon for radar level {level!r} — the level strings and the CLI "
            "have drifted apart."
        )


def test_prose_is_english():
    """Comments and docstrings are English; only the guarded data literals above may be CJK."""
    allowed = {
        "mirage_loop.py": 4,          # DANGER_PHRASES (3 lines) + the 验证/安全 dialog check
        "human_interaction.py": 20,   # SELECTORS
        "network_resilience.py": 1,   # _NOT_RETRYABLE_PATTERNS
    }
    cjk = re.compile(r"[一-鿿]")
    offenders = {}
    for fn in sorted(os.listdir(SCRIPTS)):
        if not fn.endswith(".py"):
            continue
        n = sum(1 for line in _src(fn).splitlines() if cjk.search(line))
        if n > allowed.get(fn, 0):
            offenders[fn] = f"{n} CJK lines (allowed {allowed.get(fn, 0)})"
    assert not offenders, (
        f"Chinese prose reappeared in: {offenders}. The source is English; if you added a "
        "genuinely new data literal, raise its budget in this test and explain why."
    )


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except AssertionError as e:
                print(f"  FAIL  {name}: {e}")
                failed += 1
    print("=" * 40)
    print(f"i18n guards: {'all passed' if not failed else f'{failed} FAILED'}")
    sys.exit(1 if failed else 0)
