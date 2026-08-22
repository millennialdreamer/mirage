# Mirage Network Situation Notes

> Honest version: for people who actually want to use Mirage well, no sugarcoating.

---

## Direct Connection vs Proxy: Which Is Safer?

### Direct Connection (Mirage Default)

Mirage **does not use a proxy by default**. Reasons:

1. **Residential IPs are naturally cleaner.** The IP from your home broadband/mobile network is exactly like a normal user's—Xiaohongshu's IP quality model scores "residential IP old users" highly, directly raising trust.
2. **Proxies add extra exposure surface.** Every proxy node introduces another risk point of being identified as a bot/IDC. Proxy exit IP ranges are commonly flagged in bulk, especially shared commercial proxy/VPN nodes.
3. **Don't add unnecessary complexity.** Proxy + auth + rotation is itself code risk; direct connection logic is simpler and easier to debug.

### When Is a Proxy Worth It?

- The account is already bound to a fixed IP, but you have now changed networks (e.g., moved from Tokyo back to mainland China)—a sudden login source location change is a risk control point (see below).
- You run many accounts in batch and need per-account IP isolation (one IP per account), so they cannot share the same exit.
- The residential IP is temporarily throttled (rare).

---

## Residential IP vs Datacenter IP: Risk Control Differences

| Dimension | Residential IP | Datacenter/IDC IP |
|------|---------|------------|
| IP quality score | High (ISP-authenticated home broadband/mobile) | Low (common for crawlers/bots) |
| Probability of being flagged | Low | High (especially shared nodes) |
| IP changes | Natural (power-cycle redial is normal) | Overly regular rotation → anomaly |
| Geographic consistency | Matches account registration location | Common drift (Tokyo→Singapore→US) |
| Recommendation | ✅ Preferred | ❌ Avoid if possible; if you must, use a static residential IP |

If you must use a proxy: **static residential proxy** > dynamic residential proxy > datacenter proxy.

---

## Current Proxy Support in Mirage

`network_resilience.py` provides the `ProxyPool` class, which can:

- Accept a list of proxy URLs and rotate round-robin
- Automatically mark failures with a cooldown (default 2 minutes)
- Alert when all proxies are cooling down instead of crashing

But `mirage_loop.py` **does not pass a proxy by default**. If you really need one, manually pass the `proxy` parameter when constructing `playwright.chromium.launch()`, and use `ProxyPool.next()` to get the URL. Mirage does not do this step for you—reducing hidden risks.

---

## What to Do on Weak Networks

Symptoms of a weak network: page load timeouts, images failing to load, `go_back` getting stuck.

Mirage's built-in countermeasures:

1. `network_resilience.py`'s `retry_async`: automatically retries network-layer errors with exponential backoff (max 3 retries, backoff 1.5s/3s/6s + jitter).
2. `CircuitBreaker`: after 5 consecutive failures → circuit opens, all requests stop, and it automatically probes recovery after 60s. Integrate it into the `_danger()` check in `mirage_loop.py` to catch problems early.
3. `human_sleep` has a built-in lower bound—even if rounds are otherwise quick, there is a minimum wait. On a weak network it will actually be slower and will not mistake timeouts for normal behavior.

**If the network is extremely poor (unstable VPN/circumvention):** stop Mirage and wait until the network stabilizes. The abnormal request patterns produced by forcing activity over an unstable network do more harm than not running at all.

---

## Cross-Region Login Is a Risk Control Point

This is the most easily overlooked trap:

- An account registered in Tokyo with a Japanese IP suddenly logs in from a mainland China IP → geographic jump → triggers an "abnormal login location" alert.
- The reverse also applies: a domestic account logging in overseas through a commercial proxy node is equally problematic.

**Solutions**:

1. If you are overseas (e.g., Tokyo) operating a mainland Chinese Xiaohongshu account, **use a direct connection** (Japanese residential IP). Xiaohongshu can recognize overseas Chinese scenarios and will not immediately trigger risk control—but keep frequency more conservative.
2. Do not switch regions repeatedly within the same day (Tokyo today, Beijing tomorrow, Singapore the day after).
3. If the account has been bound to a region for a long time, lower interaction frequency to warm up before switching regions.

---

## About `network_resilience.py` Usage

```python
from network_resilience import ProxyPool, retry_async, CircuitBreaker

# No proxy: call the business function directly
result = await retry_async(your_async_fn, arg1, arg2, max_retries=3)

# Proxy needed: pass a ProxyPool
pool = ProxyPool(["http://p1:1080", "http://p2:1080"])
proxy = pool.next()
# Pass proxy to playwright launch(proxy={"server": proxy}) ...

# Circuit breaker (protects the entire session)
cb = CircuitBreaker(failure_threshold=5, recovery_secs=60)
try:
    async with cb:
        await some_network_call()
except CircuitBreakerOpen:
    print("熔断，停止 session")
```

To verify logic without connecting to the network:

```bash
python3 scripts/network_resilience.py   # runs built-in demo(), never actually connects to network
```