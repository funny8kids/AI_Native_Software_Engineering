# AI Native Software Engineering

《AI 原生软件工程》——当 AI 自己兜不住的时候，组织如何接管。

## 站点

- 源码：`docs/`（Docsify，零 CDN 自托管）
- 部署：Netlify（`netlify.toml` → `publish = "docs"`）
- 本地预览：

```powershell
npm install
npm run docs
```

打开 http://localhost:3000

## 书稿结构

```text
docs/
  index.html          # Docsify 入口 + Mermaid 插件
  theme.css           # 浅色主题 + 首页组件
  assets/             # 封面与案例头图（WebP）
  vendor/             # docsify / prism / mermaid 自托管
  manuscript/         # 地基 + 33 章 + 附录
  materials.md        # 作者素材采集清单
  references.md       # 延伸阅读与公开参照
BOOK_SPEC.md          # 写作宪法
GLOSSARY.md           # 术语表
STYLE_GUIDE.md        # 风格指南
DIAGNOSIS.md          # 全书诊断
FIGURE_LIST.md        # 配图清单
```

## 编辑部纪律

不要一次性让 AI「重写全书」。正确循环：

**诊断 → 补真实素材 → AI 扩写 → 作者精修 → 配图 → 事实核查 → 风格审校**

边界见 `BOOK_SPEC.md`。四案例为自洽虚构脱敏示范，数字以 `docs/manuscript/02-数字清单.md` 为准。

## 一句话

AI 做可能，人做选择，人做负责。
