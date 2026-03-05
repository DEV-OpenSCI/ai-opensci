# ai-opensci

> 把科研变成流水线：用 AI 在每个环节降本增效

一个 Claude Code 插件，将科研流程工程化，通过 Agent 编排、MCP Server、Skills、Hooks 等能力，覆盖从文献调研到论文写作的完整科研链路。

## 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                  Orchestrator Layer                      │
│              /research-pipeline (4-Phase)                │
│   Phase 1 (并行) → Phase 2 (串→并) → Phase 3 (串行) → Phase 4 (并行)  │
├──────────┬──────────┬──────────┬──────────┬─────────────┤
│ /lit-    │ /exp-    │ /data-   │ /paper-  │ /peer-      │
│ review   │ design   │ analysis │ write    │ review      │
│ (3源并行) │          │ (+验证)  │ (串行)   │ (3角色并行) │
├──────────┴──────────┴──────────┴──────────┴─────────────┤
│                    Agent Layer                           │
│  literature-agent  analysis-agent  writing-agent  reviewer-agent  │
├─────────────────────────────────────────────────────────┤
│                    MCP Tool Layer                        │
│  Scholar  Elicit  Consensus  arXiv  CrossRef  PDF-Reader  Paper-Store  │
├─────────────────────────────────────────────────────────┤
│              State Store (pipeline_state.json)           │
└─────────────────────────────────────────────────────────┘
```

## 能力维度

| 维度 | 数量 | 实现 | 科研场景 |
|------|------|------|---------|
| **Skills** | 6 | SKILL.md + 编排规范 | 文献调研、实验设计、数据分析、论文写作、模拟审稿、全流水线 |
| **MCP Servers** | 7 | Python + FastMCP | Semantic Scholar、Elicit、Consensus、arXiv、CrossRef、PDF 解析、Paper Store |
| **Agents** | 4 | Agent markdown (规范化) | 文献专家、分析专家、写作专家、审稿专家 |
| **Hooks** | 2 | PreToolUse + PostToolUse | 可复现性检查、数据安全检查 |
| **编排模式** | 3 | 串行 + 并行 Fan-out + 混合 | 流水线 / 多源并行搜索 / 多角色并行审稿 |

## 快速开始

### 安装依赖

```bash
pip install -r mcp-servers/requirements.txt
```

### 配置 API Key（可选）

```bash
# Elicit（需要 Pro 计划，~$10/月）
export ELICIT_API_KEY="your-key-here"

# Consensus（需要申请 API access）
export CONSENSUS_API_KEY="your-key-here"

# CrossRef 礼貌池（可选，提高速率限制）
export CROSSREF_MAILTO="your-email@example.com"
```

> Semantic Scholar、arXiv、PDF Reader、Paper Store 无需 API Key。
> 缺少 Elicit/Consensus Key 时，文献调研会自动降级（跳过该源，使用剩余源）。

### 作为插件使用

```bash
# 开发模式
claude --plugin-dir /path/to/ai-opensci
```

### 使用 Skills

```bash
# 文献调研 (3源并行 + MCP + 本地存储)
/ai-opensci:literature-review transformer attention mechanism in protein structure prediction

# 实验设计
/ai-opensci:experiment-design "larger batch size improves model convergence speed"

# 数据分析 (自动分析 + 脚本验证)
/ai-opensci:data-analysis ./data/experiment_results.csv

# 论文写作 (串行 Agent 流水线 + 信息蒸馏)
/ai-opensci:paper-write "Novel attention mechanism for protein folding"

# 模拟审稿 (3 Reviewer 并行 + Meta-Review)
/ai-opensci:peer-review ./draft/paper_v1.pdf

# 全流水线 (4 Phase, 10分钟内完成)
/ai-opensci:research-pipeline "How can LLMs improve drug discovery pipeline efficiency?"
```

## 项目结构

```
ai-opensci/
├── .claude-plugin/
│   ├── plugin.json              # 插件清单
│   └── marketplace.json         # Marketplace 配置
├── package.json
├── skills/
│   ├── literature-review/       # 三源并行搜索 + MCP
│   ├── experiment-design/       # 实验方案生成
│   ├── data-analysis/           # 自动分析 + 脚本验证
│   ├── paper-write/             # 串行写作 + 信息蒸馏
│   ├── peer-review/             # 多角色并行审稿
│   └── research-pipeline/       # 4-Phase 全流程编排
├── commands/
│   ├── literature-review.md
│   ├── experiment-design.md
│   ├── data-analysis.md
│   ├── paper-write.md
│   ├── peer-review.md
│   └── research-pipeline.md
├── agents/
│   ├── literature-agent.md      # 文献调研专家
│   ├── analysis-agent.md        # 数据分析专家
│   ├── writing-agent.md         # 学术写作专家
│   └── reviewer-agent.md        # 审稿专家 (3 种角色)
├── mcp-servers/
│   ├── requirements.txt
│   ├── scholar-server/          # Semantic Scholar API
│   ├── elicit-server/           # Elicit AI 研究助手
│   ├── consensus-server/        # Consensus 立场分析
│   ├── arxiv-server/            # arXiv 预印本搜索
│   ├── pdf-reader-server/       # 本地 PDF 解析
│   ├── crossref-server/         # DOI + 期刊信息
│   └── paper-store/             # 文献下载与管理
├── hooks/
│   └── hooks.json               # PostToolUse + PreToolUse
└── scripts/
    ├── timer.py                 # 流水线计时器
    └── hooks/
        ├── check_reproducibility.py   # 可复现性检查
        └── check_data_safety.py       # 数据安全检查
```

## Agent 编排模式

### 模式 1: 并行 Fan-out + 聚合 (`/literature-review`)

```
User: "transformer in bioinformatics"
         │
    ┌────┼────────┐
    ▼    ▼        ▼         (并行 3 Agent)
[Scholar] [Elicit] [Consensus]
    │    │        │
    └────┼────────┘
         ▼                  (聚合: 去重 → 评分 → 筛选)
    5-8 篇核心论文
         │
         ▼
    保存到 Paper Store
```

### 模式 2: 串行流水线 + 信息蒸馏 (`/paper-write`)

```
大纲 → [确认] → Introduction → Methods → Results → Discussion → Abstract
                     │            │          │           │           │
                  3句摘要 →    3句摘要 →  3句摘要 →   3句摘要 →    各节摘要
                 (蒸馏传递)   (蒸馏传递)  (蒸馏传递)  (蒸馏传递)  (蒸馏传递)
```

### 模式 3: 多角色并行 + Meta-Review (`/peer-review`)

```
Paper
  │
  ├── Reviewer 1 (方法论)  ──┐
  ├── Reviewer 2 (领域)    ──┼── Meta-Reviewer → P0/P1/P2 改进项
  └── Reviewer 3 (统计)    ──┘
       (结构化 JSON 输出)     (确定性聚合逻辑)
```

## MCP Server API

### scholar-server (无需 API Key)
- `search_papers(query, limit, year_from, year_to)` — 关键词搜索
- `get_paper_details(paper_id)` — 论文详情 + TL;DR
- `get_citations(paper_id, limit)` — 前向引用
- `get_references(paper_id, limit)` — 反向引用
- `search_author(name)` — 作者搜索

### elicit-server (需要 ELICIT_API_KEY)
- `search_papers(query, max_results, type_tags, max_quartile)` — AI 学术搜索
- `create_report(research_question)` — 生成 AI 研究报告（异步）
- `get_report(report_id)` — 获取报告结果

### consensus-server (需要 CONSENSUS_API_KEY)
- `search_papers(query, study_types, exclude_preprints)` — 问句搜索 + AI takeaway

### arxiv-server (无需 API Key)
- `search_arxiv(query, limit, sort_by, category)` — 预印本搜索
- `get_arxiv_paper(arxiv_id)` — 论文详情
- `get_arxiv_latex_source(arxiv_id)` — LaTeX 源码下载

### pdf-reader-server (本地)
- `read_pdf(file_path, max_pages)` — PDF 全文提取
- `extract_paper_structure(file_path)` — 论文结构提取
- `extract_tables_and_figures(file_path)` — 图表检测

### crossref-server (无需 API Key，可选 CROSSREF_MAILTO)
- `resolve_doi(doi)` — DOI 解析
- `search_crossref(query, limit, filter_type)` — 出版物搜索
- `get_journal_info(issn)` — 期刊信息

### paper-store (本地)
- `save_paper(...)` — 保存论文元数据 + 下载 PDF
- `save_papers_batch(papers_json)` — 批量保存
- `list_papers()` — 列出本地文献库
- `get_paper(query)` — 按标题/DOI 查找
- `export_references(format)` — 导出参考文献（Markdown/BibTeX）

## Hooks

| Hook | 触发时机 | 作用 |
|------|---------|------|
| `check_reproducibility` | 保存 .py 分析脚本后 | 检查 random seed、硬编码路径 |
| `check_data_safety` | 写入文件前 | 检测敏感数据字段 + 数据文件类型警告 |

## License

MIT
