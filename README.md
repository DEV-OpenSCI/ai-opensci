# ai-opensci

> 把科研变成流水线：用 AI 在每个环节降本增效

一个 Claude Code 插件，将科研流程工程化，通过 Agent 编排、MCP Server、Skills、Hooks 等能力，覆盖从文献调研到论文写作的完整科研链路。

## 架构总览

```
                        ┌─────────────────────────────────┐
                        │     /research-pipeline          │
                        │     (全流水线串行编排)            │
                        └──────────────┬──────────────────┘
                                       │
        ┌──────────┬──────────┬────────┼────────┬──────────┐
        ▼          ▼          ▼        ▼        ▼          ▼
  ┌──────────┐┌──────────┐┌───────┐┌───────┐┌───────┐┌──────────┐
  │literature││experiment││ data  ││ paper ││ peer  ││  审稿    │
  │ review   ││ design   ││analyze││ write ││review ││  自检    │
  │(并行Agent)││          ││       ││(串行) ││(并行) ││         │
  └────┬─────┘└──────────┘└───┬───┘└───┬───┘└───┬───┘└──────────┘
       │                      │        │        │
  ┌────┴────────────────┐  ┌──┴──┐  ┌──┴──┐  ┌──┴──┐
  │  MCP Servers        │  │Agent│  │Agent│  │Agent│
  │ ┌────────┐┌───────┐ │  │分析 │  │写作 │  │审稿 │
  │ │Scholar ││arXiv  │ │  └─────┘  └─────┘  └─────┘
  │ └────────┘└───────┘ │
  │ ┌────────┐┌───────┐ │
  │ │PDF读取 ││CrossRef│ │
  │ └────────┘└───────┘ │
  └─────────────────────┘
```

## 能力维度

| 维度 | 实现 | 科研场景 |
|------|------|---------|
| **Skills** (6个) | SKILL.md + frontmatter | 文献调研、实验设计、数据分析、论文写作、模拟审稿、全流水线 |
| **MCP Servers** (4个) | Python + FastMCP | Semantic Scholar、arXiv、PDF 解析、CrossRef |
| **Agents** (4个) | Agent markdown | 文献专家、分析专家、写作专家、审稿专家 |
| **Hooks** (2个) | PreToolUse + PostToolUse | 可复现性检查、数据安全检查 |
| **编排模式** | 串行 + 并行 | 流水线 / 多源并行搜索 / 多角色并行审稿 |

## 快速开始

### 安装依赖

```bash
pip install -r mcp-servers/requirements.txt
```

### 作为插件使用

```bash
# 开发模式
claude --plugin-dir /path/to/ai-opensci

# 或安装到 Claude Code
# (发布到 marketplace 后)
# /plugin marketplace add your-name/ai-opensci
```

### 使用 Skills

```bash
# 文献调研 (并行 Agent + MCP)
/ai-opensci:literature-review transformer attention mechanism in protein structure prediction

# 实验设计
/ai-opensci:experiment-design "larger batch size improves model convergence speed"

# 数据分析
/ai-opensci:data-analysis ./data/experiment_results.csv

# 论文写作 (串行 Agent 流水线)
/ai-opensci:paper-write "Novel attention mechanism for protein folding"

# 模拟审稿 (3个 Reviewer 并行)
/ai-opensci:peer-review ./draft/paper_v1.pdf

# 全流水线 (压轴)
/ai-opensci:research-pipeline "How can LLMs improve drug discovery pipeline efficiency?"
```

## 项目结构

```
ai-opensci/
├── .claude-plugin/
│   └── plugin.json              # 插件清单
├── package.json
├── skills/
│   ├── literature-review/       # /literature-review  并行搜索 + MCP
│   ├── experiment-design/       # /experiment-design   实验方案生成
│   ├── data-analysis/           # /data-analysis       自动分析 + 可视化
│   ├── paper-write/             # /paper-write         串行写作流水线
│   ├── peer-review/             # /peer-review         多角色并行审稿
│   └── research-pipeline/       # /research-pipeline   全流程编排
├── agents/
│   ├── literature-agent.md      # 文献调研专家
│   ├── analysis-agent.md        # 数据分析专家
│   ├── writing-agent.md         # 学术写作专家
│   └── reviewer-agent.md        # 审稿专家 (支持多角色)
├── mcp-servers/
│   ├── requirements.txt
│   ├── scholar-server/          # Semantic Scholar API
│   ├── arxiv-server/            # arXiv 搜索 + 全文
│   ├── pdf-reader-server/       # 本地 PDF 解析
│   └── crossref-server/         # DOI + 期刊信息
├── hooks/
│   └── hooks.json               # PostToolUse + PreToolUse
└── scripts/
    └── hooks/
        ├── check_reproducibility.py   # 可复现性检查
        └── check_data_safety.py       # 数据安全检查
```

## Agent 编排模式详解

### 模式 1: 并行搜索 + 汇总 (`/literature-review`)

```
User: "transformer in bioinformatics"
         │
    ┌────┼────┐
    ▼    ▼    ▼         (并行)
  [S2]  [arXiv] [PDF]
    │    │    │
    └────┼────┘
         ▼              (汇总)
    [合并去重排序]
         │
         ▼
    文献调研报告
```

### 模式 2: 串行流水线 (`/paper-write`)

```
大纲 → Introduction → Methods → Results → Discussion → Abstract
  │         │            │         │           │           │
  ▼         ▼            ▼         ▼           ▼           ▼
[确认]   [写作agent]  [写作agent] [分析+写作] [写作agent] [写作agent]
```

### 模式 3: 多角色并行 (`/peer-review`)

```
Paper
  │
  ├── Reviewer 1 (方法论)  ──┐
  ├── Reviewer 2 (领域)    ──┼── Meta-Reviewer → 综合意见
  └── Reviewer 3 (统计)    ──┘
```

## MCP Server API

### scholar-server
- `search_papers(query, limit, year_from, year_to)` — 搜索论文
- `get_paper_details(paper_id)` — 获取论文详情
- `get_citations(paper_id, limit)` — 前向引用
- `get_references(paper_id, limit)` — 反向引用
- `search_author(name)` — 搜索作者

### arxiv-server
- `search_arxiv(query, limit, sort_by, category)` — 搜索预印本
- `get_arxiv_paper(arxiv_id)` — 获取论文详情
- `get_arxiv_latex_source(arxiv_id)` — LaTeX 源码下载

### pdf-reader-server
- `read_pdf(file_path, max_pages)` — 读取 PDF 全文
- `extract_paper_structure(file_path)` — 提取论文结构
- `extract_tables_and_figures(file_path)` — 提取图表信息

### crossref-server
- `resolve_doi(doi)` — DOI 解析
- `search_crossref(query, limit, filter_type)` — 搜索出版物
- `get_journal_info(issn)` — 期刊信息

## Hooks

| Hook | 触发时机 | 作用 |
|------|---------|------|
| `check_reproducibility` | 保存 .py 分析脚本后 | 检查是否设置了 random seed、是否有硬编码路径 |
| `check_data_safety` | 写入文件前 | 检测潜在的敏感数据字段（患者ID、邮箱等） |

## License

MIT
