# Claude Code / 通用 Agent Skill：paper-publication-check

## 建议目录结构

```text
paper-publication-check/
└── SKILL.md
```

---

## `SKILL.md`

```md
---
name: paper-publication-check
description: 给定一篇论文 PDF，判断它是否已经正式发表，并输出结论、证据、链接和不确定性说明。
allowed-tools: file_search, web
---

# paper-publication-check

## Purpose

给定一篇论文 PDF，判断它当前属于以下哪种状态：

1. 已正式发表（Published / Version of Record）
2. 已在线发表（Online First / Early Access / Early View）
3. 已接受但未正式发表（Accepted Manuscript / In Press / Uncorrected Proof）
4. 预印本（Preprint）
5. 无法确认

核心要求：**不能只因为有 DOI 就判断为“已发表”**。

---

## When to use

当用户提出以下类型请求时使用：

- 这篇论文是否已经发表？
- 帮我判断这份 PDF 是预印本还是正式发表版
- 检查这篇论文是否见刊
- 看看这篇文章现在是不是 published
- 根据这篇 PDF 判断它的 publication status

输入通常为：

- 用户上传的论文 PDF
- 或者一个可访问的 PDF 链接

---

## Inputs

输入为一篇论文 PDF。

优先从 PDF 中提取以下信息：

- 标题
- 作者
- DOI
- 期刊名 / 会议名 / 出版社
- 卷（volume）/ 期（issue）/ 页码（pages）/ article number
- 首页页眉页脚和版权信息
- 是否有以下状态标识：
  - Published
  - Version of Record
  - Early Access
  - Online First
  - Early View
  - Accepted Manuscript
  - In Press
  - Uncorrected Proof
  - Preprint
  - arXiv
  - bioRxiv
  - medRxiv
  - SSRN
  - Research Square

---

## Tools policy

### 1. PDF 内部信息
先读取 PDF 本身，提取标题、作者、DOI、期刊名、版权页、页眉页脚、卷期页码等信息。

### 2. 外部验证
若信息可能变化或需要验证，必须检索外部来源。
优先顺序：

1. DOI 落地页
2. 出版社官方页面
3. Crossref
4. OpenAlex
5. Google Scholar
6. 预印本平台（arXiv / bioRxiv / medRxiv / SSRN / Research Square 等）

### 3. 证据优先级
高优先级证据：
- 出版社官方页面
- DOI 官方落地页
- Crossref 元数据

中优先级证据：
- OpenAlex
- Google Scholar

低优先级证据：
- 第三方转载页
- 非官方博客或聚合站

如高优先级证据与低优先级证据冲突，以高优先级为准。

---

## Decision rules

### A. 判定“已正式发表”
满足以下任一强条件即可：

- 出版社官方页面明确标注 `Published`、`Version of Record` 或等价表述
- 文章已存在正式期刊页面，并分配了 volume / issue / pages 或正式 article number
- PDF 本身为出版社正式排版版本，且能与官方页面对应确认

### B. 判定“已在线发表”
满足以下条件：

- 已有出版社官方文章页
- 页面标注 `Online First`、`Early Access`、`Early View`、`Advance online publication` 等
- 可能还没有完整卷期页码

这类应明确写为：**已在线发表，但未必已进入正式卷期**。

### C. 判定“已接受但未正式发表”
满足以下条件之一：

- PDF 或官方页面标注 `Accepted Manuscript`
- 出现 `In Press`、`Uncorrected Proof`、`Author Accepted Manuscript`
- 没有查到正式 published record

### D. 判定“预印本”
满足以下条件之一：

- PDF 明确标注 `Preprint`
- 来源为 arXiv / bioRxiv / medRxiv / SSRN / Research Square 等预印本平台
- 没找到对应正式期刊版本

### E. 判定“无法确认”
出现以下情况之一：

- PDF 是扫描件或文字提取失败
- 标题 / DOI / 作者信息不完整，无法唯一匹配
- 检索结果冲突，且没有足够官方证据裁决
- 只能找到非官方来源

---

## Required workflow

### Step 1：从 PDF 提取信息
至少检查：

- 首页
- 页眉页脚
- 版权页
- DOI 所在位置
- 页末脚注和参考引用格式

### Step 2：做 PDF 内部初判
根据版式、标识语、期刊名、版权信息、卷期页码等，先形成初步判断。

### Step 3：外部检索验证
#### 有 DOI 时
优先用 DOI 检查：
- DOI 是否可解析
- DOI 落地页是否为出版社页面
- 页面状态是什么
- 是否已有正式 article page

#### 无 DOI 时
用 `标题 + 作者` 检索：
- 出版社官网
- Crossref
- OpenAlex
- Google Scholar
- 预印本平台

### Step 4：输出结论
必须先给结论，再给证据，不要只给模糊表述。

---

## Output format

输出必须严格包含这些字段：

```json
{
  "title": "论文标题",
  "authors": ["作者1", "作者2"],
  "doi": "若识别到则填写，否则为 null",
  "journal_or_source": "期刊名/会议名/平台名，未知则为 null",
  "status": "已正式发表 | 已在线发表 | 已接受未正式发表 | 预印本 | 无法确认",
  "confidence": "高 | 中 | 低",
  "evidence": [
    "证据1",
    "证据2",
    "证据3"
  ],
  "reasoning": "简洁解释为什么这样判断",
  "links_checked": [
    "DOI 落地页",
    "出版社页面",
    "Crossref",
    "OpenAlex / Scholar / 预印本平台"
  ],
  "notes": "补充说明，例如：有 DOI 但只是 preprint；或仅 Early Access 尚无卷期页码"
}
```

---

## Response style

- 先结论，后证据
- 不要空话
- 明确区分：
  - 正式发表
  - 在线发表
  - 已接受未正式发表
  - 预印本
- 证据不足时，不要硬判
- 结论依赖推断时，必须明确说明不确定性

---

## Standard answer patterns

### 模板：已正式发表
这篇论文**已正式发表**，置信度：**高**。

依据：
1. PDF 中出现明确期刊或出版社信息。
2. DOI 对应到出版社官方页面，状态为 `Published` 或 `Version of Record`。
3. 已存在正式卷期页码或 article number。

### 模板：已在线发表
这篇论文**已在线发表，但未必已进入正式卷期**，置信度：**中到高**。

依据：
1. DOI 已解析到出版社官方页面。
2. 页面标注 `Online First` / `Early Access` / `Early View`。
3. 暂未见完整卷期页码。

### 模板：已接受未正式发表
这篇论文目前更像是**已接受但未正式发表**，置信度：**中**。

依据：
1. PDF 或页面标注 `Accepted Manuscript` / `In Press` / `Uncorrected Proof`。
2. 未见正式出版记录。

### 模板：预印本
这篇论文目前判断为**预印本**，置信度：**高**。

依据：
1. 来源为 arXiv / bioRxiv / medRxiv / SSRN / Research Square。
2. 未找到正式出版社页面。

### 模板：无法确认
目前**无法确认**这篇论文是否已发表，置信度：**低**。

原因：
1. PDF 中缺少可靠的标题 / DOI / 来源信息。
2. 检索结果不足或冲突。
3. 暂未找到可验证状态的官方页面。

---

## Failure handling

遇到以下情况时，必须直接说明限制：

- PDF 为扫描件，文本提取失败
- DOI 模糊或识别错误
- 标题过于通用，存在多篇重名结果
- 同一论文存在多个版本，无法唯一匹配

---

## Hard constraints

1. **DOI 不是“已发表”的充分条件。**
2. **优先依赖官方来源，不依赖二手博客判断。**
3. **若发现同名预印本和正式发表版，要区分并说明二者关系。**
4. **若只能确认 early access，不得写成“正式卷期发表”。**
5. **若没有足够证据，不得强行输出高置信度结论。**

---

## One-line rule

**判断论文是否“已发表”，看的是官方出版状态，不是单看 DOI。**
```

---

## 你可以直接这样用

把上面的 `SKILL.md` 放进一个目录：

```text
.paper-publication-check/SKILL.md
```

或者：

```text
skills/paper-publication-check/SKILL.md
```

然后让 agent 在收到“检查这篇论文是否已发表”的请求时调用它。

