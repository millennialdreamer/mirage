## Change Description

<!-- What was changed and why -->

## Self-Check Checklist
- [ ] `bash scripts/ci.sh` is fully green (pytest + ruff + mypy + benchmark self-check)
- [ ] Did not touch feature markers `[xhs-stealth]` / backup suffix `.xhs-stealth.bak` (changing them would break `--check`/`--revert` in already deployed environments)
- [ ] If third-party source code is rewritten, used `write_py_safe` (atomic write + AST validation + rollback on failure)
- [ ] If adding a script that launches a browser, keep the iron rule of "let users run it manually; AI/CLI must not run it on their behalf"
- [ ] Be honest about boundaries: do not promise "100% undetectable" (see `docs/`)

> Compliance: for study and research only; do not add capabilities such as breaking CAPTCHAs / main-account volume farming.