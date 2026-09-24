# 《AI 原生软件工程》

<div class="home-hero">
  <p class="home-kicker">AI Native Software Engineering</p>
  <p class="home-tagline">当 AI 自己兜不住的时候，<strong>组织如何接管</strong>。</p>
  <p class="home-sub">不是 AI 的能力清单，是<strong>组织的接管清单</strong>。</p>
</div>

<div class="principle-row">
  <div class="principle-card">
    <span class="principle-num">01</span>
    <strong>契约先行</strong>
    <p>接口的事实声明先于代码；实现对不上契约仓就合不了。</p>
  </div>
  <div class="principle-card">
    <span class="principle-num">02</span>
    <strong>人在回路</strong>
    <p>AI 做可能，人做选择，人做负责。关键节点必须签字。</p>
  </div>
  <div class="principle-card">
    <span class="principle-num">03</span>
    <strong>留缝留痕</strong>
    <p>输出与生效之间永远留一层人工缝隙；每次操作可审计。</p>
  </div>
</div>

---

## 四个案例，一种共识

<div class="home-case-grid">
  <a class="case-card" href="manuscript/ch34-案例一-300人电商平台.md">
    <img src="assets/case-ecommerce.webp" alt="案例一 电商平台">
    <div class="case-card-body">
      <span class="case-badge">案例一 · 300 人</span>
      <h3>电商平台</h3>
      <p>资金对账不可漏。契约先行 + 留痕，从 Owner 名单开始。</p>
      <span class="case-cta">进入叙事 →</span>
    </div>
  </a>
  <a class="case-card" href="manuscript/ch35-案例二-海星交易所.md">
    <img src="assets/case-exchange.webp" alt="案例二 海星交易所">
    <div class="case-card-body">
      <span class="case-badge">案例二 · 2300 人</span>
      <h3>海星交易所</h3>
      <p>撮合精度不可优化。精度铁律 + 合规铁律，CI 硬拒禁区。</p>
      <span class="case-cta">进入叙事 →</span>
    </div>
  </a>
  <a class="case-card" href="manuscript/ch36-案例三-暗流资本.md">
    <img src="assets/case-quant.webp" alt="案例三 暗流资本">
    <div class="case-card-body">
      <span class="case-badge">案例三 · 32 人</span>
      <h3>暗流资本</h3>
      <p>策略意图不可篡改。四道闸门拦过拟合与不安全合约。</p>
      <span class="case-cta">进入叙事 →</span>
    </div>
  </a>
  <a class="case-card" href="manuscript/ch37-案例四-守夜人科技.md">
    <img src="assets/case-agent.webp" alt="案例四 守夜人科技">
    <div class="case-card-body">
      <span class="case-badge">案例四 · 10 人</span>
      <h3>守夜人科技</h3>
      <p>智能体边界不可越权。权限矩阵写进代码中间件。</p>
      <span class="case-cta">进入叙事 →</span>
    </div>
  </a>
</div>

> AI 把「可能」变多了，把「选择」和「负责」的重量全压到了人身上。

---

## 全书主线

```mermaid
flowchart LR
  A[意图与规格] --> B[上下文工程]
  B --> C[AI 生成与 Agent 执行]
  C --> D[自动评估]
  D --> E[人类审查]
  E --> F[部署与可观测]
  F -->|回灌约束| B
  style A fill:#f1ebde,stroke:#2f6154,color:#1e1c19
  style E fill:#fcefd3,stroke:#9d6127,color:#1e1c19
  style F fill:#e2f3df,stroke:#3e7247,color:#1e1c19
```

**图 HM-1｜AI 原生交付闭环** — 生成可以自动，生效必须过评估与人审，观测再回灌成下一轮上下文。

---

## 六种 AI 失灵模式

AI 稳定做不到的六件事——是**组织的接管清单**：

```mermaid
mindmap
  root((AI 失灵))
    不自证完整
    不跨上下文
    不验证只推断
    不留痕
    不懂组织约束
    不承担后果
```

**图 HM-2｜六种失灵** — 在哪里失灵，组织就必须在哪里站起来。

---

## 九部分地图

<div class="home-part-grid">
  <a class="home-part-card" href="manuscript/part-1-认知.md">
    <img src="assets/part1-cognition.webp" alt="第一部分卷首艺术">
    <span class="part-idx">壹</span>
    <strong>认知</strong>
    <span>AI 原生边界、人在回路、人机分工、工程栈四支柱</span>
  </a>
  <a class="home-part-card" href="manuscript/part-2-考古.md">
    <img src="assets/part2-archaeology.webp" alt="第二部分卷首艺术">
    <span class="part-idx">贰</span>
    <strong>考古</strong>
    <span>大规模仓库画图、跨团队依赖、读懂祖传代码</span>
  </a>
  <a class="home-part-card" href="manuscript/part-3-立界.md">
    <img src="assets/part3-boundaries.webp" alt="第三部分卷首艺术">
    <span class="part-idx">叁</span>
    <strong>立界</strong>
    <span>目标架构、契约先行、边界测试、留缝五步</span>
  </a>
  <a class="home-part-card" href="manuscript/part-4-重构.md">
    <img src="assets/part4-refactoring.webp" alt="第四部分卷首艺术">
    <span class="part-idx">肆</span>
    <strong>重构</strong>
    <span>数据分家、接口拆分、立包迁移、设计令牌</span>
  </a>
  <a class="home-part-card" href="manuscript/part-5-新功能.md">
    <img src="assets/part5-newgrowth.webp" alt="第五部分卷首艺术">
    <span class="part-idx">伍</span>
    <strong>新功能</strong>
    <span>聊天独立域、多端 BFF、亿级削峰</span>
  </a>
  <a class="home-part-card" href="manuscript/part-6-上线.md">
    <img src="assets/part6-launch.webp" alt="第六部分卷首艺术">
    <span class="part-idx">陆</span>
    <strong>上线</strong>
    <span>五层门禁、风控三防线、对账回滚、合规红线</span>
  </a>
  <a class="home-part-card" href="manuscript/part-7-治理.md">
    <img src="assets/part7-governance.webp" alt="第七部分卷首艺术">
    <span class="part-idx">柒</span>
    <strong>治理</strong>
    <span>提示词归档、幻觉处理、ADR、组织与契约治理</span>
  </a>
  <a class="home-part-card" href="manuscript/part-8-四案例.md">
    <img src="assets/part8-fourcases.webp" alt="第八部分卷首艺术">
    <span class="part-idx">捌</span>
    <strong>四案例</strong>
    <span>等权第一人称叙事 + 灰度发布锚点</span>
  </a>
  <a class="home-part-card" href="manuscript/part-9-交叉收束.md">
    <img src="assets/part9-convergence.webp" alt="第九部分卷首艺术">
    <span class="part-idx">玖</span>
    <strong>交叉收束</strong>
    <span>规模 × 治理密度 × 三原则加严形态</span>
  </a>
</div>

---

## 从哪里开始

<div class="path-row">
  <a class="path-card" href="manuscript/ch01-这本书是什么.md">
    <strong>这本书是什么</strong>
    <span>先对齐定位与边界</span>
  </a>
  <a class="path-card" href="manuscript/ch02-90天总路线图.md">
    <strong>90 天路线图</strong>
    <span>季度作战与验收</span>
  </a>
  <a class="path-card" href="guide.md">
    <strong>阅读指南</strong>
    <span>按角色选路径</span>
  </a>
  <a class="path-card" href="manuscript/ch42-附录K-一线最小实践包.md">
    <strong>一线最小包</strong>
    <span>一页可抄</span>
  </a>
</div>

- 想先看案例 → [四案例时间线](manuscript/ch03-案例时间线.md)  
- 系统面（eval / 成本 / 权限）→ [附录 J](manuscript/ch41-附录J-AI系统工程.md)  
- 全书骨架 → [总览](manuscript/README.md)

---

## 证据边界

四案例均为**自洽虚构的脱敏示范案例**，不指代任何真实公司或个人。数字以 [数字清单](manuscript/ch05-数字清单.md) 为唯一事实来源。正文引用时不得把案例当作真实记录陈述。

理论章另附**公开参照**（DORA、NIST、GitHub 企业研究等），详见 [公开证据档案](public-evidence.md) 与 [延伸阅读](references.md)。外部资料只做框架对照，不给虚构事故数字背书。

---

> **本书的一句话**：组织接管的全部意义，就是在 AI 把事情做完之后，还有人敢站出来说——**「这一步，AI 做不了，我来。」**
