# Anti-Detection Principles

Mirage is not a new crawler, but a set of behavioral hardening layers specifically designed for MediaCrawler—it significantly reduces the probability of being identified by Xiaohongshu's risk control system by modifying JS fingerprints, disrupting timing, and simulating human actions.

## What Risk Control Detects

Xiaohongshu's risk control is not a single rule, but an online model that fuses multiple signals. It simultaneously observes three categories of features:

1. **Browser fingerprint anomalies**: via JavaScript-exposed properties such as `navigator.webdriver`, `navigator.plugins`, `window.chrome`, `navigator.permissions`, it checks whether the current environment is controlled by automation tools. Typical signs include `webdriver` being `true`, empty plugin list, missing `chrome` object, permission query behavior inconsistent with normal browsers, etc.
2. **Timing and cadence features**: Human actions naturally have irregular intervals, while unmodified scripts/bots usually show a fixed cadence of "one request every N seconds." Statistical models can easily capture such periodicity.
3. **Page interaction behavior**: whether the mouse moves, whether scrolling occurs, whether search is triggered instantly after page load—these are strong signals. A completely still waiting window is very different from real human browsing.

Risk control systems essentially calculate "how bot-like is this session." Mirage's design approach is to erase these signals layer by layer, so that in the model's eyes the session falls as much as possible into the "human-like" distribution.

## Five Layers of Protection

### L1: stealth.min.js injection – correcting automation fingerprints

Xiaohongshu pages dynamically load JavaScript to inspect the environment. The most direct bot marker is `navigator.webdriver === true`, a property Chrome automatically sets when controlled via the DevTools protocol. Scripts also check the length of `navigator.plugins` (normal browsers include built-in plugins such as PDF Viewer), whether `window.chrome` exists, and the return pattern of `navigator.permissions.query`.

`stealth.min.js` (from `puppeteer-extra-plugin-stealth`) injects initialization scripts when a new document is created, overwriting these properties with normal browser values before the page reads them. This tool executes that injection automatically when launching the browser over CDP (Chrome DevTools Protocol), ensuring every frame appears to JavaScript as a "real Chrome opened by a normal human."

### L2: random jitter sleep – removing fixed cadence

The most common tell of a crawler is not "too slow" or "too fast," but "too regular." If the `sleep` between requests is always exactly 6 seconds, the histogram of request intervals shows a sharp peak that immediately exposes automation.

This tool replaces every fixed sleep with a sample from a **log-normal** distribution:
`base * random.lognormvariate(0, 0.45)`. With `base=6s` the median stays at 6s, most waits land
between 4 and 9 seconds, and a long tail occasionally stretches into the teens.

The distribution matters more than the range. Human inter-action times are **right-skewed** — many
short gaps, a few long ones (you got distracted, you actually read something). `random.uniform`
produces a **flat-topped rectangle**, which a Kolmogorov–Smirnov test separates from human behavior
immediately. Measured skewness: `uniform` ≈ **-0.01** (flat), log-normal ≈ **+1.43** (human-shaped).

### L3: batch limits + safety parameters – reducing concurrency and per-action volume

Even for a single legitimate action, excessive volume and concurrency are treated by risk control as "batch collection." This tool forces the per-crawl limit down from 15 to 8 items, making single-action scale closer to ordinary user browsing habits.

At the same time, it locks three key parameters to make the runtime environment more human-like:
- `ENABLE_CDP_MODE=True`: use the CDP protocol to control a real Chrome browser, rather than the Chromium build bundled with Playwright. Real Chrome's behavioral characteristics, binary signatures, and network stack pass environment checks better.
- `HEADLESS=False`: disable headless mode. Headless browsers differ greatly from headed versions in rendering, font metrics, WebGL, and are an easily detectable signal.
- `MAX_CONCURRENCY_NUM=1`: single concurrency. Only one request is in flight at a time, consistent with a real human doing one thing at a time.

### L4: startup warm-up – simulating "look before searching"

A real human always spends some time reading or scanning between opening a page and starting to search. Bots often send a search request the instant the page finishes loading; this "zero-latency interaction" is a very strong automation feature.

This tool inserts a warm-up pause before the first search — again log-normal rather than uniform,
centred around 5.5s and clamped to 2.5–16s. To the platform, that quiet window before the first query
reads as browsing behavior and lowers the session's automation score.

### L5: mouse + scroll simulation – proving "a human is operating"

Risk control systems track whether reasonable interaction events occur during page dwell time. If a crawler only executes `sleep` between requests, with no mouse movement, clicks, or scrolling, risk control can conclude this is an unattended session.

Between page turns, this tool uses Playwright's `mouse.wheel` to scroll and `mouse.move` to move the mouse to 2–4 random coordinates, with about a 40% probability of scrolling back a little. These actions do not generate meaningful business requests, but to the risk control model they mean "the user is still physically operating the device," adding a layer of human-specific randomness to the session's behavior.

## Why Not Use a Proxy Pool

Many people intuitively think "changing IP solves anti-crawling," but