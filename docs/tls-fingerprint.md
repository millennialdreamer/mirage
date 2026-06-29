# TLS / JA3 指纹：Mirage 的边界与正确姿势

> 结论先行：**Mirage 不做 TLS 伪装，大部分也不需要做。** CDP 真 Chrome 模式下页面层 TLS 天然真实；
> 唯一缺口在签名 API 的 httpx 请求层，那属于 MediaCrawler 的请求层 —— Mirage 只给指引、不越界接管。

## 为什么 TLS/JA3 重要

现代风控（尤其海外平台）除了看"浏览器像不像人"，还在 TLS 握手层比对 **JA3 指纹**——
ClientHello 的密码套件、扩展、椭圆曲线等组合。真 Chrome 和 Python 的 `httpx`/`requests`
发出的 ClientHello 截然不同，JA3 一对就露馅：浏览器层装得再像，传输层也可能被一票否决。

## Mirage 架构下的真实情况（两层分开看）

| 请求来源 | 走谁的网络栈 | JA3 指纹 | 结论 |
|---------|-------------|---------|------|
| 页面导航 / XHR / 资源（CDP 真 Chrome） | **真实系统 Chrome** | 真 Chrome 的 JA3 | ✅ 天然真实，无需伪装 |
| 签名 API（小红书 `x-s` / 抖音 `a_bogus`，多用 httpx 发） | **Python OpenSSL** | Python 的 JA3 | ⚠️ 真缺口，但属请求层 |

**关键洞察**：Mirage 的 L3 强制 `ENABLE_CDP_MODE=True` + `CDP_CONNECT_EXISTING=True`
（连真实系统 Chrome，不是 Playwright 自带 chromium、不是 headless）——这个选择的**隐藏好处**
就是页面层的 TLS/JA3 自动是真 Chrome 的，零额外工作。这也是"用真 Chrome"比"伪装 headless"
更稳的深层原因：**连传输层指纹都真**。

## 缺口在哪、归谁

签名 API 的 httpx 请求是 **MediaCrawler 的请求 / 签名层**实现细节，不在 Mirage
"行为层加固"的范畴。Mirage 若接管它，既越界、又会和上游 MediaCrawler 的签名逻辑强耦合
（上游一改就崩）。所以 Mirage 的正确姿势是 **明示风险 + 给指引，不深度接管**。

## 想补签名层 TLS：curl_cffi 指引

如果目标平台风控严到在签名 API 层也查 JA3，可把 MediaCrawler 里发签名请求的
`httpx` / `requests` 换成 [`curl_cffi`](https://github.com/yifeikong/curl_cffi)
（curl-impersonate 的 Python 绑定，能把 ClientHello 伪装成指定 Chrome 版本）：

```python
# 原：import httpx;  httpx.get(url, headers=..., cookies=...)
from curl_cffi import requests
resp = requests.get(url, headers=..., cookies=..., impersonate="chrome")  # JA3 伪装成 Chrome
```

⚠️ 这是改 **MediaCrawler 的请求层**，不是 Mirage 的加固范围。改前先看清上游签名代码、
做好"上游升级会冲突"的准备。Mirage 不替你做这步，也不保证上游兼容。

## 一句话

**CDP 真浏览器保页面 TLS 真实；签名 API 的 TLS 缺口属请求层，Mirage 只给 `curl_cffi` 指引、不越界接管。**
