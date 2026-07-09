# 签名层：抖音四重门与「桥接现成库」的正解

> 结论先行：抖音的签名反爬是**四重门叠加**，从零逆向是 2026 年公认的无底洞
> （业界原话 *"Most TikTok Scrapers on GitHub Are Dead"*）。正解不是自己造签名，而是
> **桥接到活跃维护的现成库 [F2](https://github.com/Johnserf-Seed/f2)（Apache-2.0）**——它已把四重门全部解决。
> Mirage 的角色是**给出正确的桥接模板 + `mirage canary` 监测失效**，不接管、不自己逆向、不保证上游兼容
> （这是 MediaCrawler 的请求层，非 Mirage 行为层）。

## 抖音到底卡在哪（四重门，端到端实测）

| 门 | 症状 | 归属 |
|----|------|------|
| ① 拿不到 id | 首页纯 SSR 空壳，连 video/user id 都提不到，要从搜索/分享/主页链接绕 | 请求层 |
| ② msToken | **不在 cookie 里，要动态生成**（另一套反爬） | 请求层 |
| ③ a_bogus + ttwid | 请求要正确的 a_bogus 签名 + ttwid | 请求层 |
| ④ webid / verifyFp / 参数 | 还要 webid、verifyFp、s_v_web_id 等一堆参数 + 抖音频繁改版 | 请求层 |
| ⑤ JA3 传输指纹 | httpx 发签名请求时 TLS 指纹暴露成 Python | 请求层（见 [tls-fingerprint.md](tls-fingerprint.md)）|

**a_bogus 只是第一道门，后面还有四道。** 单点破 a_bogus 完全不够——这正是很多"只做了 xbogus/abogus"的爬虫在 2026 集体阵亡的原因。

## 正解：桥接 F2（每一门都有对应真实解法）

F2（Johnserf-Seed/f2，**Apache-2.0**，活跃维护，覆盖 抖音/TikTok/微博）的管理器逐一对上四重门：

| 门 | F2 真实 API |
|----|-------------|
| ① id | `SecUserIdFetcher.get_sec_user_id(分享/主页 url)` —— 从链接反解 sec_user_id，绕开 SSR 空壳 |
| ② msToken | `TokenManager.gen_real_msToken()`（联网拿真 token）/ `gen_false_msToken()`（纯本地兜底） |
| ③ a_bogus | `ABogusManager.model_2_endpoint(ua, base_endpoint, params)` → 返回补好 a_bogus 的完整 URL |
| ③ ttwid | `TokenManager.gen_ttwid()` |
| ④ webid / verifyFp | `TokenManager.gen_webid()` / `VerifyFpManager.gen_verify_fp()` / `gen_s_v_web_id()` |
| ⑤ JA3 | `curl_cffi.requests.get(url, impersonate="chrome")`（见 [tls-fingerprint.md](tls-fingerprint.md)）|

可运行的桥接参考模板见 [`examples/douyin_signature_bridge.py`](../examples/douyin_signature_bridge.py)（对着 F2 当前真实 API 写）。

## 为什么"桥接"而不是"Mirage 自己做"

1. **从零逆向 = 无底洞**：抖音 a_bogus/msToken 用 ollvm 混淆 + VMP + 频繁改版，逆向成果生命周期常 < 数周，单兵维护追不动。
2. **F2 已经在追**：专职维护 + 社区 + 随抖音改版更新——站在它肩膀上，别重造轮子。
3. **属请求层，不属行为层**：Mirage 加固的是"像不像人"（行为层）；签名是 MediaCrawler 的请求层。Mirage 接管它会与上游强耦合、上游一改就崩。所以 Mirage **只给桥接模板 + 用 `mirage canary` 监测锚点/加固是否失配**，不接管。

## 维护现实（诚实，不打包票）

- 这一层**会**随抖音改版失效——这是签名反爬的天性，不是 bug。
- 生存策略：**依赖 F2 上游 + `mirage canary` 定期离线体检 + 失效时等 F2 跟进**（或换 [Evil0ctal 的 API](https://github.com/Evil0ctal/Douyin_TikTok_Download_API)）。
- 抖音反爬强度在所有平台里**最高**；只用小号、低频、随时准备失效。绝不承诺"永久可用"。

## 小红书对比（签名层容易得多）

小红书的 `x-s` / `x-s-common` 签名比抖音**可控得多**：现成库 [`Spider_XHS`](https://github.com/cv-cat/Spider_XHS) / [`xhshow`](https://github.com/Cloxl/xhshow) 直接可用，维护成本远低于抖音。同样是"桥接现成库"而非自己逆向。

## 一句话

**抖音签名四重门从零逆向必死；正解是桥接 F2（Apache-2.0，已解决全部四门）+ curl_cffi 补 JA3，Mirage 给正确模板 + canary 监测，不接管、不自造。**
