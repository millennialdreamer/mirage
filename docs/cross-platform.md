# Cross-Platform Usage Guide

## Script Compatibility Overview

| Script | Windows | macOS | Linux |
|------|---------|-------|-------|
| `apply_hardening.py` | ✅ | ✅ | ✅ |
| `verify_stealth.py` | ✅ | ✅ | ✅ |
| `human_interaction.py` | ✅ | ✅ | ✅ |
| `weekly_maintenance.py` | ✅ | ✅ | ✅ |
| `weekly_maintenance.sh` | ❌ Bash only | ✅ | ✅ |

`apply_hardening.py` uses only the Python standard library, **zero extra dependencies across all platforms**, and runs directly on any system.

## Installation Steps by Platform

### General (All Platforms)

```bash
# 1. Install Python dependencies (Playwright is required for the interaction engine / verify)
pip install -r requirements.txt

# 2. Download the Playwright browser runtime (once only)
playwright install chromium
```

### Windows Notes

- `weekly_maintenance.sh` **cannot run on Windows**; use `weekly_maintenance.py` instead
- Scheduled tasks: use "Task Scheduler" instead of cron, set the trigger to "Every Monday" and the action to:
  ```
  python C:\path\to\weekly_maintenance.py C:\path\to\MediaCrawler
  ```
- Path note: the `<MediaCrawler root>` parameter of `apply_hardening.py` supports Windows paths (including backslashes)

### macOS / Linux

```bash
# Scheduled maintenance (cron, every Monday at 3:00 AM)
# Choose one:
0 3 * * 1 /bin/bash /path/to/weekly_maintenance.sh /path/to/MediaCrawler
0 3 * * 1 python /path/to/weekly_maintenance.py /path/to/MediaCrawler
```

### Linux Headless Server

Running Playwright on a Linux server without a display requires additional dependencies:

```bash
# Debian/Ubuntu
apt-get install -y libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1
playwright install --with-deps chromium
```

## FAQ

**Q: `apply_hardening.py` modified files. Can it be reverted?**
A: Yes. A backup (`.xhs-stealth.bak`) is automatically created before the first change. Run `python apply_hardening.py <root> --revert` to fully restore.

**Q: Playwright reports that Chromium cannot be found on Windows?**
A: Run `playwright install chromium` again, making sure to do so in the same virtual environment where you run the script.