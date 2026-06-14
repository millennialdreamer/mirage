# xhs-stealth-crawler · 构建计划与进度

> 目标：把"小红书爬虫五层反检测加固"沉淀成一个**可发布到 GitHub 的成熟 Claude Code Skill**。
> 卖点：**不会被检测**（anti-detection / stealth）。
> 执行模式：plan（本文件）→ goal（多模型协作，按价值分工）→ loop（构建→多方评审→修→再审，跑到达标）。
> 约束：全程串行 + 国产模型远程评审，**不烧本机、慢速降温**。

## 一、最终交付物结构

```
xhs-stealth-crawler/
├── SKILL.md                 # Claude 用的指令（何时触发 / 加固流程 / 安全运行流程）
├── README.md                # GitHub 门面（五层防护卖点 + 一键加固演示）
├── LICENSE                  # 学习研究用途声明（继承 MediaCrawler 非商用精神）
├── PLAN.md                  # 本文件
├── .gitignore
├── scripts/
│   ├── apply_hardening.py   # ⭐灵魂：一键给任意 MediaCrawler 打入五层加固（幂等/可回滚/自动备份）
│   ├── human_behavior.py    # 人类行为模拟模块（鼠标移动+滚动+停顿）可被 core.py import
│   ├── safe_profile.py      # 安全档/常规档/激进档 一键切换
│   ├── verify_stealth.py    # 跑一个无害自检，确认 webdriver 指纹已隐藏
│   └── weekly_maintenance.sh# 每周自动更新 stealth.min.js + 检查上游补丁
└── docs/
    ├── anti-detection.md    # 反检测原理：五层防护逐层拆解（核心卖点文档）
    └── safe-usage.md        # 安全使用手册：小号 / 放量节奏 / 出警了怎么办
```

## 二、五层防护（卖点定义）

| 层 | 防什么风控信号 | 实现 |
|----|--------------|------|
| L1 stealth.min.js 注入 | `navigator.webdriver` 等自动化指纹 | CDP 启动时自动注入 |
| L2 随机抖动睡眠 | 固定 2s 节拍 = 机器特征 | `random.uniform(base*0.7, base*1.6)` |
| L3 批次限制 | 单次高曝光量 | 默认单次 ≤ 8 条 |
| L4 启动预热 | 打开页面立刻搜 = 非人类 | 首搜前停留 3~8s |
| L5 鼠标+滚动模拟 | 睡眠期页面"冻死" = 机器人 | 翻页间隔随机滚动+移动鼠标 |

## 三、执行步骤（goal 模式·按价值分工）

- [ ] S1 我写核心 `apply_hardening.py`（架构+源码补丁逻辑，判断活，**不外包**）
- [ ] S2 我写 `human_behavior.py` / `verify_stealth.py`（反检测逻辑，**不外包**）
- [ ] S3 迁移 `safe_profile.py` / `weekly_maintenance.sh` 为通用模板
- [ ] S4 我写 SKILL.md（触发判断+流程，judgement，**不外包**）
- [ ] S5 docs/README 套路段落 → delegate 国产起草，我终审改写
- [ ] S6 LICENSE / .gitignore
- [ ] **多方评审（写判分离·loop 核心）**：
  - [ ] R1 DeepSeek 审 `apply_hardening.py` 代码正确性（我写的→国产判）
  - [ ] R2 MiMo 审反检测逻辑是否真能骗过风控（多步推理）
  - [ ] R3 Kimi 审 SKILL.md + docs 完整性/一致性（长文）
  - [ ] R4 我综合三方意见 → 修 → 必要时再审一轮（≤2 轮迭代）
- [ ] S7 自检：apply_hardening.py 对一个临时拷贝跑 --dry-run + 真打 + 验证幂等
- [ ] S8 git 提交 + symlink 进 ~/.claude/skills/

## 四、验收标准（达标才算完）

1. `apply_hardening.py --dry-run` 能正确列出将要做的 5 类改动，不误伤
2. 对一份**干净的 MediaCrawler 拷贝**真打补丁后，`python -c "import ast"` 语法全过
3. 重复打补丁**幂等**（第二次不重复注入、不破坏文件）
4. `--revert` 能从 .bak 完整还原
5. 三方评审无"会被检测/逻辑错"级别的红线问题
6. README 让一个没上下文的人看懂"这是什么 + 怎么一键加固"

## 五、进度日志（loop 每轮回填）

- 2026-06-14 启动，目录骨架 + 本计划已建。
- **S1–S6 全部完成**：apply_hardening.py / human_behavior.py / verify_stealth.py / safe_profile.py / weekly_maintenance.sh / SKILL.md / README.md / docs×2 / LICENSE / .gitignore。
- **端到端自检①全绿**：dry-run 零落盘 → 真打语法过 → 体检六绿 → 幂等 → revert 完整还原（md5 一致）。
- **多方评审（写判分离·loop 核心）**：
  - R1 DeepSeek 审代码 → 抓出 4 个边界 bug（base_config `#` 截断、import 兜底破坏 coding 声明、L2 不容行尾注释、cdp 锚点可能脱类），**全修**。
  - R2 MiMo 审反检测 → 头号发现「L5 瞬移鼠标是负优化」→ 改**贝塞尔曲线**（实测 53 步分步移动，非瞬移）；uniform → 加 15% 概率长停顿。
  - R3 MiMo 审 SKILL.md → 补「没装 MediaCrawler 的引导」+「示例对话」+ README「前置依赖」。
  - （qwen/kimi 今晚模型端超时，已按容灾降级到 deepseek/mimo 完成评审。）
- **修复后自检②全绿 + 位置核验**：L5 调用锚定 search() 内（186 行）、cdp 方法锚定类内、3 个返回点全注入。
- **诚实声明**：anti-detection.md 增「已知未覆盖维度」(canvas/点击链/JA3/账号序列)，守「不打包票」铁律。
- **收尾**：本地 git commit + symlink 进 ~/.claude/skills/xhs-stealth-crawler。

## 六、验收复核（对照第四节）

1. ✅ `--dry-run` 正确列出 5 类改动，不误伤（自检①验证）
2. ✅ 干净 MediaCrawler 拷贝打补丁后语法全过（ast 自检 + 落盘自动回滚兜底）
3. ✅ 重复打补丁幂等（自检①②的第二次打补丁零变化）
4. ✅ `--revert` 从 .bak 完整还原（md5 逐文件一致）
5. ✅ 三方评审红线全部处理（L5 负优化已修，4 个 bug 已修，未覆盖维度已诚实声明）
6. ✅ README 让无上下文者看懂「是什么 + 怎么一键加固」
</content>
