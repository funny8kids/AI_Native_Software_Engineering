# 延伸阅读与公开参照

> 可点开、可复述、可标日期。完整摘要见 [公开证据档案](public-evidence.md)。
> 全部链接的可达性核验记录与核验方法：见 public-evidence.md「外链可达性台账」（核验日期 2026-09-24）。

## 已核实（本轮抓取）

| 主题 | 来源 | 日期 | 链接 |
|---|---|---|---|
| AI 是组织放大器 | DORA 2025 State of AI-assisted Software Development | 2025 | https://dora.dev/research/2025/dora-report/ |
| AI 辅助研发的 ROI 框架 | DORA / Google Cloud, ROI of AI-assisted Software Development | 2026 | https://dora.dev/ai/roi/report/ |
| 信任 / AUP / 快速反馈 | DORA Insights: Fostering developers' trust in gen AI | 2024-09-13 | https://dora.dev/insights/trust-in-ai/ |
| 准确率之外的顾虑 | DORA Insights: Concerns beyond accuracy | 2025-06-30 | https://dora.dev/insights/concerns-beyond-accuracy-of-ai-output/ |
| AI 风险治理框架 | NIST AI RMF 1.0 + GenAI Profile 600-1 | 2023-01-26 / 2024-07-26 | https://www.nist.gov/itl/ai-risk-management-framework |
| 企业 Copilot 效能 | GitHub × Accenture RCT | 2024-05-13 | https://github.blog/news-insights/research/research-quantifying-github-copilots-impact-in-the-enterprise-with-accenture/ |
| ADR 原始形态 | Michael Nygard, Documenting Architecture Decisions | 2011-11-15 | https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions |
| 研究档案入口 | DORA Research Archives | 持续更新 | https://dora.dev/research/ |

## 工程工具（官方文档，按需引用）

| 工具 | 用途 | 文档 |
|---|---|---|
| OpenAPI | HTTP 契约 | https://www.openapis.org/ |
| buf / Protobuf | 契约与 breaking change | https://buf.build/ |
| oasdiff | OpenAPI diff | https://github.com/oasdiff/oasdiff |
| import-linter | Python 分层边界 | https://github.com/seddonym/import-linter |
| Foundry | Solidity 测试 | https://book.getfoundry.sh/ |

## 使用规则

1. 外部数据用于**框架与术语对齐**，不为虚构案例背书。
2. 厂商研究（如 GitHub Blog）必须写明「厂商主导」。
3. 无链接不进正文；过期结论标年份。
4. 四案例仍是**自洽虚构脱敏示范**。

## 与本书机制的对照（速查）

| 本书机制 | 公开锚点 |
|---|---|
| 治理优先于再买工具 | DORA 2025 放大器结论 |
| 人在回路 + 门禁 | DORA 信任研究：评审与自动化测试促信任 |
| 提示词 / AI 使用边界 | DORA AUP 策略；NIST Govern |
| 度量事故率与留痕 | DORA Measure；本书自检表 |
| ADR 留痕 | Nygard 2011 |
| 沙箱 / 隔离跑 AI 代码 | DORA 2025-06-30 洞察中的 sandboxing 建议 |
