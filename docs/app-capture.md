# App Scraping: Two Routes, the Real Stack, and Mirage's Boundary

> Conclusion first: **App scraping is entirely outside Mirage's capability (web behavior layer hardening)**—it's another runtime stack (real device + frida-server + packet capture/UI automation). Mirage doesn't take over; this article is **a real-stack map + methodology validated in 2026**, helping you choose the right route and avoid pitfalls. Core reminder: **Bypassing SSL pinning via packet capture ≠ done; after decryption you still hit signatures (a_bogus/msToken)**.

## Two Routes, Choose Correctly

| Route | What it does | Suitable for | Cost |
|------|--------|------|------|
| **A Packet capture** | frida/objection bypass SSL pinning → mitmproxy capture plaintext API | Need raw interface data, scale | root + frida-server + **still need to fix signatures after capture** (see below) + countermeasure arms race |
| **B UI automation** | Appium 3 drives real App UI, reads screen to extract data | Small volume precise, bypass all signatures | Slow; scaling requires cloud phone farms |

## Route A: Packet Capture (The Real State of SSL Unpinning)

Still viable in 2026, use **mature, maintained scripts** (don't write your own):
- [`httptoolkit/frida-interception-and-unpinning`](https://github.com/httptoolkit/frida-interception-and-unpinning) — most universal, actively maintained
- [`CYRUS-STUDIO/frida-ssl-pinning-bypass`](https://github.com/CYRUS-STUDIO/frida-ssl-pinning-bypass) — Java + Native fully automatic
- `objection -g <bundleID> explore` → `android sslpinning disable` (no coding required)
- Fallback: Xposed + JustTrustMe (requires root) / IDA patch SO return values (native layer)

**But this is the first step, not the end** — bypassing pinning only lets you see plaintext requests; those requests **still carry a_bogus/msToken/ttwid signatures** (the same anti-crawler set as the web layer). So after packet capture, you still need to go back to [`docs/signature-layer.md`](signature-layer.md) to bridge F2 and fix signatures. **Packet capture ≠ done.**

## Route B: UI Automation (Bypass Signatures, Slow but Stable)

- **Appium 3** (active in 2026, unified Android/iOS, W3C caps) drives the real App, reads the screen to extract data—**completely bypasses signatures** (real device real operation, no such thing as request signatures).
- Suitable for small-volume precise collection, or when signatures are too difficult to be worth fighting head-on.
- Scaling: **cloud phone farms** (AWS Device Farm / BrowserStack / Sauce Labs / TestGrid) + **mobile proxies** (carrier IPs, gold standard for multi-account anti-ban). This is **studio-level investment**.

## Countermeasure Arms Race (Honest)

- **Frida will be detected**: RASP like Approov + cloud attestation specifically catch frida/objection; high-security apps (banks) ban outright. Content apps like Douyin/Xiaohongshu aren't as ruthless as banks, but **version changes + anti-hook are ongoing battles**.
- Mobile fingerprint / canvas fingerprint—mobile proxies can't prevent them either.
- One sentence: App scraping can be done, but it's **heavy investment + continuous maintenance**, not a one-time fix.

## Mirage's Boundary

Mirage hardens the **Playwright-driven web version behavior layer**. App scraping is a **different technology stack**—real device + frida + packet capture/Appium—which Mirage neither takes over nor can harden. This article is **to point you in the right direction + state the reality**:
- Want data at scale → Route A packet capture **+ bridge F2 to fix signatures** (arms race)
- Want small volume precise / bypass signatures → Route B Appium UI automation (slow but stable)
- Don't expect a one-time fix; Douyin App is the hardest of all scenarios.

## One Sentence

**App scraping has two routes: packet capture (frida bypasses pinning, but after capture you still need to fix signatures and return to F2) vs UI automation (Appium bypasses signatures, slow but stable, scaling = cloud phone farms, studio-level investment). Mirage only provides the map, doesn't take over.**