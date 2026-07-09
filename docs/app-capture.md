# App 抓取：两条路、真实栈、与 Mirage 的边界

> 结论先行：**App 抓取完全在 Mirage（网页行为层加固）能力范围之外**——它是另一套运行时
> （真机 + frida-server + 抓包/UI自动化）。Mirage 不接管；这篇是 **2026 实证过的真实栈地图 + 方法论**，
> 帮你选对路、别踩坑。核心提醒：**抓包绕过 SSL pinning ≠ 搞定，你解密后照样撞签名（a_bogus/msToken）**。

## 两条路，先选对

| 路线 | 干什么 | 适合 | 代价 |
|------|--------|------|------|
| **A 抓包** | frida/objection 绕 SSL pinning → mitmproxy 抓明文 API | 要原始接口数据、规模化 | root + frida-server + **抓完还要补签名**（见下）+ 反制军备赛 |
| **B UI 自动化** | Appium 3 驱动真 App 界面、读屏取数 | 少量精准、绕开所有签名 | 慢；规模化要云手机农场 |

## 路线 A：抓包（SSL unpinning 的真实现状）

2026 仍可行，用**成熟维护脚本**（别自己写）：
- [`httptoolkit/frida-interception-and-unpinning`](https://github.com/httptoolkit/frida-interception-and-unpinning) —— 最通用、活维护
- [`CYRUS-STUDIO/frida-ssl-pinning-bypass`](https://github.com/CYRUS-STUDIO/frida-ssl-pinning-bypass) —— Java + Native 全自动
- `objection -g <bundleID> explore` → `android sslpinning disable`（免写码）
- 兜底：Xposed + JustTrustMe（要 root）/ IDA 改 SO 返回值（native 层）

**但这是第一步，不是终点**——绕过 pinning 只是让你能看到明文请求；那些请求**照样带 a_bogus/msToken/ttwid 签名**（和网页层同一套反爬）。所以抓包之后，你还是要回到 [`docs/signature-layer.md`](signature-layer.md) 桥接 F2 补签名。**抓包 ≠ 搞定。**

## 路线 B：UI 自动化（绕签名，慢但稳）

- **Appium 3**（2026 活跃，Android/iOS 统一，W3C caps）驱动真 App、读屏取数——**完全绕开签名**（真机真操作，没有请求签名一说）。
- 适合少量精准采集，或签名太难不值得硬刚时。
- 规模化：**云手机农场**（AWS Device Farm / BrowserStack / Sauce Labs / TestGrid）+ **移动代理**（运营商 IP，多账号防封金标准）。这是**工作室级投入**。

## 反制军备赛（诚实）

- **Frida 会被检测**：Approov 这类 RASP + 云端 attestation 专门抓 frida/objection，高安全 App（银行）直接封。抖音/小红书这类内容 App 没银行那么狠，但**改版 + 反 hook 是持续对抗**。
- 移动指纹 / canvas 指纹，移动代理也防不住。
- 一句话：App 抓取能做，但是**重投入 + 持续维护**的活，不是一次性搞定。

## Mirage 的边界

Mirage 加固的是 **Playwright 驱动的网页版行为层**。App 抓取是真机 + frida + 抓包/Appium 的**另一套技术栈**，Mirage 既不接管也无法加固。这篇是**给你指对路 + 说清现实**：
- 要数据规模化 → 路线 A 抓包 **+ 桥接 F2 补签名**（军备赛）
- 要少量精准 / 绕签名 → 路线 B Appium UI 自动化（慢但稳）
- 别指望一次搞定；抖音 App 是所有场景里最硬的。

## 一句话

**App 抓取两条路：抓包（frida 绕 pinning，但抓完还要补签名回到 F2） vs UI 自动化（Appium 绕签名、慢但稳，规模化=云手机农场，工作室级投入）。Mirage 只给地图，不接管。**
