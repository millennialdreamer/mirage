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
5. **Run the suite.** `bash scripts/ci.sh` must be green (pytest + ruff + mypy). Behavioral changes need
   a regression test in `tests/test_behaviors.py`; every assertion in there maps to a real bug that was
   found and fixed.
6. **Check `docs/` before opening an issue.** Platform differences and install problems are documented.

## Development

```bash
pip install -e ".[browser]"
bash scripts/ci.sh
git config core.hooksPath .githooks    # run CI automatically before every push
```

Anything that launches a browser (`verify_stealth.py`, `fingerprint_benchmark.py --detect-url/--botd`)
is run manually by a human — never automatically in tests.
