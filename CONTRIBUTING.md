# Contributing

## Before anything else

This project is for **technical learning and research**. Commercial use and large-scale data
collection are out of bounds. Legal exposure and platform bans are the user's own risk; the author
is not responsible for misuse.

## Ground rules

1. **Throwaway accounts only.** Any change touching real interaction (like / follow / comment) must be
   verified on a disposable account. Never a primary account. Ever.
2. **No signature reversing, no captcha solving.** Mirage's boundary is *human-like behavior*. It does
   not reverse signing algorithms and does not defeat human verification. PRs crossing that line will
   be declined regardless of quality.
3. **Don't break the honesty.** This project deliberately documents its own ceilings (see "Honest
   limits" in the README). PRs that replace a candid limitation with marketing language will be
   declined. If you genuinely improve a capability, update the corresponding limit — don't just delete it.
4. **Patching third-party source is sacred.** Changes to `apply_hardening.py` must stay idempotent,
   keep the atomic-write → AST-validate → rollback path intact, and preserve the `[xhs-stealth]` marker
   and `.xhs-stealth.bak` suffix — deployed installs depend on those for `--check` / `--revert`.
   Run `--dry-run` twice before submitting.
5. **Some Chinese literals are data — do not translate them.** The source and docs are English, but a
   handful of strings are the exact bytes the target platforms emit: the risk-control phrases in
   `DANGER_PHRASES`, the CJK `aria-label` / button text in `SELECTORS`, the error strings in
   `_NOT_RETRYABLE_PATTERNS`. They look like an unfinished translation; they are not. Translating them
   fails *silently* — the circuit breaker stops matching, selectors match nothing, hard failures get
   retried — which is why `tests/test_i18n_guards.py` enforces it instead of a code comment. If you add
   a genuinely new literal, raise its budget in that test and say why.
6. **Run the suite.** `bash scripts/ci.sh` must be green (pytest + ruff + mypy); CI runs the same checks
   on Python 3.9/3.11/3.13 plus a full apply → check → revert lifecycle against a fixture install.
   Behavioral changes need a regression test in `tests/test_behaviors.py`; every assertion in there maps
   to a real bug that was found and fixed.
7. **Check `docs/` before opening an issue.** Platform differences and install problems are documented.

## Development

```bash
pip install -e ".[browser]"
bash scripts/ci.sh
git config core.hooksPath .githooks    # run CI automatically before every push
```

Anything that launches a browser (`verify_stealth.py`, `fingerprint_benchmark.py --detect-url/--botd`)
is run manually by a human — never automatically in tests.
