# -*- coding: utf-8 -*-
"""
device_profile.py — 统一设备画像 + 自洽校验 + 种子化确定性噪声。

## 为什么需要它（一致性 > 单值伪装）

现代检测（CreepJS / Pixelscan / iphey 这类）**不看单值，看交叉矛盾**：
UA 说 Windows 但 WebGL renderer 说 Apple、时区说东京但语言说 en-US、
主线程说 16 核但 worker 说 4 核 —— 任何一处矛盾都是强信号。

所以"东改一个 webdriver、西改一个 plugins"是**危险**的：局部改真了，整体反而更不自洽，
**比什么都不改更容易被交叉核对抓出来**。正解是像商用 antidetect 浏览器那样，
**从同一张"设备画像"派生所有值**，并在出厂前做一次自洽校验。

## 种子化确定性噪声（canvas/audio）

⚠️ **绝不能每次调用加随机噪声**。真机同一段绘制指令的 hash 是**恒定**的；每次不同 =
比 `navigator.webdriver=true` 还刺眼——检测方就是同一页面跑两遍相同绘制、比对 hash，
不一致直接判伪造（这正是 puppeteer-extra-stealth 的随机噪声在 2026 反成指纹信号的原因）。

正解：**同一个种子 → 同一套噪声**。同 profile 跨会话稳定、不同 profile 之间不同。

## 诚实边界（注入层的天花板，务必读）

本模块工作在**注入脚本层**，能做到的和做不到的：
- ✅ 能做：JS 可见层的一致性（UA / platform / languages / 时区 / 硬件并发 / WebGL 串 / canvas·audio 噪声）
- ❌ **做不到**（架构性，不是实现问题）：
  1. **TLS/JA3 指纹** —— 由网络栈决定，JS 改不了（要靠 curl_cffi 那类，见 docs/tls-fingerprint.md）
  2. **Worker / iframe realm 逃逸** —— 检测方在 Web Worker 里另取一份指纹对比主线程，注入脚本进不去
  3. **toString 泄漏** —— 包装原生函数后 `fn.toString()` 不再是 `[native code]`；就算把 toString 也 patch，
     检测方从干净 iframe 取未污染的原生引用一对比就穿帮
  4. **执行时序竞态** —— 检测脚本可在注入生效前读到原始值
- 📉 结论：**注入层对"静态指纹检测"有效（约 7-8 成），对 CreepJS/Pixelscan 的主动对拍/跨 realm 审计
  封顶约 4-5 成**。要更高必须重编译内核（camoufox 路线），那超出 Mirage"不重编译"的定位。

## 用法

    from device_profile import DeviceProfile

    p = DeviceProfile.from_seed("my-account-01")   # 同种子永远得到同一套画像
    print(p.summary())
    problems = p.check()                            # 自洽校验：空列表 = 无矛盾
    js = p.to_init_script()                         # 交给 page/context.add_init_script(script=js)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

# 真实世界存在的、内部自洽的设备套餐（UA ↔ platform ↔ GPU ↔ 屏幕 全部配对，
# 不是逐项随机拼出来的——随机拼必然产生 "Windows UA + Apple GPU" 这种致命矛盾）。
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

# 语言 ↔ 时区 配对（乱配会矛盾：时区东京却只报 zh-CN 是可疑组合）
LOCALES: list[dict[str, Any]] = [
    {"languages": ["zh-CN", "zh", "en"], "timezone": "Asia/Shanghai"},
    {"languages": ["zh-CN", "zh"], "timezone": "Asia/Shanghai"},
    {"languages": ["ja-JP", "ja", "en-US", "en"], "timezone": "Asia/Tokyo"},
    {"languages": ["en-US", "en"], "timezone": "America/Los_Angeles"},
]


def _digits(seed: str) -> list[int]:
    """把种子摊成一串确定性整数，用于各字段取值（同种子 → 同结果）。"""
    h = hashlib.sha256(seed.encode("utf-8")).digest()
    return list(h)


@dataclass
class DeviceProfile:
    """一套**内部自洽**的设备画像。所有注入值都应从这里派生，不要东一处西一处改。"""
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

    # ── 构造 ─────────────────────────────────────────────
    @classmethod
    def from_seed(cls, seed: str) -> "DeviceProfile":
        """从种子确定性地生成一套自洽画像（同种子永远同结果，跨会话稳定）。"""
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

    # ── 自洽校验 ──────────────────────────────────────────
    def check(self) -> list[str]:
        """出厂自洽校验：返回矛盾清单（空 = 无矛盾）。改了任何字段后都该重跑一次。"""
        p: list[str] = []
        ua = self.ua.lower()
        is_win_ua, is_mac_ua = "windows nt" in ua, "mac os x" in ua
        gpu = self.webgl_renderer.lower()

        if is_win_ua and self.platform != "Win32":
            p.append(f"UA 声称 Windows，但 navigator.platform={self.platform}")
        if is_mac_ua and self.platform != "MacIntel":
            p.append(f"UA 声称 macOS，但 navigator.platform={self.platform}")
        if is_win_ua and ("apple" in gpu or "metal" in gpu):
            p.append("UA 声称 Windows，但 WebGL renderer 是 Apple/Metal —— 致命矛盾")
        if is_mac_ua and ("direct3d" in gpu or "nvidia" in gpu):
            p.append("UA 声称 macOS，但 WebGL renderer 是 Direct3D/NVIDIA —— 致命矛盾")
        if is_win_ua and self.ua_platform != '"Windows"':
            p.append(f"UA 声称 Windows，但 Client Hints platform={self.ua_platform}")
        if is_mac_ua and self.ua_platform != '"macOS"':
            p.append(f"UA 声称 macOS，但 Client Hints platform={self.ua_platform}")
        if not (2 <= self.cores <= 64):
            p.append(f"hardwareConcurrency={self.cores} 不像真实设备")
        if self.memory not in (2, 4, 8, 16, 32):
            p.append(f"deviceMemory={self.memory} 不是浏览器会报的档位")
        if self.screen_w < 800 or self.screen_h < 600:
            p.append(f"屏幕 {self.screen_w}x{self.screen_h} 过小，桌面端可疑")
        if not self.languages:
            p.append("languages 为空 —— 无头浏览器的典型特征")
        if self.timezone.startswith("Asia/Shanghai") and not any(
                x.startswith("zh") for x in self.languages):
            p.append("时区在中国大陆但语言里没有 zh —— 组合可疑")
        return p

    def summary(self) -> str:
        ok = "✓ 自洽" if not self.check() else f"✗ {len(self.check())} 处矛盾"
        return (f"[设备画像 seed={self.seed}] {ok}\n"
                f"  {self.os} / {self.platform} / {self.cores}核 {self.memory}GB / "
                f"{self.screen_w}x{self.screen_h}\n"
                f"  语言={','.join(self.languages)}  时区={self.timezone}\n"
                f"  GPU={self.webgl_renderer[:60]}")

    def to_dict(self) -> dict:
        return asdict(self)

    # ── 生成注入脚本 ──────────────────────────────────────
    def to_init_script(self) -> str:
        """产出可交给 add_init_script 的 JS：统一画像 + 种子化确定性 canvas/audio 噪声。

        ⚠️ 这段脚本受注入层天花板限制（见模块 docstring）：它让**主线程 JS 可见指纹**
        自洽且稳定，但挡不住 worker realm 对拍、toString 审计、TLS 指纹。
        """
        cfg = json.dumps({
            "platform": self.platform, "languages": self.languages,
            "cores": self.cores, "memory": self.memory,
            "vendor": self.webgl_vendor, "renderer": self.webgl_renderer,
            "noiseSeed": self.noise_seed,
        }, ensure_ascii=False)
        return _INIT_JS_TEMPLATE.replace("__MIRAGE_CFG__", cfg)


# 注入脚本模板。要点：
#  - 所有值来自同一份 cfg（单一画像派生，避免自相矛盾）
#  - canvas/audio 噪声由 noiseSeed 驱动的 LCG 产生 → **同种子恒定**，不是每次随机
#  - 只扰动极少量像素、幅度 ±1，肉眼无差但 hash 变了且可复现
_INIT_JS_TEMPLATE = r"""
(() => {
  const CFG = __MIRAGE_CFG__;

  // —— 种子化 PRNG（LCG）：同 seed 必得同序列，保证跨会话 hash 恒定 ——
  const mkRand = (seed) => {
    let s = seed >>> 0;
    return () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; };
  };

  const def = (obj, prop, get) => {
    try { Object.defineProperty(obj, prop, { get, configurable: true }); } catch (e) {}
  };

  // —— 1. 基础画像（全部来自同一份 cfg，保证互相自洽）——
  def(Navigator.prototype, 'platform', () => CFG.platform);
  def(Navigator.prototype, 'languages', () => Object.freeze(CFG.languages.slice()));
  def(Navigator.prototype, 'hardwareConcurrency', () => CFG.cores);
  def(Navigator.prototype, 'deviceMemory', () => CFG.memory);

  // —— 2. WebGL：vendor/renderer 整套一起换（只换一个必然和其它参数矛盾）——
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

  // —— 3. Canvas 种子化确定性噪声 ——
  // 关键：同 seed → 同噪声。每次随机会被"同页跑两遍比 hash"直接判伪造。
  const noise = (data) => {
    const rand = mkRand(CFG.noiseSeed);
    const step = 17;                                  // 只碰约 1/17 的像素
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
    // toDataURL / toBlob 都要拦：只拦一个会被另一个出口对拍抓出来
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

  // —— 4. AudioContext 种子化微扰（复用同一个种子引擎）——
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
