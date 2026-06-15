# examples/ 使用示例

## 文件说明

| 文件 | 说明 |
|------|------|
| `harden_all.sh` | 演示 `apply_hardening.py` 的常用调用方式（Mac/Linux） |

## 快速上手

### 第一步：确认 MediaCrawler 已安装

```bash
ls /path/to/MediaCrawler/config/base_config.py  # 应该存在
```

### 第二步：dry-run 预览改动

```bash
python scripts/apply_hardening.py /path/to/MediaCrawler --dry-run
```

### 第三步：正式打补丁

```bash
python scripts/apply_hardening.py /path/to/MediaCrawler
```

### Windows 用户的等价命令

把 `harden_all.sh` 里的每条 `python scripts/apply_hardening.py ...` 原样在 PowerShell 或 CMD 里执行即可，路径用正斜杠或反斜杠均可。

## 更多说明

- 跨平台差异：见 `docs/cross-platform.md`
- 五层加固原理：见 `docs/anti-detection.md`
- 互动引擎用法：见 `SKILL.md`
