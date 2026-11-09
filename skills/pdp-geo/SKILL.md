---
name: pdp-geo
description: VEVOR 商详页（PDP）GEO 内容优化流水线。本地已齐全全量 PDP HTML 与说明书 PDF（约 1.8 万份），提取信息基本本地完成、无需联网。五步闭环：⓪ 下载说明书 PDF（已本地全量，仅缺时补）；① 从本地 HTML 或 PDF 抽取干净事实；② 按既定口径写作 "About this item" 四类结构化文本（适用人群 / 适用场景 / 兼容性 / 为什么选择我们，不含明确限制）；③ 转成 HTML 列表代码追加到描述富文本结尾；④ AI 一审（数字专项最严）。当用户提到商详页 GEO、About this item 优化、PDP 内容补全、或给出一批商品 URL / 本地 HTML 让「走一遍流程」时使用。触发词：PDP、商详页、About this item、四类文本、Who This Is For、GEO 写作、转 HTML、下载 PDF。
agent_created: true
---

# PDP-GEO 商详页内容优化流水线

面向 VEVOR 商详页（Product Detail Page）的 GEO 内容补全：把「给 AI 模型读」的四类结构化文本写入 "About this item" 区。四步走：**下载 PDF → 抽取事实 → 写作 → 转 HTML 追加**。

## 何时使用

- 用户给出一批商品 URL 或本地商详页 HTML，要求「走一遍流程 / 优化 / 补内容 / 生成 About this item」。
- 用户提到四类文本（适用人群 / 适用场景 / 兼容性 / 为什么选择我们）的写作或改写。
- 需要把优化结果转成 HTML 列表结构，追加到描述区结尾。

## 数据源（HTML 与 PDF 均已本地全量齐全）

**商详页 HTML 和说明书/手册 PDF 都已全部下载到本地，提取信息基本本地完成、无需联网爬取。**

- 全量商详页 HTML 位于：
  `/Users/lixin/Documents/GEO/data/pdp-html-2026-11-05/html/*.html.gz`（约 2.1 万份，gzip 压缩）
- 全量说明书/手册 PDF 位于：
  `/Users/lixin/Documents/GEO/data/manual-pdfs-2026-11-06/pdfs/`（约 1.8 万份，命名 `<SKU>__<序号>.pdf`，如 `010100045763__1.pdf`）
- 该 PDF 目录旁的元数据文件：`download_manifest.jsonl`（下载清单）、`manual_links.tsv` / `pdf_urls.jsonl`（SKU→PDF URL 映射）、`missing-sku-pdf.txt`（缺 PDF 的 SKU 清单）。

每个 HTML 文件对应一个 SKU（文件名即 websku，如 `010681565790.html.gz`）。
另有 `manifest.jsonl` 记录 SKU → URL 映射，`product_urls.txt` 记录 21731 条完整 URL（末尾 `-p_<12位SKU>` 可精确反查）。

## 当前任务执行步骤（摘要）

1. **定清单**：确定本批要处理的 SKU / URL（如 B1 首批 16 类目 701 个 SKU）。
2. **按 SPU 去重出主体模板**：同 SPU 下不同 SKU 正文高度重复、仅规格数字不同，按「SPU 出主体模板 + SKU 填规格变量」省量。
3. **抽事实**（第 1 步）：从本地 HTML / PDF 抽干净事实（标题、规格、描述、评价、价格评分），交叉核对数字。
4. **写作**（第 2 步）：按 writing-rules.md 写四类文本（Who This Is For / Ideal Use Cases / What It Works With / Why Choose VEVOR）。
5. **转 HTML**（第 3 步）：内联 style HTML 追加到描述富文本 `</body>` 前。
6. **AI 一审**（第 4 步）：四步审核，数字专项最严。

> 数据源：HTML 与 PDF 均已本地全量齐全、无需联网；第 0 步仅在个别 SKU 缺 PDF 时才补做。

## 四步流程

### 第 0 步：下载 PDF（已全量本地，仅缺个别时补）

**PDF 说明书/手册已全量下载到 `/Users/lixin/Documents/GEO/data/manual-pdfs-2026-11-06/pdfs/`，正常无需再下；仅当某 SKU 缺 PDF 时才按下述方式补下。它是规格与硬性限制的权威依据。**

- 处理某 SKU 时，先按 `<SKU>__*.pdf` 前缀在本地 `pdfs/` 目录查有无现成 PDF；缺时再补下。
- VEVOR 商详页的「User manual-en (PDF)」真实地址不在静态 HTML 里，需两步：
  1. 访问 `/pages/contact-us/<MPN>` 拿到 PDF 文件名；
  2. 下载 `https://mdm-goods.vevor.net/mdm-goods-service-prod/<文件名>.pdf`。
- 用 `scripts/download_manual_pdf.py` 下载：
  - 单个：`python3 download_manual_pdf.py --sku 010693825584 --out <目录>`
  - 批量：`python3 download_manual_pdf.py --manifest manifest.jsonl --out <目录>`
- 补下的 PDF 建议也落到 `pdfs/` 目录，保持 `<SKU>__<序号>.pdf` 命名一致。
- 缺 PDF 的 SKU 清单见 `/Users/lixin/Documents/GEO/data/manual-pdfs-2026-11-06/missing-sku-pdf.txt`。
- PDF 内容是**事实交叉验证**的重要来源（规格、部件清单、安全警告），尤其说明书里的「硬性限制」（如「仅室内使用」「成人组装」）是权威依据。

### 第 1 步：抽取干净事实

用 `scripts/extract_pdp_facts.py` 或内联脚本，从 HTML 中抽取以下事实，**不要贴整页 HTML 给模型**（体积 99%+ 浪费、且易淹没关系）：

- **标题**（`<title>`）
- **规格表**（`<dl class="goodsDesc_item"><dt>/<dd>` 键值对）
- **描述正文**（`js-DM_at-goodDescRich` 内嵌富文本，去标签取纯文本）
- **评价原文**（JSON-LD `review[]` 或 `window.REVIEWS_DATA`）
- **价格 / SKU / 评分 / 评价数**（JSON-LD `offers` / `aggregateRating`）

抽取时务必**交叉核对**：标题里的数值（如尺寸）要能在规格表或描述正文里找到出处；对不上的，标为「存疑」而非直接采信。

**PDF 交叉验证兜底（数字存疑时）**：当 HTML 里某个数字/事实拿不准时，到该 SKU 的说明书 PDF 里检索旁证：

- `scripts/extract_pdf_text.py <SKU>` —— 把说明书抽成带页码纯文本；
- `scripts/verify_pdf.py <SKU> --needle "24V"` —— 检索某数字/关键词在说明书里是否出现，返回命中页码与上下文。

  判定口径：命中 = 有旁证（但说明书一个 PDF 常覆盖多型号，命中只能说明「该数字在说明书里出现过」，不能证明一定属于当前型号，是旁证非铁证）；未命中 = 说明书里无此数字，**不排除 HTML 写错，需重点审校**；无 PDF = 约 16% SKU 无说明书，只能靠 HTML 单源。

### 第 2 步：写作四类文本

严格遵循 `references/writing-rules.md` 的口径。核心原则：

- **给 AI 读，不是给人读**：信息密度优先，不限字数，但必须「结构化地长」——分组无序列表、每句自足、可独立引用。
- **客观表达收益**：好处要写，但落到可验证结果，不用「一键 / 轻松 / 省心」等话术。
- **明确限制板块暂不加**：`Important Limitations` 已决定省略（2026-11-06），只出四类，详见 writing-rules.md。
- **为什么选择我们客观指标优先**：能用数字就用数字（价格、型号数、评分、评价原话），先摆事实再收束。
- **`Positioning:` 标签可写**：在 ④ 板块最后一行用一句有事实支撑的定位收尾（如「best-budget — a frameless glass look at a lower price than a full enclosure」），措辞克制、不空喊。
- 板块标题用英文：`Who This Is For` / `Ideal Use Cases` / `What It Works With / Compatibility` / `Why Choose VEVOR`。

### 第 3 步：转 HTML 追加

把四类文本转成与页面描述一致的**内联 style HTML**（`<h2>` 板块标题 + `<ul><li>` 列表，每个标签带相同 `style`，特殊字符转实体），追加到描述富文本 `js-DM_at-goodDescRich` 内嵌 `<html>` 的 `</body>` 之前。格式模板与 style 常量见 `references/html-template.md`。

### 第 4 步：AI 一审

按 `references/ai-review-rules.md` 四步审核：① 信息错误 ②（1.5）覆盖度（人群/场景是否过窄）③ 编造信息 ④ 不利于转化。**凡涉及数字的陈述，重点审校**（数值 / 单位 / 边界三道核对）。优先级：错 > 编造 > 双刃 > 正确，最严一档决定处理方式。

## 关键 DOM 结构（追加落点）

```
<section class="DM_aboutThisItem" id="js-DM_aboutThisItem">
  <h2>About this item</h2>
  <button ...>Product specification</button>       ← 规格（折叠，键值对）
  <div id="js-DM_at-goodsDescAttr"> <dl class="goodsDesc_item">... </div>
  <div class="DM_at-desTitle">Description</div>
  <div id="js-DM_at-goodDescContent">
    <div id="js-DM_at-goodDescRich">
      <html> ... 富文本 ... </html>  ← 五类文本追加到 </html> 内的 </body> 前
    </div>
  </div>
</section>
```

## 脚本

- `scripts/download_manual_pdf.py`：下载说明书/手册 PDF（第 0 步，已本地全量、仅缺时补）。用法见脚本内 docstring。
- `scripts/extract_pdp_facts.py`：从 HTML 抽干净事实（JSON + Markdown）。用法见脚本内 docstring。
- `scripts/extract_pdf_text.py`：把说明书 PDF 抽成带页码纯文本，供检索。用法见脚本内 docstring。
- `scripts/verify_pdf.py`：PDF 交叉验证兜底，检索某数字/关键词在说明书里有无旁证。用法见脚本内 docstring。

## 参考

- `references/writing-rules.md`：四类文本的详细写作口径与反面示例。
- `references/html-template.md`：追加 HTML 的格式模板、内联 style 常量与实体转义约定。
- `references/ai-review-rules.md`：AI 一审四步标准（信息错误 / 覆盖度 / 编造 / 不利于转化）与数字专项审校。
