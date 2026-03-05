---
name: literature-review
description: 文献调研——输入研究问题，通过 Semantic Scholar、Elicit、Consensus 三源并行搜索，筛选 5-8 篇高质量核心论文并汇总综述报告。展示并行 Agent 编排 + MCP Server 调用。
argument-hint: <research question or keywords>
user-invocable: true
---

# Literature Review — 三源并行搜索，筛选核心论文

你将执行一次文献调研，目标是找到 **5–8 篇质量较高（引用数高、来源可靠）的核心论文**。

## 用户输入

研究问题或关键词: `$ARGUMENTS`

## 三个数据源

| 数据源 | MCP Server | 特点 | 用法 |
|--------|-----------|------|------|
| **Semantic Scholar** | `scholar-server` | 直接输入关键词，可看引用数，覆盖 2 亿+ 论文 | 用关键词搜索，按引用量筛选 |
| **Elicit** | `elicit-server` | 输入研究问题，自动找相关论文并提炼关键点，支持研究类型过滤 | 用自然语言研究问题搜索 |
| **Consensus** | `consensus-server` | 用问句搜索，返回每篇论文支持/反对的 AI 结论（takeaway） | 用问句搜索，看论文立场 |

## 执行流程

### Step 1: 理解研究问题

将 `$ARGUMENTS` 转化为:
- **关键词版本**（给 Semantic Scholar）: 提取核心术语，如 "LLM drug discovery pipeline"
- **研究问题版本**（给 Elicit）: 完整研究问题，如 "How can large language models improve drug discovery efficiency?"
- **问句版本**（给 Consensus）: 可回答的问句，如 "Do LLMs improve drug discovery outcomes?"

### Step 2: 三源并行检索 (Parallel Agent Pattern)

**同时**启动 3 个并行搜索任务（使用 Agent 工具，设置 `run_in_background: true`）:

#### Agent A — Semantic Scholar
```
使用 scholar-server MCP:
1. search_papers(query=关键词, limit=15)
2. 对 top 3 高引论文 → get_citations() 追踪引用链
3. 对 top 3 高引论文 → get_references() 找上游经典文献
```

#### Agent B — Elicit
```
使用 elicit-server MCP:
1. search_papers(query=研究问题, max_results=10, max_quartile=1)
   → 限制 Q1 期刊，确保论文质量
2. 如有需要 → 按 type_tags 过滤 (Meta-Analysis, RCT, Systematic Review)
```

#### Agent C — Consensus
```
使用 consensus-server MCP:
1. search_papers(query=问句, exclude_preprints=true)
   → 只看同行评审论文
2. 重点提取每篇论文的 takeaway（支持/反对/中立）
```

### Step 3: 汇总筛选

等待 3 个 Agent 全部返回后:

1. **去重**: 按 DOI 或标题去重
2. **质量筛选**: 优先保留满足以下条件的论文:
   - 引用数 ≥ 20（或近2年论文放宽到 ≥ 5）
   - 发表在 Q1/Q2 期刊
   - 多个数据源都命中的论文（交叉验证）
3. **分类标记**:
   - 🔬 实证研究 (Empirical)
   - 📊 元分析 (Meta-Analysis)
   - 📝 综述 (Review/Survey)
   - 🆕 前沿工作 (Recent, < 2年)
4. **精选 5-8 篇核心论文**

### Step 4: 保存文献到本地

精选完 5-8 篇核心论文后，使用 `paper-store` MCP 保存到本地：

```
对每篇入选论文，调用 paper-store 的 save_paper:
  save_paper(
    title=论文标题,
    authors=作者列表,
    year=年份,
    abstract=摘要,
    doi=DOI,
    url=论文链接,
    venue=期刊/会议,
    citations=引用数,
    source=数据源 (如 "Semantic Scholar + Elicit"),
    takeaway=Consensus 的 AI 结论,
    pdf_url=PDF 直链 (如有)
  )
```

也可以用 `save_papers_batch` 一次批量保存所有论文（传 JSON 数组）。

保存后文件结构：
```
~/ai-opensci-papers/
├── index.json               ← 全局索引
├── metadata/
│   ├── paper_title_abc123.json   ← 元数据 (标题/作者/摘要/DOI/takeaway)
│   └── ...
└── pdfs/
    ├── paper_title_abc123.pdf    ← PDF 原文 (如有直链)
    └── ...
```

保存完成后用 `list_papers` 确认入库情况。

### Step 5: 输出报告

```markdown
# 文献调研报告: [研究主题]

## 研究现状概述
[2-3 段总结，基于三个数据源的综合分析]

## 核心论文 (5-8 篇)

| # | 论文标题 | 年份 | 引用 | 类型 | 核心贡献 | 数据源 |
|---|---------|------|------|------|---------|--------|
| 1 | ... | 2024 | 156 | 🔬 | ... | S2 + Elicit |
| 2 | ... | 2023 | 89 | 📊 | ... | 三源命中 |
| ... |

## 论文立场分析 (来自 Consensus)
- **支持**: [N 篇论文认为...]
- **反对/质疑**: [N 篇论文指出...]
- **条件性结论**: [N 篇论文表明在...条件下...]

## 研究空白 (Research Gaps)
1. [Gap 1]: 描述 + 依据
2. [Gap 2]: 描述 + 依据

## 推荐阅读顺序
1. 先读 [综述论文] → 建立全景认知
2. 再读 [核心实证] → 理解方法细节
3. 最后读 [前沿工作] → 把握最新进展

## 参考文献
[完整引用列表，含 DOI 链接]
```

报告末尾附上本地存储摘要：

```markdown
## 本地文献库
已保存 N 篇论文到 `~/ai-opensci-papers/`
- PDF 已下载: X 篇
- 仅元数据: Y 篇
使用 `list_papers` 查看完整列表，`export_references` 导出引用。
```

## 演示要点

这个 skill 演示了:
- **4 个 MCP Server 协作**: Semantic Scholar + Elicit + Consensus (搜索) + Paper Store (存储)
- **并行 Agent 编排**: 3 个 agent 同时搜索不同数据源，最后汇总
- **AI 辅助筛选**: 不只是搜索，还做质量评估和立场分析
- **结果交叉验证**: 多数据源命中的论文可信度更高
- **文献持久化**: 搜索结果自动下载 PDF + 保存元数据，形成本地知识库
