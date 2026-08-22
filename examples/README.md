# examples/ Usage Examples

## File description

| File | Description |
|------|------|
| `harden_all.sh` | Demonstrates common invocations of `apply_hardening.py` (Mac/Linux) |

## Quick start

### Step 1: Verify MediaCrawler is installed

```bash
ls /path/to/MediaCrawler/config/base_config.py  # should exist
```

### Step 2: Preview changes with dry-run

```bash
python scripts/apply_hardening.py /path/to/MediaCrawler --dry-run
```

### Step 3: Apply patches

```bash
python scripts/apply_hardening.py /path/to/MediaCrawler
```

### Equivalent commands for Windows users

Run each `python scripts/apply_hardening.py ...` line from `harden_all.sh` as-is in PowerShell or CMD; paths can use either forward slashes or backslashes.

## More information

- Cross-platform differences: see `docs/cross-platform.md`
- Five-layer hardening principles: see `docs/anti-detection.md`
- Interaction engine usage: see `SKILL.md`