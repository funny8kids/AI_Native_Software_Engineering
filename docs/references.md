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

## 工具落地卡的出处（2026-09-24 本机逐条复核）

第 9 章 9.5e 与第 13 章「工具落地卡」里的版本口径与官方表述，逐条对应下表。**每行右边的读数是当天从本机取回的，不是转述**：状态码来自直连请求，日期来自 GitHub Releases API 的 `published_at` 字段。

| 卡内断言 | 出处 | 本轮读数 |
|---|---|---|
| `openapi` / `info.title` / `info.version` 为必填，`paths` 在 3.1 起不再必填 | OpenAPI 3.1.1 规范正文（Fixed Fields 表） | 200 · https://spec.openapis.org/oas/v3.1.1.html |
| 3.1.1 发布于 2024-10-24；3.1.2 与 3.2.0 同在 2025-09-19；3.2.1 在 2026-09-10 | OpenAPI-Specification Releases API | 200 · https://api.github.com/repos/OAI/OpenAPI-Specification/releases |
| openapi-generator 7.25.0 发布于 2026-08-24；`java` 需在 PATH、最低 JDK 11 | openapi-generator Releases API + 官方 Installation 页 | 200 · https://api.github.com/repos/OpenAPITools/openapi-generator/releases/latest ｜ https://openapi-generator.tech/docs/installation/ |
| `.proto` 不要与其他语言源码同目录；`syntax` 须是第一个非空非注释行；字段号上线后不可改 | Language Guide (proto 3) | 200 · https://protobuf.dev/programming-guides/proto3/ |
| 语言口径 proto3 或 `edition = "2023"` | Protobuf Editions Overview | 200 · https://protobuf.dev/editions/overview/ |
| protoc 36.2 发布于 2026-09-17；按 `protoc-<版本>-<os>-<arch>.zip` 下载并锁版本 | protobuf Releases API + Protoc Installation | 200 · https://api.github.com/repos/protocolbuffers/protobuf/releases/latest ｜ https://protobuf.dev/installation/ |
| nginx stable 1.30.5 / mainline 1.31.6 | 官方 download 页（页面内 `nginx-x.y.z.tar.gz` 文件名直读） | 200 · https://nginx.org/en/download.html |
| conf 路径由编译期 `--conf-path` 决定，源码默认 `prefix/conf/nginx.conf` | 官方 configure 文档 | 200 · https://nginx.org/en/docs/configure.html |
| `reload` = 给 master 发 HUP，文档只描述信号语义、不承诺终端输出 | 官方 control 文档 | 200 · https://nginx.org/en/docs/control.html |
| `proxy_set_header Host / X-Real-IP / X-Forwarded-For / X-Forwarded-Proto` 这组示例形状 | 官方 proxy 模块文档 | 200 · https://nginx.org/en/docs/http/ngx_http_proxy_module.html |

**取不到读数的地址照实登记**：`github.com` 的三个 HTML 页面（两份 releases 页与一份 blob 页）本机读取超时，与首轮 import-linter 那次是同一现象（GitHub 的 HTML 页对本机慢，API 与站内文档正常）。所以卡里的版本日期一律按上表 API 读数；卡里那些**报错字符串不来自网页转述**，而是在指定版本上真实执行后的输出，复现路径写在卡内。

> 一条口径：**外部文档只背书"工具自己怎么表现"，不背书本书案例的任何数字。** 案例的数字唯一来源仍是 `manuscript/ch05-数字清单.md`。

## B 档卡的出处（2026-09-24 本机逐条复验，工具未安装、命令未复跑）

第 4 章台账把工具卡分成 A（本机实跑）/ B（文档或源码逐字）/ C（不出卡）三档。**A 档的读数在上一节**。本节登记 B 档每一行的取数地址与当日读数——`raw.githubusercontent.com` 走的是**项目源码与文档 markdown 本身**，所以「退出码常量」「摘要行字面量」这类断言核对的是代码而不是网页转述。

| 卡内断言 | 出处 | 本轮读数（2026-09-24） |
|---|---|---|
| langchain 当前 1.4.2、发布于 2026-09-18；langchain-core 1.6.4 | PyPI 项目 JSON（`info.version` / `releases[].upload_time`） | 200 · https://pypi.org/pypi/langchain/json |
| `timeout` 定义与"默认重试 6 次（网络错误 / 429 / 5xx）"两句 | LangChain 官方 Models 文档 | 200 · https://docs.langchain.com/oss/python/langchain/models |
| import-linter 当前 2.15 | PyPI 项目 JSON | 200 · https://pypi.org/pypi/import-linter/json |
| 汇总行 `Contracts: {kept} kept, {broken} broken.`、每条契约 `KEPT` / `BROKEN` | 源码 `application/rendering.py`（main 分支原文） | 200 · https://raw.githubusercontent.com/seddonym/import-linter/main/src/importlinter/application/rendering.py |
| 退出码只有 `EXIT_STATUS_SUCCESS = 0` / `EXIT_STATUS_ERROR = 1` | 源码 `cli.py` | 200 · https://raw.githubusercontent.com/seddonym/import-linter/main/src/importlinter/cli.py |
| semgrep 当前 1.178.0 | PyPI 项目 JSON | 200 · https://pypi.org/project/semgrep/json |
| 摘要四行 ` • Findings: N (M blocking)` / `Rules run` / `Targets scanned` / `Parsed lines`，末行 `Ran N rules on M files: K findings.` | 源码 `cli/src/semgrep/output.py`（develop 分支） | 200 · https://raw.githubusercontent.com/semgrep/semgrep/develop/cli/src/semgrep/output.py |
| 退出码常量 `OK=0 / FINDINGS=1 / FATAL=2 / MISSING_CONFIG=7 / INVALID_LANGUAGE=8` | 源码 `cli/src/semgrep/error.py` | 200 · https://raw.githubusercontent.com/semgrep/semgrep/develop/cli/src/semgrep/error.py |
| `--error/--no-error` 映射 `error_on_findings`（默认非真）；不传 `--config` 时回退 `["auto"]` | 源码 `commands/scan.py` | 200 · https://raw.githubusercontent.com/semgrep/semgrep/develop/cli/src/semgrep/commands/scan.py |
| 社区版"只能在单个函数或文件边界内分析、会漏掉大量真阳性" | 官方 README 自述 | 200 · https://raw.githubusercontent.com/semgrep/semgrep/develop/README.md |
| 配置默认名 `trivy.yaml`；豁免文件常量 `DefaultIgnoreFile = ".trivyignore"` | 源码 `pkg/flag/global_flags.go`、`pkg/result/filter.go` | 200 · https://raw.githubusercontent.com/aquasecurity/trivy/main/pkg/flag/global_flags.go |
| "默认即使查出问题也退出 0"、`Total: 1 (UNKNOWN: 0, LOW: 0, MEDIUM: 1, HIGH: 0, CRITICAL: 0)`、`Detecting Alpine vulnerabilities...`、表头 `LIBRARY / VULNERABILITY ID / …` | 官方文档 markdown `docs/guide/configuration/others.md` | 200 · https://raw.githubusercontent.com/aquasecurity/trivy/main/docs/guide/configuration/others.md |
| `.trivyignore` 的 `exp:` 到期日写法；`.trivyignore.yaml` 挂 EXPERIMENTAL 且必须显式 `--ignorefile` | `docs/guide/configuration/filtering.md` | 200 · https://raw.githubusercontent.com/aquasecurity/trivy/main/docs/guide/configuration/filtering.md |
| "优先精确、可能接受漏报"；版本不确定（`>=3.0`）的包通常跳过检测 | `docs/guide/scanner/vulnerability.md` | 200 · https://raw.githubusercontent.com/aquasecurity/trivy/main/docs/guide/scanner/vulnerability.md |
| Prometheus 示例行 `scrape_interval: 15s`、`--config.file=prometheus.yml`、`/api/v1/alerts` 响应含 `"state": "firing"` 与 `alertname` | 官方 getting started / querying API 页 | 200 · https://prometheus.io/docs/prometheus/latest/getting_started/ ｜ .../querying/api/ |
| `scrape_interval` 的 schema 缺省 `default = 1m` | 官方 configuration 页 | 200 · https://prometheus.io/docs/prometheus/latest/configuration/configuration/ |
| Kafka `acks=all` 为"最强保证"、幂等要求 `acks` 为 `all`、冲突时抛 `ConfigException`、重试受 `delivery.timeout.ms` 约束 | 官方 4.1 Producer Configs | 200 · https://kafka.apache.org/41/configuration/producer-configs/ |
| Redis `allkeys-lru` 是"没有特别理由时的好缺省" | 官方内存淘汰文档 | 200 · https://redis.io/docs/latest/develop/reference/eviction/ |
| Grafana「provisioned 面板在 UI 里保存会弹 Cannot save provisioned dashboard」；Docker 缺省路径 `GF_PATHS_PROVISIONING=/etc/grafana/provisioning` | 官方 Provisioning 与 Configure Docker 页 | 200 · https://grafana.com/docs/grafana/latest/administration/provisioning/ ｜ .../setup-grafana/configure-docker/ |
| Foundry 稳定版 `v1.8.2`（2026-09-15） | 官方 releases atom（**不是** `api.github.com`，该主机本轮 403） | 200 · https://github.com/foundry-rs/foundry/releases.atom |
| 文档站自身版本：`forge / cast / chisel 1.8.0-nightly`（commit `fa8b5fc2`，2026-08-04 构建）、`anvil 1.8.2-dev`（2026-09-13 构建）；页面对这版的用途说明"区分文档漂移与某个 release 的实际行为" | 官方 CLI reference versions 页 | 200 · https://book.getfoundry.sh/reference/versions |
| `forge test` 成功/失败输出全部字面量（`Ran 2 tests for test/Counter.t.sol:CounterTest`、`Suite result: ok. 2 passed; 0 failed; 0 skipped; …`、`Ran 1 test suite …: 2 tests passed, 0 failed, 0 skipped (2 total tests)`、`[FAIL: Unauthorized()]`、`Backtrace: at Vault.withdraw`）；`[fuzz] runs/max_test_rejects/seed` 块；"256 by default"；call isolation 默认开启与 warm/cold 警示；`--fork-block-number`「Pin to a specific block for reproducible tests」；符号化测试「currently an MVP」 | 官方 Testing 指南（页面 `dateModified 2026-09-19`） | 200 · https://book.getfoundry.sh/forge/tests |
| `forge test` 完整选项块中**无** `--coverage`；`--allow-failure` 逐字"Exit with code 0 even if a test fails"（含 `FOUNDRY_ALLOW_FAILURE`）；`--fail-fast`、`--gas-report`、`--junit`、`-v/--verbosity` 五档语义 | 官方 CLI reference（自动生成自 `forge test --help`） | 200 · https://book.getfoundry.sh/reference/forge/test |
| `coverage  Generate coverage reports` 是独立子命令；`--report` 取值 `summary/lcov/debug/bytecode/attribution`、缺省 `summary`、回退 `[profile.<name>.coverage] report`；`--include-libs`、`--exclude-tests` | 官方 CLI reference（`forge coverage --help`） | 200 · https://book.getfoundry.sh/reference/forge/coverage |
| anvil `127.0.0.1:8545`、`--fork-url $RPC_URL (fork the latest state of a live network)`、`--block-time`、`--state state.json (load state if it exists and dump it on exit)`、`-a` 缺省 10、`--balance` 缺省 10000 | 官方 CLI reference（`anvil --help`） | 200 · https://book.getfoundry.sh/reference/anvil/anvil |
| 配置发现（cwd 向父目录 + 全局 `~/.foundry/foundry.toml`、`FOUNDRY_CONFIG` 覆盖）、profile 缺省名 `default` 且其余档继承它、优先级"内置缺省 < foundry.toml < `FOUNDRY_`/`DAPP_` 环境变量"、`forge config` 打印完全解析后的配置 | 官方 Configuration Overview 页 | 200 · https://book.getfoundry.sh/reference/config/overview |
| **Foundry 稳定版更正为 `v1.8.3`（2026-09-15T12:49:47Z），上一条 `v1.8.2` 是 2026-09-14**；本表与卡里先前那条「v1.8.2 / 09-15」是把跨条目的 `<title>`–`<updated>` 配错了对象（这个 feed 里稳定版与 Nightly 交错排列），现改为**逐 `<entry>` 切分后再配** | releases atom（逐 entry 解析） | 200 · https://github.com/foundry-rs/foundry/releases.atom |
| Trivy 最新稳定版 `v0.74.0`（2026-08-14T11:48:42Z）、上一条 `v0.73.0`（2026-08-03）——**改走 atom 后不再受 `api.github.com` 的 403 限制** | releases atom（逐 entry 解析） | 200 · https://github.com/aquasecurity/trivy/releases.atom |
| Semgrep 发布序列 `1.178.0`（2026-09-23）/`1.177.0`/`1.176.0`/`1.175.0`；与 PyPI `1.178.0`、`requires_python >=3.10` 交叉一致 | releases atom + PyPI JSON | 200 · https://github.com/returntocorp/semgrep/releases.atom ｜ https://pypi.org/pypi/semgrep/json |
| Semgrep 退出码**文档侧**码表：`0`（未用 `--error`）、`1`（用了 `--error` 且有 finding）、`2` 失败、`3` 被扫语言语法非法（仅 `--strict`）、`4` 规则 schema 里有非法 pattern、`5` 配置不是合法 YAML、`7` 配置里至少一条规则非法、`8` 不认识指定语言 ——**与源码常量在"7"上语义不一致**（源码是 `MISSING_CONFIG_EXIT_CODE = 7`），卡里并列不裁决 | 官方 CLI reference 页 Exit codes 节 | 200 · https://docs.semgrep.dev/cli-reference |
| Sentry SDK 版本线：PyPI 当前 `2.70.0`，`3.x` 只有 `3.0.0a1…a7` 预发布 ⇒ 2.x 是可抄的维护线 | PyPI 项目 JSON | 200 · https://pypi.org/pypi/sentry-sdk/json |
| `sentry-cli info` 的**文档侧只有一句用途说明、无输出样例**（逐字 "To make sure everything works you can run `sentry-cli info`…"）；`.sentryclirc` 逐字（含"向上查找 + `~/.sentryclirc` 总是加载"、"standard INI syntax"）；`export SENTRY_AUTH_TOKEN=<token>` 与 `sentry-cli login --auth-token` 两种注入形状 | 官方 CLI configuration 页 | 200 · https://docs.sentry.io/cli/configuration/ |
| `sentry-cli info` 的可 grep 行名（`Sentry Server: `、`Default Project: `、`Authentication Info:`、`  Method: `、`  User: `、`  Scopes:`、`    - `）与**无凭据时 `Method` 取值就是 `Unauthorized`** | 项目源码 `src/commands/info.rs`（master）——**出处是源码不是文档** | 200 · https://raw.githubusercontent.com/getsentry/sentry-cli/master/src/commands/info.rs |

**B 档卡里仍然没核到手的，照实留在卡面上**：`sentry-cli` 自己的版本号（本轮只核了 SDK 那条线）、`kafka-topics.sh --create --replication-factor` 的精确 flag 拼法、`redis-cli INFO` 的整行样例输出、`Prometheus /api/v1/alerts` 中 `state` 的全部取值、Grafana `/api/health` 的故障态返回、Semgrep 规则必需键表（`docs.semgrep.dev/writing-rules/*` 的这两个路径本机 404，卡里的键名仍按转述登记）、LangChain 运行后的重试日志形状（官方未给样例，卡内那一格是空的）、以及 `foundry.toml` 的目录布局键（`src` / `out` / `libs` 的精确键名与缺省值本轮未逐字核对，所以案例三那张卡里**没有**写它们）。**这些不是"暂未写全"，是"这些行你还不能信"。**

**本轮从"未核实"转成"有读数"的两件**：Trivy 的小版本（先前记的是"`api.github.com` 限流取不到"，改走 `releases.atom` 一次到位）与 Sentry 的判据行（先前判 C 档，理由是文档没有输出样例；后来从源码 `src/commands/info.rs` 取到）。**教训是取数路径，不是取数结论**：`api.github.com` 会 403、文档子页会 404/超时，而 `releases.atom` 与 `raw.githubusercontent.com` 两条路不需要鉴权也没有那层限流——**「取不到」要先怀疑口径，再落成「未核实」。**

**整件工具出不了卡的，台账里留了行**：Mythril / Slither（案例三闸门二的第 2、3 层）与 oasdiff / buf 的判据行（案例一的契约仓）——本轮取不到可核对的判据行，判 **C 档**，正文保留点名但不给配置。Sentry 已升 B 档出卡（卡在第 21 章）。

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
