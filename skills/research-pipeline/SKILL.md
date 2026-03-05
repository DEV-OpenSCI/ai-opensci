---
name: research-pipeline
description: 全流水线科研编排——从文献调研到论文写作，4 Phase 串行+并行混合编排，10分钟内生成论文。
argument-hint: <research question>
user-invocable: true
---

# Research Pipeline — 全流程科研流水线

## 用户输入

研究问题: `$ARGUMENTS`

---

## 编排架构

```
┌───────────────────────────────────────────────────────┐
│                  Orchestrator (本 Skill)               │  ← 任务拆解、路由、聚合
├───────────┬───────────┬───────────┬───────────────────┤
│ lit-agent │ wri-agent │ rev-agent │  analysis-agent   │  ← 执行层
│   ×3并行  │   串行    │   ×3并行  │     并行          │
├───────────┴───────────┴───────────┴───────────────────┤
│              MCP Tool Layer                           │  ← scholar/elicit/consensus/paper-store
├───────────────────────────────────────────────────────┤
│              State Store (pipeline_state.json)        │  ← 共享状态持久化
└───────────────────────────────────────────────────────┘
```

### 通信模式

```
Phase 1: Parallel Fan-out (3 源文献检索)
Phase 2: Sequential → Parallel Fan-out (假设串行 → 实验+分析并行)
Phase 3: Sequential (论文各节串行)
Phase 4: Parallel Fan-out (3 角色审稿)
```

---

## 终止条件（强制）

```
TIMEOUT_SECONDS   = 600       # 总超时 10 分钟
MAX_RETRIES       = 2         # 单节点最大重试次数
MAX_AGENT_CALLS   = 12        # 全链路 Agent 调用上限
```

超过任一条件时立即终止，输出已完成部分 + 错误报告。

---

## 状态管理

### 状态存储

所有中间状态写入 `output/pipeline_state.json`，禁止依赖 Agent 对话历史传递状态。

```json
{
  "task_id": "pipeline-<timestamp>",
  "status": "RUNNING",
  "current_phase": "phase_1",
  "phases": {
    "phase_1": { "status": "SUCCESS", "checkpoint": { ... } },
    "phase_2a": { "status": "PENDING" },
    "phase_2b": { "status": "PENDING" },
    "phase_3": { "status": "PENDING" },
    "phase_4": { "status": "PENDING" }
  },
  "created_at": "...",
  "updated_at": "..."
}
```

### 状态机

```
PENDING   → 已创建，等待执行
RUNNING   → 执行中
SUCCESS   → 完成，输出可用
FAILED    → 执行失败
  ├─ RETRYABLE  → 可自动重试（MCP 超时、网络错误）
  └─ FATAL      → 需人工介入（全部数据源不可用）
SKIPPED   → 被降级跳过（非关键节点失败）
```

### Checkpoint

每个 Phase 完成后，将以下内容写入 `pipeline_state.json`:
- 当前阶段标识
- 已完成节点的**输出摘要**（不是全量输出）
- 下一步执行所需的最小上下文

---

## 计时器

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" start-pipeline
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" start "阶段名称"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" end
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" report
```

---

## 执行流程

### 启动

1. 生成 `task_id`: `pipeline-<YYYYMMDD-HHmmss>`
2. 初始化 `output/pipeline_state.json`（全部 Phase 标记 PENDING）
3. 启动计时器

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" start-pipeline
```

---

### Phase 1: 文献调研（Parallel Fan-out，目标 ≤2.5min）

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" start "1.文献调研"
```

**输入准备（Orchestrator 执行，确定性逻辑）：**

将 `$ARGUMENTS` 转化为三种检索形式：
```json
{
  "keywords": "提取的核心术语",
  "research_question": "完整研究问题",
  "answerable_query": "可回答的问句"
}
```

**并行启动 3 个 literature-agent**（`run_in_background: true`）：

每个 Agent 接收结构化输入：

```json
// Agent A — Semantic Scholar
{
  "task_id": "<task_id>-lit-scholar",
  "from": "orchestrator",
  "to": "literature-agent",
  "type": "execute",
  "payload": {
    "source": "semantic_scholar",
    "query": "<keywords>",
    "limit": 8
  },
  "metadata": { "timeout_seconds": 120, "retry_count": 0 }
}

// Agent B — Elicit
{
  "task_id": "<task_id>-lit-elicit",
  "from": "orchestrator",
  "to": "literature-agent",
  "type": "execute",
  "payload": {
    "source": "elicit",
    "query": "<research_question>",
    "limit": 8
  },
  "metadata": { "timeout_seconds": 120, "retry_count": 0 }
}

// Agent C — Consensus
{
  "task_id": "<task_id>-lit-consensus",
  "from": "orchestrator",
  "to": "literature-agent",
  "type": "execute",
  "payload": {
    "source": "consensus",
    "query": "<answerable_query>",
    "exclude_preprints": true
  },
  "metadata": { "timeout_seconds": 120, "retry_count": 0 }
}
```

**期望响应格式（每个 Agent）：**

```json
{
  "task_id": "<task_id>-lit-xxx",
  "status": "success",
  "output": {
    "papers": [
      {
        "title": "...", "authors": "...", "year": 2024,
        "venue": "...", "citations": 156, "doi": "...",
        "abstract_summary": "1-2 句摘要",
        "type": "empirical|meta_analysis|review|frontier",
        "takeaway": "支持/反对/中立（仅 Consensus）"
      }
    ],
    "source": "semantic_scholar|elicit|consensus"
  }
}
```

**聚合（Orchestrator 执行，处理部分失败）：**

1. 收集 3 个 Agent 返回结果
2. **部分失败处理**：≥1 个源成功即继续，标记失败源为 SKIPPED
3. 按 DOI/标题去重
4. 筛选 5-8 篇核心论文（优先多源命中 → 高引用 → 近年）
5. 识别 2-3 个 Research Gap
6. 调用 `paper-store` 的 `save_papers_batch` 保存

**Checkpoint 写入（信息蒸馏后）：**

```json
// 写入 pipeline_state.json 的 phase_1.checkpoint
{
  "core_papers": [
    { "title": "...", "year": 2024, "citations": 156,
      "type": "empirical", "contribution": "1句话",
      "doi": "...", "sources": ["scholar", "elicit"] }
  ],
  "research_gaps": ["Gap 1", "Gap 2"],
  "stance_summary": { "support": 3, "oppose": 1, "conditional": 2 },
  "skipped_sources": []
}
```

> **信息蒸馏**：只传 `core_papers` 摘要 + `research_gaps`，不传完整搜索结果。

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" end
```

---

### Phase 2: 假设 + 实验 + 分析（Sequential → Parallel，目标 ≤2.5min）

#### Phase 2a: 假设提炼（Orchestrator 直接执行，无需 Agent）

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" start "2a.假设提炼"
```

**输入**：Phase 1 checkpoint 的 `research_gaps`

**确定性逻辑**：从 research_gaps 中选择第一个 gap 作为假设方向（不依赖 LLM 路由）。

**输出**：
```json
{
  "hypothesis": {
    "h0": "零假设描述",
    "h1": "备择假设描述",
    "iv": "自变量",
    "dv": "因变量",
    "direction": "two-tailed"
  }
}
```

**Checkpoint 写入**：将假设写入 `pipeline_state.json` 的 `phase_2a.checkpoint`。

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" end
```

#### Phase 2b: 实验设计 + 数据分析方案（Parallel Fan-out）

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" start "2b.实验设计+分析方案"
```

**同时启动 2 个 Agent**（`run_in_background: true`）：

```json
// Agent D — 实验设计（Orchestrator 直接生成，或使用 analysis-agent）
{
  "task_id": "<task_id>-exp-design",
  "from": "orchestrator",
  "to": "analysis-agent",
  "type": "execute",
  "payload": {
    "task": "experiment_design",
    "hypothesis": { "h0": "...", "h1": "...", "iv": "...", "dv": "..." }
  },
  "metadata": { "timeout_seconds": 90, "retry_count": 0 }
}

// Agent E — 数据分析方案
{
  "task_id": "<task_id>-analysis-plan",
  "from": "orchestrator",
  "to": "analysis-agent",
  "type": "execute",
  "payload": {
    "task": "analysis_plan",
    "hypothesis": { "h0": "...", "h1": "...", "iv": "...", "dv": "..." }
  },
  "metadata": { "timeout_seconds": 90, "retry_count": 0 }
}
```

**期望响应格式：**

```json
// Agent D 响应
{
  "status": "success",
  "output": {
    "design_type": "RCT / 2x3 析因设计 / ...",
    "variables": { "iv": "...", "dv": "...", "controls": ["..."] },
    "sample_size": { "n_per_group": 30, "total": 60, "with_dropout": 75 },
    "protocol_steps": ["步骤1", "步骤2", "..."]
  }
}

// Agent E 响应
{
  "status": "success",
  "output": {
    "primary_test": "Independent t-test",
    "effect_size_metric": "Cohen's d",
    "visualizations": ["分布图", "箱线图", "对比图"],
    "alpha": 0.05,
    "power": 0.80
  }
}
```

**聚合 + 部分失败处理**：
- 2 个都成功 → 合并结果
- 1 个失败 → 用成功方的结果继续，标记失败方为 SKIPPED
- 2 个都失败 → 标记 Phase 2b 为 FAILED，Phase 3 仍可用 Phase 1+2a 数据继续

**Checkpoint 写入（蒸馏后）：**

```json
{
  "experiment_design": { "design_type": "...", "sample_size": 60, "protocol_steps": ["..."] },
  "analysis_plan": { "primary_test": "...", "effect_size_metric": "...", "visualizations": ["..."] },
  "skipped": []
}
```

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" end
```

---

### Phase 3: 论文写作（Sequential，目标 ≤3.5min）

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" start "3.论文写作"
```

**输入准备（信息蒸馏）：**

从 pipeline_state.json 提取 Phase 1-2 的 checkpoint，**不传完整搜索结果**，只传：

```json
{
  "task_id": "<task_id>-paper-write",
  "from": "orchestrator",
  "to": "writing-agent",
  "type": "execute",
  "payload": {
    "research_question": "$ARGUMENTS",
    "language": "zh-CN",
    "core_papers": [ /* Phase 1 的 5-8 篇论文摘要 */ ],
    "research_gaps": ["Gap 1", "Gap 2"],
    "hypothesis": { "h0": "...", "h1": "..." },
    "experiment_design": { /* Phase 2b 蒸馏后的方案 */ },
    "analysis_plan": { /* Phase 2b 蒸馏后的方案 */ }
  },
  "metadata": { "timeout_seconds": 210, "retry_count": 0 }
}
```

**writing-agent 串行生成各节**（Agent 内部串行，Orchestrator 视为单次调用）：

> **⚠️ 语言要求：论文正文必须使用中文撰写。** 章节标题使用中文（如"引言"、"方法"、"结果"、"讨论"），参考文献条目保留英文原文。

1. 标题 + 摘要（150-250 字，中文）
2. 引言（引用 core_papers，中文撰写）
3. 方法（基于 experiment_design + analysis_plan，中文撰写）
4. 结果（标记 `[TODO: 填入实验数据]`，中文撰写）
5. 讨论（引用 core_papers，讨论 research_gaps，中文撰写）
6. 参考文献（基于 core_papers 的 DOI，英文条目）

**期望响应格式：**

```json
{
  "status": "success",
  "output": {
    "file_path": "output/paper_draft.md",
    "sections_completed": ["title", "abstract", "introduction", "methods", "results", "discussion", "references"],
    "todo_count": 3,
    "word_count": 3500
  }
}
```

**Checkpoint 写入：**
```json
{
  "paper_file": "output/paper_draft.md",
  "sections_completed": ["title", "abstract", "introduction", "methods", "results", "discussion", "references"],
  "word_count": 3500
}
```

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" end
```

---

### Phase 4: 快速审稿自检（Parallel Fan-out，目标 ≤1.5min）

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" start "4.审稿自检"
```

**并行启动 3 个 reviewer-agent**（`run_in_background: true`）：

```json
// 3 个 Agent 共用同一输入结构，仅 role 不同
{
  "task_id": "<task_id>-review-<role>",
  "from": "orchestrator",
  "to": "reviewer-agent",
  "type": "execute",
  "payload": {
    "role": "methodologist | domain_expert | statistician",
    "paper_file": "output/paper_draft.md",
    "mode": "pipeline_quick"
  },
  "metadata": { "timeout_seconds": 90, "retry_count": 0 }
}
```

**期望响应格式（每个 Reviewer）：**

```json
{
  "status": "success",
  "output": {
    "role": "methodologist",
    "strengths": ["优点1", "优点2"],
    "weaknesses": [
      { "severity": "major", "issue": "问题描述", "suggestion": "改进建议" }
    ],
    "recommendation": "minor_revision",
    "confidence": 4
  }
}
```

**聚合（处理部分失败）：**

1. ≥2 个 Reviewer 成功 → 正常汇总
2. 仅 1 个成功 → 使用该结果，注明"仅单 Reviewer 意见"
3. 全部失败 → 标记 Phase 4 为 SKIPPED，输出论文草稿但无审稿意见

**Meta-Review 汇总逻辑（Orchestrator 执行）：**

1. 提取共识问题（≥2 个 Reviewer 提到的同一类问题）
2. 标记分歧点
3. 按 severity 排序：P0（所有人提到的 major）→ P1（单人 major）→ P2（minor）
4. 综合 recommendation 取最严格

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" end
```

---

### 完成判断标准（显式，不由 Agent 决定）

流水线在以下**全部条件满足**时标记为 SUCCESS：

- [ ] Phase 1 输出 ≥3 篇核心论文
- [ ] Phase 2a 输出包含 h0 和 h1
- [ ] Phase 3 输出文件 `output/paper_draft.md` 存在且 ≥1000 字
- [ ] `pipeline_state.json` 中 Phase 1-3 状态均为 SUCCESS

Phase 4（审稿）标记为 SKIPPED 时仍可判定整体 SUCCESS（审稿为非关键节点）。

---

### 生成用时报告

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" report
```

---

## 错误处理（4 级策略）

```
Level 1 — 自动重试
  触发：MCP 调用超时、单个数据源返回空
  策略：重试 1 次（间隔 2s）
  超限：升级为 Level 2

Level 2 — 降级处理
  触发：Phase 1 中 1-2 个数据源失败；Phase 4 中 1-2 个 Reviewer 失败
  策略：跳过失败节点（SKIPPED），用成功节点的结果继续
  记录：在 pipeline_state.json 的 skipped_sources 中记录

Level 3 — 人工介入
  触发：Phase 3（论文写作）失败；全部数据源不可用
  策略：暂停流水线，输出已完成部分 + 错误信息，等待用户决定

Level 4 — 全链路终止
  触发：超过 TIMEOUT_SECONDS（600s）；Agent 调用次数超过 MAX_AGENT_CALLS（12）
  策略：立即终止，输出已完成部分 + 用时报告
```

---

## 最终输出

### 1. 交付物

| 文件 | 内容 |
|------|------|
| `output/paper_draft.md` | 完整 IMRaD 论文草稿 |
| `output/pipeline_state.json` | 流水线状态 + 各阶段 checkpoint |

### 2. 终端输出

```markdown
# 科研流水线完成报告

## 状态: SUCCESS / PARTIAL / FAILED
- Phase 1 文献调研: SUCCESS (5 篇核心论文, 1 源跳过)
- Phase 2a 假设提炼: SUCCESS
- Phase 2b 实验+分析: SUCCESS
- Phase 3 论文写作: SUCCESS (3500 字)
- Phase 4 审稿自检: SUCCESS (3/3 Reviewer)

## 核心文献
| # | 论文 | 年份 | 引用 | 核心贡献 |
|---|------|------|------|---------|

## 研究假设
- H0: ...
- H1: ...

## 审稿建议: [Minor Revision]
### 改进项
- [ ] P0: ...
- [ ] P1: ...

## 论文草稿
已保存到 `output/paper_draft.md`

## 用时统计
[timer.py report 输出]
```
