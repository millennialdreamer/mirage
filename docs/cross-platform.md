# 跨平台使用说明

## 脚本兼容性一览

| 脚本 | Windows | macOS | Linux |
|------|---------|-------|-------|
| `apply_hardening.py` | ✅ | ✅ | ✅ |
| `verify_stealth.py` | ✅ | ✅ | ✅ |
| `human_interaction.py` | ✅ | ✅ | ✅ |
| `weekly_maintenance.py` | ✅ | ✅ | ✅ |
| `weekly_maintenance.sh` | ❌ 仅 bash | ✅ | ✅ |

`apply_hardening.py` 只用 Python 标准库，**全平台零额外依赖**，任意系统直接运行。

## 各平台安装步骤

### 通用（所有平台）

```bash
# 1. 安装 Python 依赖（互动引擎/verify 需要 playwright）
pip install -r requirements.txt

# 2. 下载 Playwright 浏览器内核（仅一次）
playwright install chromium
```

### Windows 特别说明

- `weekly_maintenance.sh` 在 Windows 上**无法运行**，请改用 `weekly_maintenance.py`
- 定时任务：用「任务计划程序」替代 cron，触发器选"每周一"，操作填：
  ```
  python C:\path\to\weekly_maintenance.py C:\path\to\MediaCrawler
  ```
- 路径注意：`apply_hardening.py` 的 `<MediaCrawler根>` 参数支持 Windows 路径（含反斜杠）

### macOS / Linux

```bash
# 定时维护（cron，每周一凌晨 3 点）
# 任选其一：
0 3 * * 1 /bin/bash /path/to/weekly_maintenance.sh /path/to/MediaCrawler
0 3 * * 1 python /path/to/weekly_maintenance.py /path/to/MediaCrawler
```

### Linux 无头服务器

在无显示器的 Linux 服务器上运行 playwright，需要额外依赖：

```bash
# Debian/Ubuntu
apt-get install -y libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1
playwright install --with-deps chromium
```

## 常见问题

**Q: `apply_hardening.py` 改了文件，能撤销吗？**
A: 可以，首次改动前会自动备份（`.xhs-stealth.bak`），执行 `python apply_hardening.py <root> --revert` 完整还原。

**Q: Windows 上 playwright 报找不到 chromium？**
A: 重新运行 `playwright install chromium`，确保在你运行脚本的同一个虚拟环境里执行。
