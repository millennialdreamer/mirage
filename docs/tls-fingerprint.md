# TLS / JA3 Fingerprint: Mirage's Boundaries and the Right Approach

> TL;DR: **Mirage does not do TLS impersonation, and in most cases it doesn't need to.** Under CDP real Chrome mode, page-layer TLS is naturally real;
> the only gap is the signature API's httpx request layer, which belongs to MediaCrawler's request layer — Mirage only gives guidance and does not overstep to take over.

## Why TLS/JA3 Matters

Modern risk control (especially overseas platforms) doesn't just check whether the browser "behaves like a human"; it also compares the **JA3 fingerprint** at the TLS handshake layer — the combination of ClientHello cipher suites, extensions, elliptic curves, etc. Real Chrome and Python's `httpx`/`requests` send completely different ClientHello, and a JA3 match immediately exposes the difference: no matter how realistic the browser layer is, the transport layer can still veto it outright.

## The Real Situation Under Mirage's Architecture (Look at Two Layers Separately)

| Request Source | Whose Network Stack | JA3 Fingerprint | Verdict |
|---------|-------------|---------|------|
| Page navigation / XHR / resources (CDP real Chrome) | **Real system Chrome** | Real Chrome JA3 | ✅ naturally real, no impersonation needed |
| Signature API (Xiaohongshu `x-s` / Douyin `a_bogus`, mostly sent via httpx) | **Python OpenSSL** | Python JA3 | ⚠️ real gap, but belongs to the request layer |

**Key Insight**: Mirage's L3 enforces `ENABLE_CDP_MODE=True` + `CDP_CONNECT_EXISTING=True`
(connecting to the real system Chrome, not Playwright's bundled Chromium, not headless) — the **hidden benefit** of this choice is that page-layer TLS/JA3 is automatically real Chrome's, with zero extra work. This is also the deeper reason "using real Chrome" is more stable than "impersonating headless": **even the transport-layer fingerprint is real**.

## Where the Gap Is and Whose Responsibility

The signature API's httpx requests are an implementation detail of **MediaCrawler's request / signing layer**, not within Mirage's "behavior-layer hardening" scope. If Mirage took it over, it would both overstep and become tightly coupled to upstream MediaCrawler's signing logic (any upstream change would break it). Therefore Mirage's correct approach is **to flag the risk + give guidance, not deeply take over**.

## Want to Patch Signature-Layer TLS: curl_cffi Guidance

If the target platform's risk control is strict enough to also check JA3 at the signature API layer, you can replace the `httpx` / `requests` that sends signing requests in MediaCrawler with [`curl_cffi`](https://github.com/yifeikong/curl_cffi) (Python bindings for curl-impersonate that can impersonate the ClientHello of a specified Chrome version):

```python
# before: import httpx;  httpx.get(url, headers=..., cookies=...)
from curl_cffi import requests
resp = requests.get(url, headers=..., cookies=..., impersonate="chrome")  # JA3 now impersonates Chrome
```

⚠️ This changes **MediaCrawler's request layer**, not Mirage's hardening scope. Before changing, read the upstream signing code carefully and be prepared for "upstream upgrades will conflict". Mirage does not do this step for you, nor does it guarantee upstream compatibility.

## One Sentence

**CDP real browser keeps page TLS real; the signature API's TLS gap belongs to the request layer — Mirage only provides `curl_cffi` guidance and does not overstep to take over.**