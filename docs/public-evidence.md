# 公开证据档案（可核实）

> 本页只收录**本轮实际抓取并核对过的公开来源**。  
> 用途：给理论章提供外部参照；**不给四案例虚构数字背书**。  
> 核对时间：2026 年本轮编辑（站点内标注以源站日期为准）。

## E1 · DORA 2025：AI 是放大器

| 项 | 内容 |
|---|---|
| 标题 | State of AI-assisted Software Development（2025 DORA Report） |
| 发布方 | Google Cloud / DORA（合作方含 GitHub、GitLab、IT Revolution 等） |
| 链接 | https://dora.dev/research/2025/dora-report/ |
| 核心表述 | AI 的主要角色是**放大器**（amplifier），放大组织既有的强项与弱项；最大回报不来自工具本身，而来自对底层社会技术系统的投入 |
| 与本书关系 | 直接支撑「不是再买工具，是重建流程与责任」的开篇立场 |

## E2 · DORA 2024 调研中的生产力感知

| 项 | 内容 |
|---|---|
| 文章 | Fostering developers' trust in generative artificial intelligence |
| 发布 | DORA Insights，2024-09-13（页面标注更新至 2025-03-19） |
| 链接 | https://dora.dev/insights/trust-in-ai/ |
| 可引用要点 | ① 2024 DORA 调查中 **75%** 受访者认为 gen AI 对生产力有正面影响；② 谷歌内部日志研究：更常接受补全建议的开发者提交更多 CL、检索信息时间更少（控制职级/司龄/语言等混杂后仍成立）；③ 对 gen AI 输出质量「只信任一点点 / 完全不信任」的约 **39%**（谷歌外部样本）；④ 五条促信任策略含 **可接受使用政策（AUP）**、**高质量快速反馈（评审+自动化测试）**、**鼓励但不强制** |
| 与本书关系 | 第 2 章人在回路、第 19 章门禁、第 23 章提示词治理的外部对照 |

## E3 · DORA 2025：准确率之外的顾虑

| 项 | 内容 |
|---|---|
| 文章 | Concerns beyond the accuracy of AI output |
| 发布 | DORA Insights，2025-06-30（更新 2025-07-31） |
| 链接 | https://dora.dev/insights/concerns-beyond-accuracy-of-ai-output/ |
| 方法 | 8 次约 90 分钟深度访谈；主题编码 |
| 可引用要点 | 半数以上参与者提到的五类顾虑：**数据隐私、技能退化（deskilling）、岗位替代焦虑、恶意使用、开发文化/署名**；策略含澄清 AUP、技能时间、强调评审与自动化测试、**沙箱运行 AI 生成代码**、承认 AI 协作劳动 |
| 与本书关系 | 第 24 章幻觉之外的风险面；第 22 章合规留痕；第 26 章组织博弈 |

## E4 · NIST AI RMF

| 项 | 内容 |
|---|---|
| 文档 | AI Risk Management Framework 1.0（NIST AI 100-1） |
| 发布 | NIST，**2023-01-26** 发布；页面说明 1.0 正随白宫 AI Action Plan 修订 |
| 生成式 AI 附件 | NIST AI 600-1，**2024-07-26** |
| 链接 | https://www.nist.gov/itl/ai-risk-management-framework （PDF：https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf） |
| 核心功能 | Govern / Map / Measure / Manage（治理、映射、度量、管理） |
| 与本书关系 | 与本书「治理委员会 + 度量 + 门禁」结构可对照；不替代本书案例 |

## E5 · GitHub Copilot × Accenture 企业研究

| 项 | 内容 |
|---|---|
| 标题 | Research: Quantifying GitHub Copilot's impact in the enterprise with Accenture |
| 发布 | GitHub Blog，**2024-05-13** |
| 链接 | https://github.blog/news-insights/research/research-quantifying-github-copilots-impact-in-the-enterprise-with-accenture/ |
| 方法 | 与 Accenture 的随机对照试验（RCT）+ 全员采用分析 + 问卷 |
| 可引用要点 | 人均 PR **+8.69%**；PR 合并率 **+15%**；成功构建 **+84%**；建议接受率约 **30%**；约 **67%** 受访者每周使用 ≥5 天；满意度：**90%** 更有成就感、**95%** 更享受编码 |
| 使用限制 | 厂商主导研究，引用时应写明来源与方法，不可当作独立第三方审计 |

## E6 · ADR 经典出处

| 项 | 内容 |
|---|---|
| 标题 | Documenting Architecture Decisions |
| 作者 / 日期 | Michael Nygard，**2011-11-15** |
| 链接 | https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions |
| 核心 | 短文记录架构显著决策：Title / Context / Decision / Status / Consequences；进仓库版本管理；被取代保留并标记 superseded |
| 与本书关系 | 第 25 章 ADR 治理的原始公开出处 |

## 与四案例的边界

| 可以 | 不可以 |
|---|---|
| 用 E1–E6 支撑「为什么要治理、度量什么、如何写 ADR」 | 用外部报告「证明」某虚构事故的具体金额 |
| 在理论章「公开参照」小节引用 | 把厂商营销数字写成行业唯一事实 |
| 对照 NIST 四功能与本书机制 | 宣称本书四案例「来自真实公司」 |

## 建议引用格式（正文）

```text
据 DORA 2025《State of AI-assisted Software Development》，AI 主要扮演放大器角色，
最大回报来自对底层组织系统的投入（https://dora.dev/research/2025/dora-report/）。
```

```text
GitHub 与 Accenture 2024-05-13 公布的企业 RCT 报告称人均 PR 提升 8.69%、
合并率提升 15%（厂商研究，https://github.blog/...）。
```
