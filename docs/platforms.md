# 多平台反爬对照

Mirage 的五层加固（行为层）对 MediaCrawler 支持的 **7 个平台通用**。但各平台反爬强度天差地别——本表帮你定"对应方法"和参数保守度。

## 反爬强度分级

| 平台 | 别名 | 强度 | 主要反爬机制 | 五层够吗 | 建议 |
|------|------|------|-------------|---------|------|
| 抖音 | `dy` | 🔴 极高 | a_bogus / X-Bogus 签名 + 设备指纹 ttwid + 强行为风控 | 行为层必备但不充分 | SLEEP 调到 10s+，量极小，签名靠上游 |
| 快手 | `ks` | 🟠 高 | 签名 + did 设备标识 + 风控 | 同上 | SLEEP 8s+，保守 |
| 知乎 | `zhihu` | 🟡 中 | x-zse-96 签名 + cookie 校验 | 行为层 + 自带签名够日常 | 默认 safe 档 |
| 小红书 | `xhs` | 🟡 中 | x-s / x-t 签名 + 行为风控 | 行为层 + 签名 | 默认 safe 档 |
| 微博 | `wb` | 🟡 中 | cookie 校验 + 老式反爬 | 行为层够 | 默认 safe 档 |
| B站 | `bili` | 🟢 中低 | wbi 签名（较简单）+ 风控松 | 行为层富余 | 可上 normal 档 |
| 贴吧 | `tieba` | 🟢 低 | 基本无强反爬 | 行为层富余 | 可 normal / fast |

## 一键加固

```bash
python apply_hardening.py <MediaCrawler根> -p all --dry-run    # 先看 7 平台会改什么
python apply_hardening.py <MediaCrawler根> -p all              # 7 平台一起加固
python apply_hardening.py <MediaCrawler根> -p dy               # 只加固抖音
python apply_hardening.py <MediaCrawler根> -p all --check      # 全平台体检
python apply_hardening.py <MediaCrawler根> -p bili --revert    # 还原某平台
```

> `cdp_browser.py`(L1) 和 `base_config.py`(L3) 是全平台共享的，`-p all` 时第一个平台改、其余幂等跳过；`core.py`(L2/L4/L5) 各平台独立加固。

## 为什么"难反制"——双层防线

1. **行为层（Mirage 五层）**：让请求"像真人"。这层最稳——平台风控模型再变，"慢一点、有抖动、真 Chrome、鼠标会动"永远像人。**7 平台通用，一次改锚点全适配**。
2. **签名层（MediaCrawler 自带）**：a_bogus / x-s / wbi 等。这层最易失效——平台一更新签名算法，就要等上游 MediaCrawler 跟进。**Mirage 不碰签名，靠上游**（`weekly_maintenance.sh` 会提醒上游补丁）。

所以"难反制" = 行为层稳如磐石 + 签名层跟随上游。两层各司其职，比任何单层方案都耐打。

## 诚实声明

- **强反爬平台（抖音/快手）即便加固，也可能因签名算法更新而暂时失效** —— 这是任何爬虫的共同天花板，不是 Mirage 能单独解决的。遇到大面积抓取失败，先查上游 MediaCrawler 有没有更新签名。
- 各平台都要**只用小号、循序渐进**；强反爬平台更要把量压到最小、间隔拉到最大。
- 加固降低被识别概率，**不保证不被封**。
