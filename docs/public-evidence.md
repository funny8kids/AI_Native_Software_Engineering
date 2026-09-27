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
| 可引用要点 | ① 2024 DORA 调查中 **75%** 受访者认为 gen AI 对生产力有正面影响；② 谷歌内部日志研究：更常接受补全建议的开发者提交更多 CL、检索信息时间更少（控制职级/司龄/语言等混杂后仍成立）；③ 对 gen AI 输出质量「只信任一点点 / 完全不信任」的约 **39%（谷歌外部样本）**；④ 五条促信任策略含 **可接受使用政策（AUP）**、**高质量快速反馈（评审+自动化测试）**、**鼓励但不强制** |
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
| 可引用要点 | **人均 PR** +8.69%；**PR 合并率** +15%；**成功构建** +84%；**建议接受率**约 30%；约 **67%** 受访者每周使用 ≥5 天；满意度：**90%** 更有成就感、**95%** 更享受编码 |
| 使用限制 | 厂商主导研究，引用时应写明来源与方法，不可当作独立第三方审计 |

## E6 · ADR 经典出处

| 项 | 内容 |
|---|---|
| 标题 | Documenting Architecture Decisions |
| 作者 / 日期 | Michael Nygard，**2011-11-15** |
| 链接 | https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions |
| 核心 | 短文记录架构显著决策：Title / Context / Decision / Status / Consequences；进仓库版本管理；被取代保留并标记 superseded |
| 与本书关系 | 第 25 章 ADR 治理的原始公开出处 |

## E7 · DORA：AI 辅助研发的 ROI

| 项 | 内容 |
|---|---|
| 标题 | ROI of AI-assisted Software Development |
| 发布方 | Google Cloud / DORA |
| 链接 | https://dora.dev/ai/roi/report/ （正文与 references 用此 DORA 站内地址；出版方页面：https://cloud.google.com/resources/content/dora-roi-of-ai-assisted-software-development） |
| 与本书关系 | 附录 J 的「ROI 框架不替代你自己的账」出处；与 E1 的放大器结论同向 |
| 使用限制 | 厂商与机构联合发布，用作讨论框架，不当作独立审计结论 |

## E8 · SWE at Google 第 16 章：单体仓库与版本控制

| 项 | 内容 |
|---|---|
| 标题 | Version Control and Branch Management（Software Engineering at Google，O'Reilly 2020，全书免费在线） |
| 链接 | https://abseil.io/resources/swe-book/html/ch16.html |
| 取回通道 | 本机 2026-09-27 抓取并逐字比对；页面标题实测为 "Version Control and Branch Management" |
| 逐字原文 | "At Google, the vast majority of our source is managed in a single repository (monorepo) shared among roughly 50,000 engineers." ／ "we'll regularly handle 60,000 to 70,000 commits to the repository per work day." ／ "We rely on an in-house-developed centralized VCS called Piper, built to run as a distributed microservice in our production environment." ／ "Almost all projects that are owned by Google live there, except large open source projects like Chromium and Android. This includes public-facing products like Search, Gmail, our advertising products, our Google Cloud Platform offerings, as well as the internal infrastructure necessary to support and develop all of those products."（这一句就是"哪些业务线在同一座仓库里"的公开自述）／ "a globally available VCS storing more than 80 TB of content and metadata" ／ "it takes perhaps 15 seconds total to create a new client at trunk, add a file, and commit an (unreviewed) change to Piper" ／ "we have a notion of granular ownership in the monorepo: at every level of the file hierarchy, we can find OWNERS files that list the usernames of engineers that are allowed to approve commits within that subtree of the repository" ／ "ownership is just a text file, not tied to a physical separation of repositories, so it is trivial to update as the result of a team transfer or organization restructuring" ／ "version control is also about policy" ／ "For every dependency in our repository, there must be only one version of that dependency to choose."（书中称此政策为 "One Version"）／ "For third-party packages, this means that there can be only a single version of that package checked into our repository, in the steady state." | ／ "By virtue of Piper being an in-house product, we have the ability to customize it and enforce whatever source control policies we choose." |
| 脚注事实 | 该章脚注引的一手文章是 **Rachel Potvin and Josh Levenberg, "Why Google stores billions of lines of code in a single repository," Communications of the ACM 59 No. 7 (2016): 78-87** —— 不是常被转引的 "IEEE Software / Leffler" |
| 与本书关系 | 对照案「规模读数」「门禁的公开形状」与「逐业务线治理对照」的原点：这一章同时给出了业务线名单、OWNERS 的执行位置与 "One Version" 这条依赖政策；第 14 章 Python 立包、第 27 章契约治理的反面参照 |
| 使用限制 | 书中数字是 2019 年写作时点，且"vast majority"未给百分比——任何"95% 代码在单体仓库"的说法都不出自本章；"except large open source projects like Chromium and Android" 这一句划出了本章口径的**外部**，把 Chromium/Android 的治理当成同一座仓库的读数就是误引 |

## E9 · SWE at Google 第 22 章：大规模变更（LSC）

| 项 | 内容 |
|---|---|
| 标题 | Large-Scale Changes across Code Bases |
| 链接 | https://abseil.io/resources/swe-book/html/ch22.html |
| 取回通道 | 本机 2026-09-27 抓取并逐字比对 |
| 逐字原文 | "an LSC is any set of changes that are logically related but cannot practically be submitted as a single atomic unit." ／ "for a double-digit percentage (10% to 20%) of the changes in a project to be the result of LSCs" ／ "generating, testing and committing more than 700 independent changes, touching more than 15,000 files per day." ／（脚注 7）"removed more than one billion lines of code from the repository over the course of three days." ／ "And all of this happens with only a few dozen engineers supporting tens of thousands of others." |
| 与本书关系 | 第 21 章平台组的成本账、第 16 章重构批次、第 12 章测试迁移的直接对照 |
| 使用限制 | "10%-20%" 是"某个项目内"的经验区间，不是全公司统计；论文《Large-Scale Changes Across Google》(ICSE 2018) 一篇本机未证得，第 22 章脚注 [5] 实为 Titus Winters, "Non-Atomic Refactoring and Software Sustainability", WAPI 2018 |

## E10 · SWE at Google 第 23 章：持续集成与预提交命中率

| 项 | 内容 |
|---|---|
| 标题 | Continuous Integration |
| 链接 | https://abseil.io/resources/swe-book/html/ch23.html |
| 取回通道 | 本机 2026-09-27 抓取并逐字比对 |
| 逐字原文 | "handling more than 50,000 unique changes and running more than four billion individual test cases." ／ "a change that passes the presubmit has a very high likelihood (95%+) of passing the rest of the tests" ／ "We call this a mid-air collision, and though generally rare, it happens most days at our scale." ／ "CI systems for smaller repositories or projects can avoid this problem by serializing submits so that there is no difference between what is about to enter and what just did." ／ "We also have a system for flake classification, which uses statistics to classify flakes at a Google-wide level, so engineers don't need to figure this out for themselves to determine whether their change broke another project's test (if the test is flaky: probably not)." ／ "it can be dangerous for an application built from code pending review on presubmit to talk to real production backends (think security and quota vulnerabilities), whereas this is often acceptable for a staging environment." |
| 与本书关系 | 第 11 章门禁、第 13 章 flaky 与重试预算、第 19 章"绿灯的含金量"；对照案「门禁的公开形状」与「对本书机制的反证」两节的主证据（mid-air collision 与全站 flake 分类器都是"预提交命中率"这一统计量的代价面） |
| 使用限制 | 95%+ 是"预提交过后还剩多少可能挂"的条件概率表述，不可当成"CI 通过率"；mid-air collision 的 "most days" 是该规模下的频次，且同一页明说小仓库可以靠串行提交绕开——不能据此宣称"你的组织也每天有碰撞" |

## E11 · SWE at Google 第 18 章：构建系统的规模与内部满意度

| 项 | 内容 |
|---|---|
| 标题 | Build Systems and Build Philosophy |
| 链接 | https://abseil.io/resources/swe-book/html/ch18.html |
| 取回通道 | 本机 2026-09-27 抓取并逐字比对 |
| 逐字原文 | "Google runs millions of builds executing millions of test cases and producing petabytes of build outputs from billions of lines of source code every day." ／ "Even simple binaries at Google often depend on tens of thousands of build targets." ／ "Authors of low-level libraries are able to test their changes across the entire codebase, ensuring that their changes are safe across millions of tests and binaries." ／ "Engineers are able to create large-scale changes (LSCs) that touch tens of thousands of source files at a time (e.g., renaming a common symbol) while still being able to safely submit and test those changes." ／（脚注 1）"In an internal survey, 83% of Googlers reported being satisfied with the build system, making it the fourth most satisfying tool of the 19 surveyed." |
| 与本书关系 | 第 9 章工程栈、第 14 章立包与迁移、第 24 章度量口径（**内部调查 = 不可外部复核的读数种类**，本书第 24 章的分类正好有它一个活例） |
| 使用限制 | 83% 是公司内部调查，样本、问卷与口径均未公开，只能作为"自评读数"这一类引用 |

## E12 · SWE at Google 第 11 章：测试分层与 flaky 率

| 项 | 内容 |
|---|---|
| 标题 | Testing Overview / Testing at Google |
| 链接 | https://abseil.io/resources/swe-book/html/ch11.html |
| 取回通道 | 本机 2026-09-27 抓取并逐字比对 |
| 逐字原文 | "The primary constraint is that small tests must run in a single process." ／ "Medium tests can span multiple processes, use threads, and can make blocking calls, including network calls, to localhost." ／ "At Google, our flaky rate hovers around 0.15%, which implies thousands of flakes every day." |
| 与本书关系 | 第 13 章测试金字塔的边界条件、第 19 章门禁里"重跑"这一格的预算 |
| 使用限制 | 0.15% 是**全站口径**的均值，任何单个团队拿它当自己的目标都是误用；small/medium 的具体秒级上限未在该页给出，本书不写 |

## E13 · Google Engineering Practices：评审标准、小 CL、评审速度

| 项 | 内容 |
|---|---|
| 链接 | https://google.github.io/eng-practices/review/reviewer/standard.html ／ https://google.github.io/eng-practices/review/developer/small-cls.html ／ https://google.github.io/eng-practices/review/reviewer/speed.html |
| 取回通道 | 本机 2026-09-27 三份页面各自抓取并逐字比对 |
| 逐字原文 | "The primary purpose of code review is to make sure that the overall code health of Google's code base is improving over time." ／ "Also, a reviewer has ownership and responsibility over the code they are reviewing." ／ "In general, reviewers should favor approving a CL once it is in a state where it definitely improves the overall code health" ／ "100 lines is usually a reasonable size for a CL, and 1000 lines is usually too large" ／ "A 200-line change in one file might be okay, but spread across 50 files it would usually be too large." ／ "One business day is the maximum time it should take to respond to a code review request (i.e., first thing the next morning)." |
| 与本书关系 | 第 2 章人在回路的判据化写法、第 24 章 AI 评审的"谁担责"一格、第 21 章评审时限锚 |
| 使用限制 | 这三页是**给内部评审者看的规范**，不是度量口径；"CL 中位数低于 100 行"之类的数字不在任何公开页上，本书不写 |

## E14 · Chromium 工程门禁文档（评审 / 提交队列 / 发布分支 / 优先级 SLO）

| 项 | 内容 |
|---|---|
| 链接 | 原始站：https://chromium.googlesource.com/chromium/src/+/main/docs/ ＋ 本机改走同源 GitHub 镜像，**逐份落盘的是下面这八个文件**（镜像的目录路径在 raw 通道上取不到列表，所以这里一条一个全链接，不写"目录＋文件名"那种点开是 404 的形状）：https://raw.githubusercontent.com/chromium/chromium/main/docs/code_reviews.md ／ https://raw.githubusercontent.com/chromium/chromium/main/docs/code_review_owners.md ／ https://raw.githubusercontent.com/chromium/chromium/main/docs/contributing.md ／ https://raw.githubusercontent.com/chromium/chromium/main/docs/gardener.md ／ https://raw.githubusercontent.com/chromium/chromium/main/docs/process/release_cycle.md ／ https://raw.githubusercontent.com/chromium/chromium/main/docs/process/merge_request.md ／ https://raw.githubusercontent.com/chromium/chromium/main/docs/process/release_blockers.md ／ https://raw.githubusercontent.com/chromium/chromium/main/docs/process/priorities_slo.md |
| 取回通道 | 2026-09-27：`googlesource.com` 与 `source.android.com` 在本机所有通道不可达，改用官方 GitHub 镜像的 raw 文件逐份落盘后本地检索（镜像 README 自述内容由 Gitiles 同源渲染） |
| 逐字原文 | "All change lists (CLs) must be reviewed." ／ "You must get a positive review from an owner of each directory your change touches." ／ "Owners must be committers with at least 3 months' tenure, and in addition should:" ／ "Beginning on March 24, 2021, committers@ of Chromium are no longer able to circumvent code review and OWNERS approval on CLs." ／ "Rubber Stamper never provides OWNERS approval, by design." ／ "For break-glass scenarios, there are several folks who have the ability to direct push" ／ "TBRs were removed in Q1 2021." ／ "If all try bots return green, the change will automatically be committed." ／ "the CQ will not process the patch unless the person setting the label has try job access" ／ "Chrome ships a new milestone (major version) to the stable channel every two weeks." ／ "which is then stabilized for three weeks before being shipped to stable" ／ "Chrome Browser also maintains every fourth milestone branch for six additional weeks" ／ "Features which are not code complete by branch point should be punted to the following milestone." ／ "Release managers (and delegates like the security team) must review all merges made to release branches" ／ "Merge criteria become more strict as the stable release date approaches" ／ "monitoring the canary channel for 24 hours post-release" ／ "all flag changes must land before the branch cut date." ／ "we will not ship M59 Android builds to either the beta or stable channel until the bug is addressed" ／ "please consider a revert of the culprit CL as your first option if it is safe to do so" ／ "The tree is open, because when the tree is closed nobody can make progress" ／ 优先级表 P0 修复 "Within 1 week"、P1 "Within 4 weeks"、发布阻塞问题 Urgent 修复 "2 days*" |
| 与本书关系 | 对照案「门禁的公开形状」一节的主证据；第 2 章（机器可批格式、人必批权限）、第 19 章（旁路要具名且有到期）、第 28 章（灰度与分支门槛） |
| 使用限制 | Chromium 是开源项目的公开流程文档，**不等同于 Google 公司内部产品线的门禁**；本书只把它当"同一套工程文化里可核的那一份"，不当全集团口径 |

## E15 · F1 论文：广告系统的存储与"schema 变更不许停机"

| 项 | 内容 |
|---|---|
| 标题 | F1: A Distributed SQL Database That Scales（PVLDB Vol. 6 No. 11, VLDB 2013；作者 Shute 等，Google, Inc.） |
| 链接 | https://www.vldb.org/pvldb/vol6/p1068-shute.pdf |
| 取回通道 | 本机 2026-09-27 下载 PDF（416,055 字节）后用 `pdftotext` 转文本、在文本上逐字检索 |
| 逐字原文 | "F1 is a fault-tolerant globally-distributed OLTP and OLAP database built at Google as the new storage system for Google's AdWords system." ／ "The F1 system has been managing all AdWords advertising campaign data in production since early 2012." ／ "This database is over 100 TB, serves up to hundreds of thousands of requests per second, and runs SQL queries that scan tens of trillions of data rows per day." ／ "Availability reaches five nines, even in the presence of unplanned outages" ／ "The system stores data for Google's core business. Any downtime has a significant revenue impact." ／ "Downtime or table locking during schema changes (e.g. adding indexes) is not acceptable." ／ "We have designed F1 to make all schema changes fully non-blocking." |
| 与本书关系 | 对照案「各业务线的差异」里广告这一格的主证据；第 9 章"契约变更要能在线做"的物理动机 |
| 使用限制 | 论文里的系统名是 AdWords，正文一律沿用这个名称并在首次出现处注明它是论文用词；读数是 2013 年投稿时点前的状态，不能外推到其它业务线 |

## E16 · Megastore 论文：广域强一致存储的读数

| 项 | 内容 |
|---|---|
| 标题 | Megastore: Providing Scalable, Highly Available Storage for Interactive Services（CIDR 2011） |
| 链接 | https://www.cidrdb.org/cidr2011/Papers/CIDR11_Paper32.pdf |
| 取回通道 | 本机 2026-09-27 下载 PDF（953,069 字节）并转文本逐字检索 |
| 逐字原文 | "It handles more than three billion write and 20 billion read transactions daily and stores nearly a petabyte of primary data across many global datacenters." |
| 与本书关系 | 对照案规模节：与 E15 一起给出"数据面也是分层的"这一格 |
| 使用限制 | **全文 0 次出现 AdWords/AdMob**（本机 `grep -c` 实测）——"服务广告系统"这一层归因只来自 E15，把 Megastore 写成广告系统的故事就是张冠李戴 |

## E17 · YouTube 官方博客：观看量与音乐分成

| 项 | 内容 |
|---|---|
| 链接 | https://blog.youtube/news-and-events/you-know-whats-cool-billion-hours/ （2017-02-27，Cristos Goodrow，VP of Engineering）／ https://blog.youtube/news-and-events/4-billion-paid-music-industry/ （2021-06-02，The YouTube Team） |
| 取回通道 | 本机 2026-09-27：该域**首两次 TLS 握手失败**（`URLError: UNEXPECTED_EOF_WHILE_READING`），第三次重试成功；两份 HTML 落盘后剥标签逐字检索 |
| 逐字原文 | "people around the world are now watching a billion hours of YouTube's incredible content every single day!" ／ "YouTube has paid over $4 billion to the music industry in the last 12 months alone" ／ "Of the more than $4 billion generated for artists, songwriters, and rights-holders in the last 12 months, over 30% has come from UGC." |
| 与本书关系 | 对照案「逐业务线治理对照」中内容平台那一行的读数来源；"每秒上传一小时"这条本机**未**在原页证得，故不入正文 |
| 使用限制 | 官方口径的营销性发布，日期决定读数（2017 / 2021），正文引用必须带年份 |

## E18 · Gemini 1.0 技术报告：训练设施

| 项 | 内容 |
|---|---|
| 标题 | Gemini 1.5: Unlocking multimodal understanding across millions of tokens of context（官方 PDF）；Gemini 1.0 报告 §3 Training Infrastructure |
| 链接 | https://storage.googleapis.com/deepmind-media/gemini/gemini_1_report.pdf （另有 gemini_v1_5_report.pdf） |
| 取回通道 | 本机 2026-09-27 下载（27,110,234 字节）转文本逐字检索 |
| 逐字原文 | "We trained Gemini models using TPUv5e and TPUv4 (Jouppi et al., 2023), depending on their sizes and configuration." ／ "TPUv4 accelerators are deployed in "SuperPods" of 4096 chips, each connected to a dedicated optical switch" ／ "allows a single Python process to orchestrate the entire training run, dramatically simplifying the development workflow" |
| 与本书关系 | 对照案里 AI 业务线那一格：**同一评审门禁之下，模型的"变更单元"与代码不同**（参数规模官方从未披露，任何"参数量"说法无一手来源） |
| 使用限制 | 报告不披露训练故障率与恢复口径，该格在对照案里按缺口处理 |

## E19 · ChromeOS 发布节奏页

| 项 | 内容 |
|---|---|
| 标题 | Understanding ChromeOS releases |
| 链接 | https://www.chromium.org/chromium-os/developer-library/reference/release/understanding-chromeos-releases/ |
| 取回通道 | 本机 2026-09-27 抓取并逐字比对 |
| 逐字原文 | "ChromeOS operates on a 4 week cycle, and operates on 5 channels" ／ "Extended Stable: The stable channel, but longer. This channel is only available to enrolled devices." |
| 与本书关系 | 与 E14 的 Chrome Browser 双周节奏并排，就是"同一公司、两套发布列车"的那一格 |
| 使用限制 | 设备/渠道口径与 Chrome Browser 不同，两套数字不可混用 |

## E20 · SWE at Google 第 24 章：持续交付（Search／Maps／YouTube／Android 四条产品线的发布口径）

| 项 | 内容 |
|---|---|
| 标题 | Continuous Delivery |
| 链接 | https://abseil.io/resources/swe-book/html/ch24.html |
| 取回通道 | 本机 2026-09-27 抓取（35,252 字节），剥标签转文本后逐字检索；页内 H1 实测为 "Continuous Delivery" |
| 逐字原文 | "One of our codebases, YouTube, is a large, monolithic Python application. The release process is laborious, with Build Cops, release managers, and other volunteers." ／ "Almost every release has multiple cherry-picked changes and respins." ／ "There is also a 50-hour manual regression testing cycle run by a remote QA team on every release." ／ "Google's Search binary is its first and oldest... a search through our codebase can still find code written at least as far back as 2003" ／ "At one point, we were releasing the Search binary into production only once per week, and even hitting that target was rare and often based on luck." ／ "We could now consistently release a new Search binary into production every other day." ／ "if you're late for the release train, it will leave without you" ／ "Generally speaking, no amount of pleading or begging will get a feature into today's release after the deadline has passed." ／ "A world of regular releases means that if a developer misses the release train, they'll be able to catch the next train in a matter of hours rather than days." ／ "On Google Maps, we take the perspective that features are very important, but only very seldom is any feature so important that a release should be held for it." ／ "One release responsibility is to protect the product from the developers." ／ "A key to reliable continuous releases is to make sure engineers "flag guard" all changes." ／ "the recommended best practice is to aim for change-neutral releases. All new features are flag guarded so that the only change being tested during a rollout is the stability of the deployment itself." ／ "at Google, some of our larger apps also A/B test their deployments. This means sending out two versions of the product: one that is the desired update, with the baseline being a placebo (your old version just gets shipped again)." ／ "we could expect a statistically significant change in user metrics simply from pushing an update" ／ "Even if you're building for only Android devices, the sheer diversity of the more than two billion Android devices can make the prospect of qualifying a release overwhelming." ／ "the diversity of our client market was not a problem, but a fact" ／ "Release qualification in a synthetic environment that isn't similar to the production environment can lead to late surprises." ／ "We don't actually release a wildly different version of Search, Maps, or YouTube every day, but to be able to do so requires a robust, well-documented continuous deployment process, accurate and real-time metrics on user satisfaction and product health, and a coordinated team with clear policies on what makes it in or out and why." ／ "counterintuitively, faster is safer" |
| 页内故事两件 | ① 菲律宾方言搜索返回空白页：书中写他们跑遍办公室去数"到底有多少人讲这种方言"，最后把问题交给 Search 的 SVP，结论是 "we delayed the release and fixed the bug"；② 周五晚六点六个工程师带着 NBA 合同要求 cherry-pick，书里写的答复是 "it will take four hours to cut and test a new binary" |
| 与本书关系 | 对照案「发布与可靠性」「逐业务线治理对照」「各业务线的差异」三节的主证据——它是目前找到的**唯一一份**在同一页里同时点名 Search、Maps、YouTube、Android 四条产品线发布治理的公开材料 |
| 使用限制 | 本章由多位贡献作者按各自经历写（文中署名 Sheri Shipe），是**从业者回忆＋经验总结**，不是流程规范：Search"隔天发一次"、YouTube"50 小时人工回归"都是书中写作时点的状态，书本身也强调"how often a viable release is created can be separated from how often a user receives it"，任何"Google 每天发布 X 次"的推断都不出自这一页 |

## E21 · SWE at Google 第 17 章：Code Search（全站代码视图的两级新鲜度）

| 项 | 内容 |
|---|---|
| 标题 | Code Search |
| 链接 | https://abseil.io/resources/swe-book/html/ch17.html |
| 取回通道 | 本机 2026-09-27 抓取（48,772 字节），剥标签转文本后逐字检索；页内 H1 实测为 "Code Search" |
| 逐字原文 | "the Google codebase is so large that a local copy of the full codebase—a prerequisite for most IDEs—simply doesn't fit on a single machine" ／ "the Code Search index is incrementally updated with every submitted change, enabling index construction with linear cost" ／ "Incrementality isn't possible for it, as any code change can potentially influence the entire codebase, and in practice often does affect thousands of files." ／ "It uses a ton of compute resources to produce the index daily (the current frequency)." ／ "The discrepancy between the instant search index and the daily cross-reference index is a source of rare but recurring issues for users." ／ "Within Google, we process much more than one million search queries from developers within Code Search per day." ／ "For one million queries, an increase of just one second per search request corresponds to about 35 idle full-time engineers every day." ／ "During an incident, a discrepancy between the index and the running code can be especially problematic because it can hide real causes or introduce irrelevant distractions." |
| 与本书关系 | 对照案「规模的公开读数」的"新鲜度"那一格；第 5 章考古画图、第 21 章事故取证里"你查到的图是不是当时跑着的那份"的公开活例 |
| 使用限制 | "35 名空闲全职工程师"是**该书为量化延迟价值做的换算示例**，不是编制数字；"more than one million queries per day"是全站开发者口径，与产品端用户无关 |

## E22 · SWE at Google 第 19 章：Critique（评审工具怎么把信任写进界面）

| 项 | 内容 |
|---|---|
| 标题 | Critique: Google's Code Review Tool |
| 链接 | https://abseil.io/resources/swe-book/html/ch19.html |
| 取回通道 | 本机 2026-09-27 抓取（47,147 字节），剥标签转文本后逐字检索；页内 H1 实测为 "Critique: Google's Code Review Tool" |
| 逐字原文 | "Code review is not for slowing others down; instead, it is for empowering others. Trusting colleagues as much as possible makes it work." ／ "This might mean, for example, trusting authors to make changes and not requiring an additional review phase to double check that minor comments are actually addressed." ／ "Trust also plays out by making changes openly accessible (for viewing and reviewing) across Google." ／（脚注 2）"Although most changes are small (fewer than 100 lines), Critique is sometimes used to review large refactoring changes that can touch hundreds or thousands of files, especially for LSCs that must be executed atomically" |
| 与本书关系 | 对照案「门禁的公开形状」里"评审工具的默认值就是治理"那一格；第 2 章人在回路、第 24 章 AI 评审的"谁担责"一格 |
| 使用限制 | 这一页讲的是**工具的设计取向**，不是流程 SLA；"fewer than 100 lines" 是脚注里的观察性说法，不能与 E13 的规范句合并成"Google 规定 CL 不超过 100 行" |

## E23 · SWE at Google 第 21 章：依赖管理（Hyrum 定律、third_party 双 OWNERS、AppEngine 的三年拖延）

| 项 | 内容 |
|---|---|
| 标题 | Dependency Management |
| 链接 | https://abseil.io/resources/swe-book/html/ch21.html |
| 取回通道 | 本机 2026-09-27 抓取（99,839 字节），剥标签转文本后逐字检索；页内 H1 实测为 "Dependency Management" |
| 逐字原文 | "With a sufficient number of users, every observable behavior of your system will be depended upon by someone."（书中对 Hyrum's Law 的表述）／ "The idea that SemVer patch versions, which in theory are only changing implementation details, are 'safe' changes absolutely runs afoul of Google's experience with Hyrum's Law" ／ "make sure at least two engineers are signed up as OWNERS to maintain the package in the event that any maintenance is necessary" ／ "Nobody changed the OWNERS file. Thousands of projects depend on this indirectly—we can't just delete it without breaking the build for Search and a dozen other big teams." ／ "Our third_party policies don't work for these unfortunately common scenarios. We roughly understand that we need a higher bar for ownership, we need to make it easier (and more rewarding) to update regularly and more difficult for third_party packages to be orphaned and important at the same time." ／ "Our codebase has an expected lifespan of decades at this point: upstream projects that are not explicitly prioritizing stability are a risk." ／ "an optimization opportunity worth some thousands of aggregate CPUs across Google's fleet was significantly delayed, not because it was difficult to update the API that 250 million lines of code depended upon, but because a tiny handful of projects were relying on unpromised and unexpected things" ／ "Because there were some customers that were paying a significant amount of money for AppEngine services, AppEngine was able to make a strong business case that a forced switch to the new language and compiler versions must be delayed." ／ "That situation persisted for almost three years." ／ "if most (or at least a representative sample) of our dependencies are publicly visible, we run the tests for those dependencies with every proposed change" |
| 与本书关系 | 对照案「对本书机制的反证」最强的一格：第 27 章"变更分类决定版本号位"的整套写法，在这一页被明确否定并给出替代口径（跑下游测试，而不是给分类打标签）；第 9 章"契约的物理动机"、第 14 章立包、第 26 章"付费客户能否决全站升级" |
| 使用限制 | AppEngine 段是书中自述的历史事件（2014 年起的运行时升级），年份按原书；"250 million lines of code" 是该书对该 API 依赖面的表述，不是仓库总量读数；本页两处 Hyrum 定律措辞不同（另一处为 "With enough users, any 'observable' of your system will come to be depended upon by somebody"），本书只引前者并注明出处 |

## E24 · SWE at Google 第 15 章：废弃（强制废弃要有执行机制）

| 项 | 内容 |
|---|---|
| 标题 | Deprecation |
| 链接 | https://abseil.io/resources/swe-book/html/ch15.html |
| 取回通道 | 本机 2026-09-27 抓取（43,176 字节），剥标签转文本后逐字检索；页内 H1 实测为 "Deprecation" |
| 逐字原文 | "We've learned at Google that without explicit owners, a deprecation process is unlikely to make meaningful progress, no matter how many warnings and alerts a system might generate." ／ "For compulsory deprecation to actually work, its schedule needs to have an enforcement mechanism." ／ "This does not imply that the schedule can't change, but empower the team running the deprecation process to break noncompliant users after they have been sufficiently warned through efforts to migrate them." ／ "Without this power, it becomes easy for customer teams to ignore deprecation work in favor of features or other more pressing work." ／ "don't ever deprecate anything, or delegate deprecation efforts to the users of the system" ／ "Much of the initial work of deprecation is determining who is using the old system—and in which unanticipated ways." ／ "Deprecating in an organized and well-managed fashion is often overlooked as a source of benefit to an organization, but is essential for its long-term sustainability." |
| 与本书关系 | 对照案「可抄与不可抄」与「对本书机制的反证」；第 25 章文档/ADR/令牌治理里"退役也要有 owner 和截止日"这一格的公开支撑 |
| 使用限制 | 这一页的口径是**内部平台对内部使用者**的废弃（书中"customer teams"指内部依赖方），把它当成"对用户宣布停服"的流程就是越界 |

## E25 · SWE at Google 第 25 章：Compute as a Service（Borg：容量参数会自己长成事故）

| 项 | 内容 |
|---|---|
| 标题 | Compute as a Service |
| 链接 | https://abseil.io/resources/swe-book/html/ch25.html |
| 取回通道 | 本机 2026-09-27 抓取（79,206 字节），剥标签转文本后逐字检索；页内 H1 实测为 "Compute as a Service" |
| 逐字原文 | "Google has only recently reached a point at which more than half of the resource usage over the whole Borg fleet is determined by rightsizing automation." ／ "these configuration parameters become themselves, over time, a source of inefficiency" ／ "as time passes, the program evolves (likely grows), but the configuration parameters do not keep up. This ends in an outage—where it turns out that over time the new releases had resource requirements that ate into the slack left for unexpected spikes or outages" ／ "in 2011, engineers working on Borg discovered that the exhaustion of the process ID space (which was set by default to 32,000 PIDs) was becoming an isolation failure" ／ "the vast majority of Google's resource footprint comes from high-traffic services, and so it's comparably cheap to overprovision the small services" ／ "scheduling for GPUs and TPUs is a major change in Borg that happened over the past 10 years" ／ "any compute service choice will eventually become surrounded by a large ecosystem of helper services—tools for logging, monitoring, debugging, alerting, visualization, on-the-fly analysis, configuration languages and meta-languages, user interfaces, and more. These tools would need to be rewritten as a part of a compute service change, and even understanding and enumerating those tools is likely to be a challenge for a medium or large organization" |
| 与本书关系 | 对照案「各业务线的差异」里"同一底座、不同暴露面"那一格；第 18 章亿级流量、第 21 章回滚与容量、第 24 章"配置也是一种会腐烂的变更" |
| 使用限制 | 全章写的是**内部**计算底座 Borg，不等于对外售卖的 Google Cloud；"half of the resource usage" 是自动化接管比例，不是成本或可用性读数；GPU/TPU 调度那一句是"过去 10 年间发生"的粗粒度表述 |

## E26 · SWE at Google 第 10 章：文档（把文档挪进代码的那套流程）

| 项 | 内容 |
|---|---|
| 标题 | Documentation |
| 链接 | https://abseil.io/resources/swe-book/html/ch10.html |
| 取回通道 | 本机 2026-09-27 抓取（53,761 字节），剥标签转文本后逐字检索；页内 H1 实测为 "Documentation" |
| 逐字原文 | "When Google was much smaller and leaner, it had few technical writers. The easiest way to share information was through our own internal wiki (GooWiki)." ／ "The way to improve the situation was to move important documentation under the same sort of source control that was being used to track code changes." ／ "Documents began to have their own owners, canonical locations within the source tree, and processes for identifying bugs and fixing them; the documentation began to dramatically improve." ／ "Errors in the documents could be reported within our bug tracking software. Changes to the documents could be handled using the existing code review process." ／ "Eventually, engineers began to fix the documents themselves or send changes to technical writers (who were often the owners)." ／ "the state of software testing in the late 1980s"（作者对文档处境的类比）／ "Not every engineering team needs a technical writer (and even if that were the case, there aren't enough of them)." |
| 与本书关系 | 对照案「可抄与不可抄」里"评审与文档同流程"那一行的出处；第 25 章文档/ADR/设计令牌治理——本书写的"文档进版本控制、要有 owner"，这一页就是它的公开同型物 |
| 使用限制 | 这一页讲的是**工程文档**（API 文档、设计文档），不含产品帮助文档与对外合规文本；GooWiki 段的替换过程书中只给方向不给时间表，任何"迁移耗时 X 年"的说法不出自本页 |

## E27 · SWE at Google 第 20 章：静态分析（假阳率、误报账与 "CLEANUP=" 豁免）

| 项 | 内容 |
|---|---|
| 标题 | Static Analysis |
| 链接 | https://abseil.io/resources/swe-book/html/ch20.html |
| 取回通道 | 本机 2026-09-27 抓取（43,625 字节），剥标签转文本后逐字检索；页内 H1 实测为 "Static Analysis" |
| 逐字原文 | "Static analysis tools at Google must scale to the size of Google's multibillion-line codebase." ／ "In addition to making sure analysis tools can run on a large codebase, we also must scale up the number and variety of analyses available. Analysis contributions are solicited from throughout the company." ／ "static analysis can save reviewer time by highlighting common issues automatically; static analysis tools help the code review process (and the reviewers) scale." ／ "Reviewers click \"Please Fix\" thousands of times per day, and authors apply the automated fixes approximately 3,000 times per day." ／ "We also keep track of how well analysis tools are performing. If you don't measure this, you can't fix problems. We only deploy analysis tools with low false-positive rates" ／ "User trust is extremely important for the success of static analysis tools." ／ "Team-specific presubmits can make the large-scale change (LSC) process (see Large-Scale Changes) more difficult, so some are skipped for changes with \"CLEANUP=\" in the change description." |
| 与本书关系 | 对照案「门禁的公开形状」3.3 小节的主证据：机器检查与人工评审的分工是有**日读数**的（一天数千次"请修复"点击、约 3,000 次自动修复被应用），而豁免写进了变更描述（"CLEANUP="），不是写在会上；第 19 章五层门禁、第 24 章 AI 评审的"假阳率是入场券"这一格 |
| 使用限制 | "multibillion-line codebase" 是该页的表述，与 E8 的"billions of lines"同源，不是可分列的第二个读数；"thousands of times per day / approximately 3,000 times per day" 是 Tricorder 一系统的日内读数，写作时点口径，不可与任何全站指标相加 |

## E28 · SWE at Google 第 23 章补充：预提交该跑哪些测试、测试选择按预测命中率

| 项 | 内容 |
|---|---|
| 标题 | Continuous Integration（与 E10 同页，此处登记本节单独用到的段落） |
| 链接 | https://abseil.io/resources/swe-book/html/ch23.html |
| 取回通道 | 本机 2026-09-27 抓取（80,634 字节）并逐字检索 |
| 逐字原文 | "which tests do we run on presubmit, which do we save for post-submit, and which do we save even later until our staging deploy? Accordingly, how do we represent our SUT at each of these points?" ／ "The main reason is that it's too expensive. Engineer productivity is extremely valuable, and waiting a long time to run every test during code submission can be severely disruptive." ／ "by removing the constraint for presubmits to be exhaustive, a lot of efficiency gains can be made if tests pass far more frequently than they fail. For example, the tests that are run can be restricted to certain scopes, or selected based on a model that predicts their likelihood of detecting a failure." |
| 与本书关系 | 对照案「门禁的公开形状」3.3：预提交不穷举是**经济性决定**，且选择口径可以是"预测这条测试发现失败的可能性"；第 13 章测试预算、第 19 章门禁分层 |
| 使用限制 | 与 E10 同页不同段，不构成独立印证；"按预测命中率选测试"是书中描述的做法，未给模型口径或准确率读数 |

## 外链可达性台账（编辑部实测）

> **这一节只誊一张命令打出来的表**：`python3 scripts/probe_external_links.py`。它做三件事——
> ① 从 `docs` 下全部 .md 的**围栏外**枚举 http(s) 地址并去重；② 逐条直连（首跑 15 秒超时，失败者换 30 秒重跑一次，
> 两次都不通才记"本机不可达"）；③ 把逐条结果打成表，并在末尾打印分档读数。
> 条数、状态、"出现在哪几个文件"三列都来自它那一跑，本节不再自己数一遍；日志路径写在表下面那行。
>
> **口径为什么换成"从正文派生"这一种**：下面这份表的前一版（2026-09-24）是一份**手抄的链接清单**——列了 17 条就只测这 17 条。
> 第十七轮给对照案补了 21 条来源，那 21 条一条都没进过核验；把枚举改成从正文派生之后，同一口径一次量到的去重 URL
> 比手抄清单多出数倍。手抄清单漏掉的不是几条链接，而是「清单之外还会长东西」这件事本身。这与第八条守卫的名册支同形：
> 那份名册也从手抄文件名改成现读 `scripts/check_*.py`（理由一样，抄的那一份会在第一个新件落地当天开始漏检）。
>
> **核验日期：2026-09-27**，本机、单栈、无代理。下面这张表是**该日那一跑的逐字抄件**；
> 本节自身也是那条命令的枚举对象，所以从下一跑起，表内链接会与档案里同址的那条**去重成一条**（"出现在"那一列并两个文件名），
> 条数不会因为誊表而翻倍。

> 誊法有两条让步，都是被实测逼出来的。① 探针给「本机不可达」那几格的报错原文带尖括号，而尖括号原文一进表格单元格就会被 Markdown 当成标签吞掉；把尖括号转义成实体也不算解决——渲染出来的文本仍长得像标签，第九条守卫照样判泄漏。所以表内那一格只留人话，报错原文一字不改地住在下面的围栏里（围栏内是字面文本，守卫不看那儿）。② 探针表里的「最终地址」那一列**不誊**：它是上一条链接的去向，誊进本节它就变成新的被测对象——本轮真量到过，那一跑比前后两跑多测出七条，全是本页自己抄出来的落点。两条让步都只挪字的位置，不改一个字的内容。

| 链接 | 状态 | 出现在 |
|---|---|---|
| https://abseil.io/resources/swe-book/html/ch10.html | 200 | public-evidence.md |
| https://abseil.io/resources/swe-book/html/ch11.html | 200 | public-evidence.md |
| https://abseil.io/resources/swe-book/html/ch15.html | 200 | public-evidence.md |
| https://abseil.io/resources/swe-book/html/ch16.html | 200 | public-evidence.md |
| https://abseil.io/resources/swe-book/html/ch17.html | 200 | public-evidence.md |
| https://abseil.io/resources/swe-book/html/ch18.html | 200 | public-evidence.md |
| https://abseil.io/resources/swe-book/html/ch19.html | 200 | public-evidence.md |
| https://abseil.io/resources/swe-book/html/ch20.html | 200 | public-evidence.md |
| https://abseil.io/resources/swe-book/html/ch21.html | 200 | public-evidence.md |
| https://abseil.io/resources/swe-book/html/ch22.html | 200 | public-evidence.md |
| https://abseil.io/resources/swe-book/html/ch23.html | 200 | public-evidence.md |
| https://abseil.io/resources/swe-book/html/ch24.html | 200 | public-evidence.md |
| https://abseil.io/resources/swe-book/html/ch25.html | 200 | public-evidence.md |
| https://api.github.com/repos/OAI/OpenAPI-Specification/releases | 200 | public-evidence.md、references.md |
| https://api.github.com/repos/OpenAPITools/openapi-generator/releases/latest | 200 | public-evidence.md、references.md |
| https://api.github.com/repos/protocolbuffers/protobuf/releases/latest | 200 | public-evidence.md、references.md |
| https://blog.youtube/news-and-events/4-billion-paid-music-industry/ | 200 | public-evidence.md |
| https://blog.youtube/news-and-events/you-know-whats-cool-billion-hours/ | 200 | public-evidence.md |
| https://book.getfoundry.sh/ | 200 | public-evidence.md、references.md |
| https://book.getfoundry.sh/forge/tests | 200 | public-evidence.md、references.md |
| https://book.getfoundry.sh/reference/anvil/anvil | 200 | public-evidence.md、references.md |
| https://book.getfoundry.sh/reference/config/overview | 200 | public-evidence.md、references.md |
| https://book.getfoundry.sh/reference/forge/coverage | 200 | public-evidence.md、references.md |
| https://book.getfoundry.sh/reference/forge/test | 200 | public-evidence.md、references.md |
| https://book.getfoundry.sh/reference/versions | 200 | public-evidence.md、references.md |
| https://buf.build/ | 200 | public-evidence.md、references.md |
| https://chromium.googlesource.com/chromium/src/+/main/docs/ | 不可达（两次都不通，原文见下方日志块） | public-evidence.md |
| https://cloud.google.com/resources/content/dora-roi-of-ai-assisted-software-development | 不可达（两次都不通，原文见下方日志块） | public-evidence.md |
| https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions | 200 | manuscript/ch30-第25章-文档ADR-RFC-设计令牌治理.md、public-evidence.md、references.md |
| https://docs.langchain.com/oss/python/langchain/models | 200 | public-evidence.md、references.md |
| https://docs.semgrep.dev/cli-reference | 200 | public-evidence.md、references.md |
| https://docs.sentry.io/cli/configuration/ | 200 | public-evidence.md、references.md |
| https://dora.dev/ai/roi/report/ | 200 | manuscript/ch41-附录J-AI系统工程.md、public-evidence.md、references.md |
| https://dora.dev/insights/concerns-beyond-accuracy-of-ai-output/ | 200 | manuscript/ch28-第23章-提示词工程与归档.md、manuscript/ch29-第24章-AI评审与幻觉处理.md、manuscript/ch41-附录J-AI系统工程.md、public-evidence.md、references.md |
| https://dora.dev/insights/trust-in-ai/ | 200 | manuscript/ch01-这本书是什么.md、manuscript/ch07-第2章-人在回路.md、manuscript/ch28-第23章-提示词工程与归档.md、public-evidence.md、references.md |
| https://dora.dev/research/ | 200 | public-evidence.md、references.md |
| https://dora.dev/research/2025/dora-report/ | 200 | manuscript/ch01-这本书是什么.md、manuscript/ch06-第1章-AI原生不是让AI写代码.md、manuscript/ch09-第4章-AI原生工程栈.md、public-evidence.md、references.md |
| https://github.blog/news-insights/research/research-quantifying-github-copilots-impact-in-the-enterprise-with-accenture/ | 200 | manuscript/ch02-90天总路线图.md、manuscript/ch06-第1章-AI原生不是让AI写代码.md、manuscript/ch09-第4章-AI原生工程栈.md、public-evidence.md、references.md |
| https://github.com | 200 | manuscript/_navbar.md、public-evidence.md |
| https://github.com/aquasecurity/trivy/releases.atom | 200 | public-evidence.md、references.md |
| https://github.com/foundry-rs/foundry/releases.atom | 200 | public-evidence.md、references.md |
| https://github.com/oasdiff/oasdiff | 200 | public-evidence.md、references.md |
| https://github.com/seddonym/import-linter | 200 | public-evidence.md、references.md |
| https://github.com/semgrep/semgrep/releases.atom | 200 | public-evidence.md、references.md |
| https://google.github.io/eng-practices/review/developer/small-cls.html | 200 | public-evidence.md |
| https://google.github.io/eng-practices/review/reviewer/speed.html | 200 | public-evidence.md |
| https://google.github.io/eng-practices/review/reviewer/standard.html | 200 | public-evidence.md |
| https://grafana.com/docs/grafana/latest/administration/provisioning/ | 200 | public-evidence.md、references.md |
| https://kafka.apache.org/41/configuration/producer-configs/ | 200 | public-evidence.md、references.md |
| https://nginx.org/en/docs/configure.html | 200 | public-evidence.md、references.md |
| https://nginx.org/en/docs/control.html | 200 | public-evidence.md、references.md |
| https://nginx.org/en/docs/http/ngx_http_proxy_module.html | 200 | public-evidence.md、references.md |
| https://nginx.org/en/download.html | 200 | public-evidence.md、references.md |
| https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf | 200 | public-evidence.md |
| https://openapi-generator.tech/docs/installation/ | 200 | public-evidence.md、references.md |
| https://prometheus.io/docs/prometheus/latest/configuration/configuration/ | 200 | public-evidence.md、references.md |
| https://prometheus.io/docs/prometheus/latest/getting_started/ | 200 | public-evidence.md、references.md |
| https://protobuf.dev/editions/overview/ | 200 | public-evidence.md、references.md |
| https://protobuf.dev/installation/ | 200 | public-evidence.md、references.md |
| https://protobuf.dev/programming-guides/proto3/ | 200 | public-evidence.md、references.md |
| https://pypi.org/project/semgrep/json | 200 | public-evidence.md、references.md |
| https://pypi.org/pypi/import-linter/json | 200 | public-evidence.md、references.md |
| https://pypi.org/pypi/langchain/json | 200 | public-evidence.md、references.md |
| https://pypi.org/pypi/semgrep/json | 200 | public-evidence.md、references.md |
| https://pypi.org/pypi/sentry-sdk/json | 200 | public-evidence.md、references.md |
| https://raw.githubusercontent.com/aquasecurity/trivy/main/docs/guide/configuration/filtering.md | 200 | public-evidence.md、references.md |
| https://raw.githubusercontent.com/aquasecurity/trivy/main/docs/guide/configuration/others.md | 200 | public-evidence.md、references.md |
| https://raw.githubusercontent.com/aquasecurity/trivy/main/docs/guide/scanner/vulnerability.md | 200 | public-evidence.md、references.md |
| https://raw.githubusercontent.com/aquasecurity/trivy/main/pkg/flag/global_flags.go | 200 | public-evidence.md、references.md |
| https://raw.githubusercontent.com/chromium/chromium/main/docs/code_review_owners.md | 200 | public-evidence.md |
| https://raw.githubusercontent.com/chromium/chromium/main/docs/code_reviews.md | 200 | public-evidence.md |
| https://raw.githubusercontent.com/chromium/chromium/main/docs/contributing.md | 200 | public-evidence.md |
| https://raw.githubusercontent.com/chromium/chromium/main/docs/gardener.md | 200 | public-evidence.md |
| https://raw.githubusercontent.com/chromium/chromium/main/docs/process/merge_request.md | 200 | public-evidence.md |
| https://raw.githubusercontent.com/chromium/chromium/main/docs/process/priorities_slo.md | 200 | public-evidence.md |
| https://raw.githubusercontent.com/chromium/chromium/main/docs/process/release_blockers.md | 200 | public-evidence.md |
| https://raw.githubusercontent.com/chromium/chromium/main/docs/process/release_cycle.md | 200 | public-evidence.md |
| https://raw.githubusercontent.com/getsentry/sentry-cli/master/src/commands/info.rs | 200 | public-evidence.md、references.md |
| https://raw.githubusercontent.com/seddonym/import-linter/main/src/importlinter/application/rendering.py | 200 | public-evidence.md、references.md |
| https://raw.githubusercontent.com/seddonym/import-linter/main/src/importlinter/cli.py | 200 | public-evidence.md、references.md |
| https://raw.githubusercontent.com/semgrep/semgrep/develop/README.md | 200 | public-evidence.md、references.md |
| https://raw.githubusercontent.com/semgrep/semgrep/develop/cli/src/semgrep/commands/scan.py | 200 | public-evidence.md、references.md |
| https://raw.githubusercontent.com/semgrep/semgrep/develop/cli/src/semgrep/error.py | 200 | public-evidence.md、references.md |
| https://raw.githubusercontent.com/semgrep/semgrep/develop/cli/src/semgrep/output.py | 200 | public-evidence.md、references.md |
| https://redis.io/docs/latest/develop/reference/eviction/ | 200 | public-evidence.md、references.md |
| https://spec.openapis.org/oas/v3.1.1.html | 200 | public-evidence.md、references.md |
| https://storage.googleapis.com/deepmind-media/gemini/gemini_1_report.pdf | 200 | public-evidence.md |
| https://www.chromium.org/chromium-os/developer-library/reference/release/understanding-chromeos-releases/ | 200 | public-evidence.md |
| https://www.cidrdb.org/cidr2011/Papers/CIDR11_Paper32.pdf | 200 | public-evidence.md |
| https://www.nist.gov/itl/ai-risk-management-framework | 200 | manuscript/ch01-这本书是什么.md、manuscript/ch29-第24章-AI评审与幻觉处理.md、manuscript/ch30-第25章-文档ADR-RFC-设计令牌治理.md、manuscript/ch41-附录J-AI系统工程.md、public-evidence.md、references.md |
| https://www.openapis.org/ | 200 | public-evidence.md、references.md |
| https://www.vldb.org/pvldb/vol6/p1068-shute.pdf | 200 | public-evidence.md |

```text
[枚举] docs/**/*.md 围栏外去重 URL 96 条：内网／示意 4 条不测，实测 92 条
  [未测·示意] http://$entry
  [未测·示意] http://backend
  [未测·示意] http://backend/
  [未测·示意] http://localhost:9090/api/v1/alerts
[读数] 实测 92 条：200 = 90；死链(404/410/5xx) = 0；其他非 200 = 0；本机不可达 = 2；200 但经重定向 = 7；首跑超时、重跑才回 200 = 0
  [本机不可达] https://chromium.googlesource.com/chromium/src/+/main/docs/ → 首跑 URLError: <urlopen error [Errno 101] Network is un ／ 重跑 URLError: <urlopen error [Errno 101] Network is un
  [本机不可达] https://cloud.google.com/resources/content/dora-roi-of-ai-assisted-software-development → 首跑 URLError: <urlopen error [Errno 101] Network is un ／ 重跑 URLError: <urlopen error [Errno 101] Network is un
  [重定向] https://book.getfoundry.sh/ → https://www.getfoundry.sh/
  [重定向] https://book.getfoundry.sh/forge/tests → https://www.getfoundry.sh/forge/testing
  [重定向] https://book.getfoundry.sh/reference/anvil/anvil → https://www.getfoundry.sh/reference/anvil/anvil
  [重定向] https://book.getfoundry.sh/reference/config/overview → https://www.getfoundry.sh/config/reference/overview
  [重定向] https://book.getfoundry.sh/reference/forge/coverage → https://www.getfoundry.sh/reference/forge/coverage
  [重定向] https://book.getfoundry.sh/reference/forge/test → https://www.getfoundry.sh/reference/forge/test
  [重定向] https://book.getfoundry.sh/reference/versions → https://www.getfoundry.sh/reference/versions
```

**六跑之间的状态对账**（表只誊最后一跑；这一小段负责说明它和前面几跑差在哪，以及差在哪一类）：

```text
[跨跑对账] 同一批条目在六跑之间的状态（由六份日志派生，不由人记）：
  图例：. = 200 ／ X = 本机不可达 ／ ! = 其他状态。跑序：A B C D E F   条目
  .   .   .   .   X   .    https://blog.youtube/news-and-events/4-billion-paid-music-industry/
  .   X   .   .   .   .    https://blog.youtube/news-and-events/you-know-whats-cool-billion-hours/
  .   .   .   X   X   .    https://github.com
  .   .   .   X   X   .    https://github.com/aquasecurity/trivy/releases.atom
  .   .   .   X   X   .    https://github.com/foundry-rs/foundry/releases.atom
  .   .   .   X   X   .    https://github.com/oasdiff/oasdiff
  .   .   .   X   X   .    https://github.com/seddonym/import-linter
  .   .   .   X   X   .    https://github.com/semgrep/semgrep/releases.atom
  锚定条目 92 条里，六跑同状态 84 条，动过 8 条；动过的这些里，6 条同属 github.com 一族，且坏在同两跑。
```

> 本轮六跑，按发起顺序：**A** `/tmp/probeA.txt`／**B** `/tmp/probeB.txt`／**C** `/tmp/probeC2.txt`／**D** `/tmp/probeD.txt`／**E** `/tmp/probeE.txt`／**F** `/tmp/probeF.txt`。状态列誊的是 **F**（最后一跑）。跑与跑之间允许出现的差别只有两处：一是「出现在」那一列每条都会多出 `public-evidence.md` 这个文件名（表本身在页上，必然结果，不是漏数）；二是状态列随时刻动——动了哪几条由上面那段对账逐条列，本节不手抄。另外 `/tmp/probeC2.txt` 这个文件名带 2：C 那一跑先发起过一次，输出被自己的重跑盖掉（违反本轮立的「日志不可被重跑覆盖」那条，事故与成因记在 DIAGNOSIS 第十七轮）。**读数跟着探针的版本走**：D 之前探针按 URL 字典序排队，之后改成按主机轮转，所以六跑不是同一把尺的六次读数，而是两把尺（见下面第五件事）。F 之后本节还改过字，但改的都是不含地址的说明文字——用 `python3 scripts/probe_external_links.py --enumerate-only` 复核过：它打出的前五行与 F 日志的前五行相等，也就是这一跑的地址面在 F 之后没有变过。

**分档与处置**（这一小节是把上面那条命令打印的读数折成能行动的四件事，不另计一次数）：

1. **真死链与"我这网络不通"要分开记账。** 只有 404／410／5xx 判死链，探针为此退出 1；"网络不可达"不判死，
   因为它随读者所在网络变，不随本书的字节变。本机的不可达面在第十七轮实测包括：`chromium.googlesource.com`（E14 的原始站，
   改走同源 GitHub 镜像逐份取回）、`cloud.google.com`（E7 的出版方页面，正文与 references 一律引用可直连的 DORA 站内地址）。
   **上一版把后者定性成"反爬拦截（浏览器 403）"，本轮同一地址是本机路由层不可达**——同一条地址两次给出不同成因，
   所以这一格只登记读数与处置，不再给"资源本身在线与否"下断言；能下的断言只有一句：本书不依赖它。
2. **靠重定向回来的 200 是引用正在腐烂的读数。** `book.getfoundry.sh` 整站在搬迁（本轮该域下每条都 301 到 `www.getfoundry.sh`，
   其中 `/forge/tests` 落点已经改名成 `/forge/testing`），而案例三那张 B 档卡与 references 的出处表抄的是旧域；
   `github.com/returntocorp/semgrep/releases.atom` 也靠重定向到 `semgrep/semgrep`。Semgrep 这一条本轮已改写成现组织路径
   （与先前 `Tufin/oasdiff` 那次同一处置）。Foundry 的域**先不改**：卡里逐字引的是 2026-09-24 从旧域页面取回的正文，
   改链接等于改出处，要么整张卡重取要么留着旧域并知道它在漂——这一轮选后者，把形状登记在这里。
3. **「取不到」里有一部分是时刻，不是性质。** 本轮有两条首跑超时、重跑才回 200（`blog.youtube` 的一条、Foundry 配置总览那条），
   这正是 2026-09-24 那一版把三条 `github.com` HTML 页归因成"GitHub 对本机慢"的地方——本轮这几条直连 200。
   所以探针把"首跑失败、重跑成功"单独打一档，不许并进"一次通过"。
4. **目录型链接在 raw 通道上一定是 404。** GitHub 的 raw 只给文件不给目录列表，所以"镜像目录 URL ＋ 括号里列文件名"那种写法
   点开的是一条 404。E14 本轮改成八个文件各一条全链接。**这条判据可以机检**（凡是"以 `/` 结尾且落在 raw 域"的引用直连必 404），
   本轮先登记为未立闸的轴，配法与假阳对照写法同第八节末尾那条。

> **可达面不等于结论**：这一张表量的是"这台机器今天能不能点开"，不是"这条陈述真不真"。
> 每条陈述的逐字原文与取回通道在上方各 E 条目里；读者所在网络若比本机宽（能通 `sre.google`、`research.google`），
> 会读到比本书更宽的材料——那不是本档案的结论错，是可达面不同。对照案第 8.3 节把同一句话写成了给读者的第三步核验。

## 与四案例的边界

> 全书现在有两类案例，证据种类不同，所以边界要分两栏写。四虚构案（案例一至案例四）是**自洽虚构**的脱敏示范，数字来自本书自己的清单；对照案（案例五）是**实名、只引公开文献**的对照材料，没有叙述者、不进时间线、不进角色卡、不进数字清单，也不发明事故编号。两边不许互相借证据，也不许并进同一张等权对照表。

| 可以 | 不可以 |
|---|---|
| 用 E1–E6 支撑「为什么要治理、度量什么、如何写 ADR」 | 用外部报告「证明」某虚构事故的具体金额 |
| 在理论章「公开参照」小节引用 | 把厂商营销数字写成行业唯一事实 |
| 对照 NIST 四功能与本书机制 | 宣称本书四案例「来自真实公司」 |
| 用 E8–E28 支撑对照案的每一条陈述，并在节末点名条目号 | 把对照案写成访谈、内部材料或一手数据（本书没有接触过其中任何一件） |
| 在对照案里明说哪些业务线公开材料没给那一格 | 用邻近业务线的数字凑出空白格，或挂一个 `[待核实]` 把推测留在句子里 |
| 用对照案反证本书机制的口径缺陷（正文第七节干这件事） | 把对照案与四个虚构案混进同一张等权对照表——两边的证据种类不同，一比就把虚构案升格成事实 |
| 引 Chromium 公开流程文档作为"同一工程文化里可核的那一份" | 把 Chromium 的门禁当成 Google 全集团产品线的门禁 |

**对照案的读法（一句提醒）**：档案里 E8–E12 与 E20–E28 来自**同一本书的公开免费在线章节**（《Software Engineering at Google》第 10 到 25 章，E28 与 E10 同页不同段），E13 是另一套公开的工程实践规范页，E14 是 Chromium 的公开流程文档，E15 与 E16 是会议论文，E17 到 E19 是官方博客与产品文档。同源的坏处明显——那十几条共享同一批作者的口径与时点（多为 2019–2020 年写作时点），**同一来源的不同章节不算互相印证**；好处也明显——每条都能被读者点开、逐字比对本机落盘的字节。正文引用一律带条目号，读者随时可以把正文句子和这一页的引文对齐。

## 建议引用格式（正文）

```text
据 DORA 2025《State of AI-assisted Software Development》，AI 主要扮演放大器角色，
最大回报来自对底层组织系统的投入（https://dora.dev/research/2025/dora-report/）。
```

```text
GitHub 与 Accenture 2024-05-13 公布的企业 RCT 报告称人均 PR 提升 8.69%、
合并率提升 15%（厂商研究，https://github.blog/...）。
```
