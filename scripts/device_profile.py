# -*- coding: utf-8 -*-
"""
device_profile.py — unified device profile + self-consistency check + seeded deterministic noise.

## Why this exists (consistency > single-value spoofing)

Modern detection (CreepJS / Pixelscan / iphey, etc.) doesn't look at isolated values, it looks for cross-contradictions:
UA says Windows but WebGL renderer says Apple, timezone says Tokyo but language says en-US,
main thread says 16 cores but worker says 4 — any contradiction is a strong signal.

So "change webdriver here, patch plugins there" is dangerous: local values look real, but the whole becomes less self-consistent,
and is easier to catch via cross-checks than doing nothing. The correct approach, like commercial antidetect browsers,
is to derive all values from the same "device profile" and run a self-consistency check before shipping.

## Seeded deterministic noise (canvas/audio)

⚠️ Never add random noise on every call. A real device's hash for the same drawing commands is constant; per-call variation =
more glaring than `navigator.webdriver=true` — detectors simply run the same drawing twice on the same page and compare hashes;
a mismatch means forgery (this is exactly why puppeteer-extra-stealth's random noise became a fingerprint signal by 2026).

Correct: same seed → same noise set. Stable across sessions for the same profile, different between profiles.

## Honest boundary (injection layer ceiling — read this)

This module operates at the injection script layer. What it can and cannot do:
- ✅ Can: JS-visible-layer consistency (UA / platform / languages / timezone / hardware concurrency / WebGL strings / canvas·audio noise)
- ❌ Cannot (architectural, not implementation):
  1. TLS/JA3 fingerprint — determined by the network stack, JS cannot change it (requires curl_cffi-type solutions, see docs/tls-
  fingerprint.md)
  2. Worker / iframe realm escape — the detector can read another fingerprint inside a Web Worker and compare it with the main
  thread; injected scripts cannot enter there
  3. toString leak — after wrapping native functions, `fn.toString()` is no longer `[native code]`; even patching toString won't help,
     the detector gets an unpolluted native reference from a clean iframe and compares, exposing the patch
  4. Execution timing race — the detector script can read original values before injection takes effect
- 📉 Conclusion: the injection layer is effective against "static fingerprint detection" (about 70-80%), but against
CreepJS/Pixelscan active comparison / cross-realm audits
  it tops out around 40-50%. Higher requires kernel-level recompilation (the camoufox path), which is outside Mirage's "no
  recompilation" scope.

## Usage

    from device_profile import DeviceProfile

    p = DeviceProfile.from_seed("my-account-01")   # same seed always yields the same profile
    print(p.summary())
    problems = p.check()                            # self-consistency check: empty list = no contradictions
    js = p.to_init_script()                         # pass to page/context.add_init_script(script=js)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

# Real-world, internally consistent device bundles (UA ↔ platform ↔ GPU ↔ screen all paired,
# not assembled from random per-item choices — random assembly inevitably produces fatal contradictions
# like "Windows UA + Apple GPU").
BUNDLES: list[dict[str, Any]] = [
    {
        "os": "Windows 11",
        "platform": "Win32",
        "ua": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
        "ua_platform": '"Windows"',
        "webgl_vendor": "Google Inc. (NVIDIA)",
        "webgl_renderer": ("ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0), "
                           "or similar"),
        "screens": [(1920, 1080), (2560, 1440), (1536, 864)],
        "cores": [8, 12, 16],
        "memory": [8, 16],
    },
    {
        "os": "Windows 11 (Intel)",
        "platform": "Win32",
        "ua": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"),
        "ua_platform": '"Windows"',
        "webgl_vendor": "Google Inc. (Intel)",
        "webgl_renderer": ("ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0), "
                           "or similar"),
        "screens": [(1920, 1080), (1366, 768)],
        "cores": [4, 8],
        "memory": [8, 16],
    },
    {
        "os": "macOS",
        "platform": "MacIntel",
        "ua": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
        "ua_platform": '"macOS"',
        "webgl_vendor": "Google Inc. (Apple)",
        "webgl_renderer": "ANGLE (Apple, ANGLE Metal Renderer: Apple M2, Unspecified Version)",
        "screens": [(1512, 982), (1728, 1117), (2560, 1440)],
        "cores": [8, 10, 12],
        "memory": [8, 16],
    },
]

# Language ↔ timezone pairs (random mismatch creates a contradiction: Tokyo timezone but reporting only zh-CN is suspicious)
LOCALES: list[dict[str, Any]] = [
    {"languages": ["zh-CN", "zh", "en"], "timezone": "Asia/Shanghai"},
    {"languages": ["zh-CN", "zh"], "timezone": "Asia/Shanghai"},
    {"languages": ["ja-JP", "ja", "en-US", "en"], "timezone": "Asia/Tokyo"},
    {"languages": ["en-US", "en"], "timezone": "America/Los_Angeles"},
]


def _digits(seed: str) -> list[int]:
    """Spread the seed into a deterministic integer sequence used for field selection (same seed → same result)."""
    h = hashlib.sha256(seed.encode("utf-8")).digest()
    return list(h)


@dataclass
class DeviceProfile:
    """A **internally consistent** device profile. All injected values should derive from here — do not patch one field here and another there."""
    seed: str
    os: str
    platform: str
    ua: str
    ua_platform: str
    languages: list[str]
    timezone: str
    cores: int
    memory: int
    screen_w: int
    screen_h: int
    webgl_vendor: str
    webgl_renderer: str
    noise_seed: int = field(default=0)

    # ── construction ─────────────────────────────────────
    @classmethod
    def from_seed(cls, seed: str) -> "DeviceProfile":
        """Deterministically generate a self-consistent profile from a seed (same seed always same result, stable across sessions)."""
        d = _digits(seed)
        b = BUNDLES[d[0] % len(BUNDLES)]
        loc = LOCALES[d[1] % len(LOCALES)]
        sw, sh = b["screens"][d[2] % len(b["screens"])]
        return cls(
            seed=seed, os=b["os"], platform=b["platform"], ua=b["ua"],
            ua_platform=b["ua_platform"], languages=list(loc["languages"]),
            timezone=loc["timezone"], cores=b["cores"][d[3] % len(b["cores"])],
            memory=b["memory"][d[4] % len(b["memory"])], screen_w=sw, screen_h=sh,
            webgl_vendor=b["webgl_vendor"], webgl_renderer=b["webgl_renderer"],
            noise_seed=int.from_bytes(bytes(d[5:9]), "big"),
        )

    # ── self-consistency check ────────────────────────────
    def check(self) -> list[str]:
        """Factory self-consistency check: return a list of contradictions (empty = no contradictions). Re-run after changing any field."""
        p: list[str] = []
        ua = self.ua.lower()
        is_win_ua, is_mac_ua = "windows nt" in ua, "mac os x" in ua
        gpu = self.webgl_renderer.lower()

        if is_win_ua and self.platform != "Win32":
            p.append(f"UA claims Windows but navigator.platform={self.platform}")
        if is_mac_ua and self.platform != "MacIntel":
            p.append(f"UA claims macOS but navigator.platform={self.platform}")
        if is_win_ua and ("apple" in gpu or "metal" in gpu):
            p.append("UA claims Windows but WebGL renderer is Apple/Metal — fatal contradiction")
        if is_mac_ua and ("direct3d" in gpu or "nvidia" in gpu):
            p.append("UA claims macOS but WebGL renderer is Direct3D/NVIDIA — fatal contradiction")
        if is_win_ua and self.ua_platform != '"Windows"':
            p.append(f"UA claims Windows but Client Hints platform={self.ua_platform}")
        if is_mac_ua and self.ua_platform != '"macOS"':
            p.append(f"UA claims macOS but Client Hints platform={self.ua_platform}")
        if not (2 <= self.cores <= 64):
            p.append(f"hardwareConcurrency={self.cores} does not look like a real device")
        if self.memory not in (2, 4, 8, 16, 32):
            p.append(f"deviceMemory={self.memory} is not a browser-reported tier")
        if self.screen_w < 800 or self.screen_h < 600:
            p.append(f"screen {self.screen_w}x{self.screen_h} is too small, suspicious for desktop")
        if not self.languages:
            p.append("languages is empty — typical headless-browser signature")
        if self.timezone.startswith("Asia/Shanghai") and not any(
                x.startswith("zh") for x in self.languages):
            p.append("timezone is in mainland China but languages contain no zh — suspicious combination")
        return p

    def summary(self) -> str:
        ok = "✓ consistent" if not self.check() else f"✗ {len(self.check())} contradiction(s)"
        return (f"[device profile seed={self.seed}] {ok}\n"
                f"  {self.os} / {self.platform} / {self.cores} cores {self.memory}GB / "
                f"{self.screen_w}x{self.screen_h}\n"
                f"  languages={','.join(self.languages)}  timezone={self.timezone}\n"
                f"  GPU={self.webgl_renderer[:60]}")

    def to_dict(self) -> dict:
        return asdict(self)

    # ── generate injection script ─────────────────────────
    def to_init_script(self) -> str:
        """Produce JS suitable for add_init_script: unified profile + seeded deterministic canvas/audio noise.

        ⚠️ This snippet is limited by the injection-layer ceiling (see module docstring): it makes **main-thread JS-visible fingerprint**
        consistent and stable, but cannot defeat worker-realm comparison, toString audits, or TLS fingerprinting.
        """
        cfg = json.dumps({
            "platform": self.platform, "languages": self.languages,
            "cores": self.cores, "memory": self.memory,
            "vendor": self.webgl_vendor, "renderer": self.webgl_renderer,
            "noiseSeed": self.noise_seed,
        }, ensure_ascii=False)
        return _INIT_JS_TEMPLATE.replace("__MIRAGE_CFG__", cfg)


# Injection script template. Key points:
#  - All values come from the same cfg (single-profile derivation, avoids self-contradiction)
#  - canvas/audio noise is generated by an LCG driven by noiseSeed → **same seed constant**, not per-call random
#  - Only perturb a tiny number of pixels, amplitude ±1; visually identical but hash changes and is reproducible
_INIT_JS_TEMPLATE = r"""
(() => {
  const CFG = __MIRAGE_CFG__;

  // —— Seeded PRNG (LCG): same seed always yields same sequence, keeping cross-session hash constant ——
  const mkRand = (seed) => {
    let s = seed >>> 0;
    return () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; };
  };

  const def = (obj, prop, get) => {
    try { Object.defineProperty(obj, prop, { get, configurable: true }); } catch (e) {}
  };

  // —— 1. Base profile (all from the same cfg, ensuring mutual consistency) ——
  def(Navigator.prototype, 'platform', () => CFG.platform);
  def(Navigator.prototype, 'languages', () => Object.freeze(CFG.languages.slice()));
  def(Navigator.prototype, 'hardwareConcurrency', () => CFG.cores);
  def(Navigator.prototype, 'deviceMemory', () => CFG.memory);

  // —— 2. WebGL: swap vendor/renderer as a set (changing only one inevitably contradicts the others) ——
  const patchGL = (proto) => {
    if (!proto || !proto.getParameter) return;
    const orig = proto.getParameter;
    proto.getParameter = function (p) {
      if (p === 37445) return CFG.vendor;     // UNMASKED_VENDOR_WEBGL
      if (p === 37446) return CFG.renderer;   // UNMASKED_RENDERER_WEBGL
      return orig.apply(this, arguments);
    };
  };
  patchGL(window.WebGLRenderingContext && WebGLRenderingContext.prototype);
  patchGL(window.WebGL2RenderingContext && WebGL2RenderingContext.prototype);

  // —— 3. Canvas seeded deterministic noise ——
  // Key: same seed → same noise. Per-call randomness gets caught by "run the same page twice and compare hashes".
  const noise = (data) => {
    const rand = mkRand(CFG.noiseSeed);
    const step = 17;                                  // only touch ~1/17 of pixels
    for (let i = 0; i < data.length; i += 4 * step) {
      const d = rand() < 0.5 ? -1 : 1;
      data[i] = Math.max(0, Math.min(255, data[i] + d));
    }
    return data;
  };
  const wrapCanvas = () => {
    const proto = window.HTMLCanvasElement && HTMLCanvasElement.prototype;
    const ctxProto = window.CanvasRenderingContext2D && CanvasRenderingContext2D.prototype;
    if (!proto || !ctxProto) return;
    const origGetImageData = ctxProto.getImageData;
    ctxProto.getImageData = function () {
      const img = origGetImageData.apply(this, arguments);
      try { noise(img.data); } catch (e) {}
      return img;
    };
    // Both toDataURL / toBlob must be intercepted: patching one lets the other exit expose the mismatch
    const shade = function (orig) {
      return function () {
        try {
          const ctx = this.getContext('2d');
          if (ctx) { const im = origGetImageData.call(ctx, 0, 0, this.width, this.height);
                     noise(im.data); ctx.putImageData(im, 0, 0); }
        } catch (e) {}
        return orig.apply(this, arguments);
      };
    };
    proto.toDataURL = shade(proto.toDataURL);
    proto.toBlob = shade(proto.toBlob);
  };
  wrapCanvas();

  // —— 4. AudioContext seeded micro-perturbation (reuses the same seed engine) ——
  try {
    const AP = window.AudioBuffer && AudioBuffer.prototype;
    if (AP && AP.getChannelData) {
      const orig = AP.getChannelData;
      AP.getChannelData = function () {
        const out = orig.apply(this, arguments);
        try {
          const rand = mkRand(CFG.noiseSeed ^ 0x9e3779b9);
          for (let i = 0; i < out.length; i += 1000) out[i] += (rand() - 0.5) * 1e-7;
        } catch (e) {}
        return out;
      };
    }
  } catch (e) {}
})();
"""
