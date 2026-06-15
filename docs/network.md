# Mirage 网络情况说明

> 诚实版：写给真正想用好 Mirage 的人，不粉饰。

---

## 直连 vs 代理：哪种更安全？

### 直连（Mirage 默认）

Mirage **默认不接代理**，理由是：

1. **住宅 IP 天然更干净**。你用家里宽带/手机网络的 IP，跟普通用户一模一样——小红书的 IP 质量模型会给"住宅 IP 老用户"打高分，直接拉高可信度。
2. **代理带来额外暴露面**。每引入一个代理节点，就多一个"被识别为机器/IDC"的风险点。代理出口 IP 段被批量标记是常态，尤其机场/VPN 共享节点。
3. **没有必要的复杂度就不加**。代理 + 认证 + 轮换本身是代码风险，直连逻辑更简单、更容易 debug。

### 什么情况才值得上代理？

- 账号已和某个固定 IP 绑定，但你现在换了网络（如从东京换到国内）——登录来源地突变是风控点（见下）。
- 批量多号且需要不同 IP 隔离（每号一 IP），彼此不能共用同一个出口。
- 住宅 IP 被临时限速（罕见）。

---

## 住宅 IP vs 机房 IP：风控差异

| 维度 | 住宅 IP | 机房/IDC IP |
|------|---------|------------|
| IP 质量分 | 高（ISP 认证家宽/移动） | 低（常见于爬虫/机器） |
| 被标记概率 | 低 | 高（尤其共享节点） |
| IP 变动 | 自然（断电重拨正常） | 轮换过于规律 → 异常 |
| 地理一致性 | 和账号注册地吻合 | 常见漂移（东京→新加坡→美国） |
| 推荐程度 | ✅ 首选 | ❌ 尽量不用；非用不可则选静态住宅 IP |

如果一定要代理：**静态住宅代理** > 动态住宅代理 > 数据中心代理。

---

## Mirage 的代理支持现状

`network_resilience.py` 提供了 `ProxyPool` 类，可以：

- 传入代理 URL 列表，Round-Robin 轮换
- 失败自动标记冷却（默认 2 分钟）
- 全部冷却时告警而非崩溃

但 `mirage_loop.py` **默认不传代理**。如果你确实需要，在构造 `playwright.chromium.launch()` 时手动传入 `proxy` 参数，并用 `ProxyPool.next()` 取 URL。Mirage 不帮你做这一步——减少隐患。

---

## 弱网怎么办

弱网的表现：页面加载超时、图片刷不出来、go_back 卡住。

Mirage 的应对策略（已内置）：

1. `network_resilience.py` 的 `retry_async`：网络层错误自动指数退避重试（最多 3 次，退避 1.5s/3s/6s + 抖动）。
2. `CircuitBreaker`：连续失败 5 次 → 熔断，停止一切请求，60s 后自动试探恢复。整合到 `mirage_loop.py` 的 `_danger()` 检查里可以早发现。
3`human_sleep` 本身带下界——哪怕轮间很快也有最短等待，弱网时实际会更慢，不会把超时误当正常。

**如果网络极差（翻墙不稳定）**：直接停掉 Mirage，等网络稳定再跑。强刷不稳定网络产生的异常请求模式比不刷伤害更大。

---

## 跨地域登录是风控点

这是最容易被忽视的坑：

- 你在东京用日本 IP 注册的号，突然从中国大陆 IP 登录 → 地理跳变 → 触发"登录位置异常"告警。
- 反过来也是：国内号跑到海外用机场节点登录同样有问题。

**解决方案**：
1. 如果你在海外（如东京）操作国内小红书号，**直接用直连**（日本住宅 IP），小红书能识别海外华人场景，不会立刻触发风控——但频率要更保守。
2. 不要在同一天内反复切换地域（今天东京，明天北京，后天新加坡）。
3. 如果账号已和某个地区绑定很久，换地区前考虑先降低互动频率暖场。

---

## 关于 `network_resilience.py` 的使用姿势

```python
from network_resilience import ProxyPool, retry_async, CircuitBreaker

# 不用代理：直接调业务函数
result = await retry_async(your_async_fn, arg1, arg2, max_retries=3)

# 需要代理：传入 ProxyPool
pool = ProxyPool(["http://p1:1080", "http://p2:1080"])
proxy = pool.next()
# 把 proxy 传给 playwright launch(proxy={"server": proxy}) ...

# 熔断器（保护整个 session）
cb = CircuitBreaker(failure_threshold=5, recovery_secs=60)
try:
    async with cb:
        await some_network_call()
except CircuitBreakerOpen:
    print("熔断，停止 session")
```

不连网验证逻辑：
```bash
python3 scripts/network_resilience.py   # 运行内置 demo()，全程不真连网
```
