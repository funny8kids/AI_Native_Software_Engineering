# FIGURE_LIST — 全书配图清单（与实物一致）

> 规则：技术图 = Mermaid；封面/卷首/头图 = 抽象位图（无文字）。可读对象 ≤12（定义见 `BOOK_SPEC.md` §9）。术语见 `GLOSSARY.md`。
> **本表的图数、图号、图型三列由 `python3 scripts/check_figures.py --print` 从手稿实测生成，不手写。**
> 最近一次刷新：2026-09-24。实测结论：**107 张技术图**（手稿 43 个文件 104 张 + 站点页 3 张），**107/107 通过浏览器端 `mermaid.parse` 全量校验，0 语法错误**；守卫同时判定每章 2–5 张、图号按阅读顺序递增、图注与图一一对应、节点上限全部达标。
> 配套：`python3 scripts/check_links.py`（**要先起本地服务**：`python3 -m http.server 8080 --directory docs`——它把每条本地引用换成真实 HTTP 请求，所以没有服务就没有判据）→ 去重后的全部本地引用 URL 均 HTTP 200、死链 = 0；**引用条数随正文增删而变，以命令自己打印的那一行为准**，这里不写死。它的失败方向也记一笔：服务没起时它把**全部**引用报成死链并退出 1，不会把"取不到"洗成"通过"。已用两条假链做过变异自检，确认守卫会红。图在窄屏是否被缩糊由第六条守卫 `check_mobile.py --report` 逐图给 `viewBox / 渲染宽 / 缩放`；**图上的字能不能读清、以及宽图宽表有没有"还能滚"的暗示，由第七条守卫 `check_legibility.py` 把住**——它按每张图自己的 `viewBox` 与自然字号解出所需宽度，判据是「任意视口下有效字号 ≥11px」+「每个需横向滚动的容器都挂了随 `scrollLeft` 更新的边缘暗示，且暗示层不吃点击」，`--report` 逐图给 `自然字号 / 有效字号 / 缩放`，`--screenshot DIR` 出逐图截图。

## 每文件图数（实测）

| 文件 | 图 | 图号 | 图型 |
|---|---|---|---|
| README（书稿总览，非章） | 1 | TOC-1 | flowchart |
| ch01-这本书是什么 | 2 | 0-1、0-2 | flowchart |
| ch02-90天总路线图 | 3 | R-1、R-2、R-3 | flowchart/gantt |
| ch03-案例时间线 | 2 | 00-1、00-2 | flowchart/gantt |
| ch04-角色设定卡 | 3 | R-1、R-2、R-3 | flowchart |
| ch05-数字清单 | 2 | N-1、N-2 | flowchart |
| ch06-第1章-AI原生不是让AI写代码 | 3 | 1-1、1-2、1-3 | flowchart |
| ch07-第2章-人在回路 | 3 | 2-1、2-2、2-3 | flowchart/state |
| ch08-第3章-人机分工 | 2 | 3-1、3-2 | flowchart/sequence |
| ch09-第4章-AI原生工程栈 | 3 | 4-1、4-2、4-3 | flowchart/gantt |
| ch10-第5章-大规模考古画图 | 3 | 5-1、5-2、5-3 | flowchart |
| ch11-第6章-跨团队依赖分析 | 2 | 6-1、6-2 | flowchart |
| ch12-第7章-AI读懂祖传代码 | 2 | 7-1、7-2 | flowchart/state |
| ch13-第8章-目标架构 | 2 | 8-1、8-2 | flowchart |
| ch14-第9章-契约先行 | 3 | 9-1、9-2、9-3 | flowchart |
| ch15-第10章-边界变测试 | 2 | 10-1、10-2 | flowchart |
| ch16-第11章-留缝 | 3 | 11-1、11-2、11-3 | flowchart |
| ch17-第12章-数据与日志分家 | 2 | 12-1、12-2 | flowchart |
| ch18-第13章-单文件API到router+nginx | 2 | 13-1、13-2 | flowchart |
| ch19-第14章-Python立包与迁移 | 2 | 14-1、14-2 | flowchart/state |
| ch20-第15章-前端解耦多端设计系统 | 2 | 15-1、15-2 | flowchart |
| ch21-第16章-聊天功能 | 2 | 16-1、16-2 | flowchart/sequence |
| ch22-第17章-多端BFF | 2 | 17-1、17-2 | flowchart |
| ch23-第18章-亿级流量 | 2 | 18-1、18-2 | flowchart/state |
| ch24-第19章-五层门禁 | 3 | 19-1、19-2、19-3 | flowchart/state |
| ch25-第20章-风控不可绕过 | 3 | 20-1、20-2、20-3 | flowchart/sequence |
| ch26-第21章-对账灰度回滚监控 | 3 | 21-1、21-2、21-3 | flowchart/sequence |
| ch27-第22章-安全合规公开仓库 | 2 | 22-1、22-2 | flowchart/sequence |
| ch28-第23章-提示词工程与归档 | 3 | 23-1、23-2、23-3 | flowchart |
| ch29-第24章-AI评审与幻觉处理 | 3 | 24-1、24-2、24-3 | flowchart/sequence |
| ch30-第25章-文档ADR-RFC-设计令牌治理 | 2 | 25-1、25-2 | flowchart/state |
| ch31-第26章-组织治理 | 2 | 26-1、26-2 | flowchart/state |
| ch32-第27章-契约治理 | 3 | 27-1、27-2、27-3 | flowchart/sequence/state |
| ch33-第28章-灰度发布 | 3 | 28-1、28-2、28-3 | flowchart/sequence/state |
| ch34-案例一-300人电商平台 | 3 | C1-1、C1-2、C1-3 | flowchart |
| ch35-案例二-海星交易所 | 3 | C2-1、C2-2、C2-3 | flowchart/sequence |
| ch36-案例三-暗流资本 | 3 | C3-1、C3-2、C3-3 | flowchart/sequence |
| ch37-案例四-守夜人科技 | 3 | C4-1、C4-2、C4-3 | flowchart/mindmap/sequence |
| ch38-第33章-四案例交叉启示 | 2 | 33-1、33-2 | flowchart/mindmap |
| ch39-附录A-提示词库骨架 | 2 | A-1、A-2 | flowchart/state |
| ch40-附录I-契约治理规范模板 | 2 | I-1、I-2 | flowchart |
| ch41-附录J-AI系统工程 | 2 | J-1、J-2 | flowchart |
| ch42-附录K-一线最小实践包 | 2 | K-1、K-2 | flowchart/sequence |
| README（站点页） | 2 | 0-1、0-2 | flowchart/mindmap |
| guide（站点页） | 1 | G-1 | flowchart |

42 个 `chNN-` 文件全部落在 2–3 张区间，无一例外。`manuscript/README.md` 是书稿总览页（1 张骨架图），九个 `part-*.md` 卷首页用位图艺术开场——两者都不是章，不参与「2–5 张」判定，由守卫按同一口径跳过。

## 附录为什么不豁免（2026-09-24 更正）

本清单旧版写着「附录 A / I / K 为纯文本模板包，按 STYLE_GUIDE 豁免配图」。**`BOOK_SPEC.md` §9 从来没有豁免条款**，那句是清单自己造的，属于元数据比实物好看了。现已补齐：

- 附录 A：A-1 条目生命周期（由文件自带 `status` 字段推导）、A-2 按失灵模式反查提示词（由自带分类速查表推导）。
- 附录 I：I-1 契约变更分级流程、I-2 五端同步与拦截（由 §5–§6 的条款推导）。
- 附录 J：J-1 AI 系统最小面、J-2 评估飞轮。
- 附录 K：K-1 一线日常最小闭环、K-2 事故当夜动作顺序（sequenceDiagram）。
- 前置三件套同步补图：ch03 时间线加 00-2（失灵→接手→制度化的统一形状），ch04 角色卡拆出 R-1/R-2 并加 R-3（对话指纹生成链），ch05 数字清单加 N-1（单一事实源）与 N-2（收益与代价必须成对）。

**所有新图只重画各文件自己已有的表与条款，没有引入任何新数字**；节点数、图号与图注由守卫持续把关。

## 旧版超 12 个可读对象的四张图（已收口）

| 图 | 原来 | 现在 |
|---|---|---|
| 书稿总览 TOC-1 | 13 个卡片（附录被画成主干一环） | 12——附录移出主干链，改写进结论句 |
| ch04 图 R-1 | 16 个角色卡片挤在一张 | 拆成 R-1（案例一、二）+ R-2（案例三、四），各 8 卡 |
| ch07 图 2-1 | 14（六失灵 + 中心枢纽 + 六接管） | 12——删掉中心枢纽，改为两栏一一连线，正好对上「一一对应」这句话 |
| ch24 图 19-2 | 计数曾误报 13 | 计数口径修正后为 12（subgraph 标题与 `style` 行不算卡片） |

## 位图（无文字，14 张实际引用 + 1 张历史遗留）

| 用途 | 路径 | 状态 |
|---|---|---|
| 封面艺术（_coverpage） | `docs/assets/cover-ainse.webp` | 完成 |
| （旧版封面，已无引用） | `docs/assets/cover.webp` | 遗留，待作者决定是否删 |
| 案例一～四头图 | `docs/assets/case-{ecommerce,exchange,quant,agent}.webp` | 完成 |
| 九部分卷首艺术 | `docs/assets/part1-cognition … part9-convergence.webp`（9 张） | 完成 |

## 题图（手工版画 SVG，9 张，共 164.9 KB）

九个**部分开卷章**各一张，母题不重复。体积逐张由 `ls` 实测，不是估的。

| 章 | 母题 | 路径 | 体积 |
|---|---|---|---|
| ch06 第 1 章 | 筛子 | `assets/plates/ch06-sieve.svg` | 38.9 KB |
| ch10 第 5 章 | 探沟剖面 | `assets/plates/ch10-strata.svg` | 13.5 KB |
| ch13 第 8 章 | 等高线 | `assets/plates/ch13-contour.svg` | 20.4 KB |
| ch17 第 12 章 | 织机 | `assets/plates/ch17-loom.svg` | 23.0 KB |
| ch21 第 16 章 | 桁架 | `assets/plates/ch21-truss.svg` | 15.3 KB |
| ch24 第 19 章 | 水闸 | `assets/plates/ch24-gate.svg` | 10.5 KB |
| ch28 第 23 章 | 卡尺 | `assets/plates/ch28-caliper.svg` | 13.7 KB |
| ch33 第 28 章 | 溢洪道 | `assets/plates/ch33-spillway.svg` | 10.5 KB |
| ch38 第 33 章 | 回波屏 | `assets/plates/ch38-radar.svg` | 19.2 KB |

四条不是顺手写下的取舍：

1. **为什么不是位图**：本机图像生成接口返回 403（配额），而"先冷生成再后期调色"要欠两笔债——色板对不上 token、放大即糊。于是改由 `scripts/plate_engine.py` 现读 `theme.css` 的 `--c-plate*` 令牌画矢量：板外色在构造上不可能出现，任意视口不糊，整批 164.9 KB。
2. **为什么只有 9 张**：42 章 ÷ 9 个母题会读成贴纸。题图只压在部分开卷章，与"部分"这一层结构对齐。
3. **描边按页面实际宽度预放大 1.792×**：CDP 量 `.chapter-plate img` 的 `getBoundingClientRect().width`，1280 与 1440 两档同为 **670px**（正文栏有 max-width，视口加宽不加宽图），390 档 **340px**。不预放大的第一版在 1280 截图里 0.8 档发丝线只有 0.447 CSS px，整张像蒙了层灰——这就是"不够高级"的具体形状。改口径要连这条读数一起改：`plate_engine.py` 顶部 `DISPLAY_W`。
4. **覆盖边界（谁看不见它）**：题图经 `<img>` 引用，第八条配色闸的 DOM 对比度读数**看不见 SVG 内部**——它量的是页面，不是纸里。题图的颜色纪律由引擎自己的 `check()` 把住（板外色 / XML 解析失败 / 含 `<text>` 三种都判红），窄档可读性由 `check_palette.py --screenshot` 的 390 档截图人工复核：340×132 的版面上，最细一档落回 0.4px 级，题图是论点不是数据，因此不做横向滚动，接受细线变淡。

## 自托管字体（零 CDN）

`scripts/build_fonts.py` 从本机 Noto CJK TTC 的 SC 面（face 2）子集化，charset 覆盖 docs 全部 md/html 实际用字（1,903 字）：
`docs/vendor/fonts/noto-serif-sc-{400,700}.woff2`（约 320/335 KB）+ `noto-sans-sc-{400,700}.woff2`（约 256/260 KB）。

## 图注模板

````markdown
```mermaid
flowchart LR
  ...
```

**图 N-M｜标题** — 一句话结论，直接可写进 PPT。
````

## 复核命令

```bash
python3 scripts/check_figures.py                      # 图数 / 图号 / 图注 / 节点上限
python3 scripts/check_links.py                        # 第二条：本地引用逐条发 HTTP（自带临时服务器）
python3 scripts/check_markdown.py                     # 第三条：围栏 / 裸围栏 / HTML 块吞语法 / 双副本一致
python3 scripts/check_overlays.py                     # 第四条：整屏遮罩的层叠语义闸（静态）
python3 scripts/check_interactions.py                 # 第五条：命中测试 + 真实点击（62 路由 × 1280/390）
python3 scripts/check_mobile.py                       # 第六条：390 窄屏几何闸（顶栏折行 / 图缩糊 / 居中溢出）
python3 scripts/check_mobile.py --report              # 逐图输出 viewBox / 渲染宽 / 缩放（本表的图数不看缩放）
python3 scripts/check_legibility.py                   # 第七条：有效字号地板 + 滚动暗示覆盖率（真浏览器、真点主题按钮）
python3 scripts/check_legibility.py --report          # 逐图输出 自然字号 / 有效字号 / 缩放
python3 scripts/check_legibility.py --mutate          # 第七条的变异自检 A–E：每条判据各自要能报红
python3 scripts/check_palette.py                      # 第八条：token 纪律 + 逐层 alpha 合成后的对比度（真浏览器、真点 #btn-theme）
python3 scripts/check_palette.py --mutate             # 第八条的变异自检：七条判据各自要能报红
python3 scripts/check_palette.py --screenshot DIR     # 1280/1440/390 × 浅/深 逐页截图（题图与配色改动后逐项复核用这条）
python3 scripts/plate_engine.py --check               # 题图引擎自检：板外色 / XML 解析 / 含 <text> 三种都判红
# 浏览器端：对 107 个围栏逐个 mermaid.parse（本表刷新时 107/107 通过）
```

## 下一轮

1. `assets/cover.webp` 是无引用的旧封面——作者确认后删除。
2. 图号前缀目前混用（`0-1` / `00-1` / `R-1` / `N-1` / `C1-1`），语义清楚但不齐整；若要统一需要一次正文引用同步改。
3. 附录 A 可再加「按提示词反查失灵模式」的反向索引表。
4. 外部公开引用的年份与措辞随 `references.md` 台账季度复核（17 条外链逐条读数见 `public-evidence.md`）。
