---
name: research-pipeline
description: 全流水线科研编排——从文献调研到论文写作，串联所有环节，统计每阶段用时。展示完整串行+并行混合编排。
argument-hint: <research question>
user-invocable: true
---

# Research Pipeline — 全流程科研流水线（10分钟内完成）

你将执行一次完整的科研流水线，从文献调研到论文生成，**全程自动化、无需等待用户确认**，目标在 10 分钟内完成。

## 用户输入

研究问题: `$ARGUMENTS`

## 计时器使用

在每个阶段的开始和结束时，使用 Bash 调用计时器脚本：

```bash
# 流水线开始
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" start-pipeline

# 每个阶段开始
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" start "阶段名称"

# 每个阶段结束
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" end

# 最终报告
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" report
```

**重要**: 你必须在每个 Phase 开始前调用 `start`，结束后调用 `end`，最后调用 `report` 生成统计。

## 核心优化策略

1. **零等待**: 全程不暂停，自动流转到下一阶段
2. **最大并行**: 独立阶段同时执行（文献三源并行、实验+分析并行、三角色并行审稿）
3. **精简深度**: 文献搜索不追引用链，每源限 8 篇；论文直接生成完整草稿
4. **轻量 Agent**: 非核心阶段用 sonnet 模型

## 执行流程（4 Phase 架构）

```
Phase 1: 文献调研 (3源并行)
    ↓ 自动流转
Phase 2: 假设提炼 + 实验设计 + 数据分析方案 (假设串行 → 实验&分析并行)
    ↓ 自动流转
Phase 3: 论文写作 (完整 IMRaD 草稿)
    ↓ 自动流转
Phase 4: 快速审稿自检 (3角色并行)
    ↓
最终报告
```

---

### 启动流水线

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" start-pipeline
```

---

### Phase 1: 文献调研（目标 ≤2.5 分钟）

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" start "1.文献调研"
```

**并行启动 3 个 Agent**（全部设 `run_in_background: true`）:

#### Agent A — Semantic Scholar
```
使用 scholar-server MCP:
1. search_papers(query=关键词, limit=8)
2. 返回论文列表（标题、年份、引用数、摘要）
注意: 不追引用链，节省时间
```

#### Agent B — Elicit
```
使用 elicit-server MCP:
1. search_papers(query=研究问题, max_results=8)
注意: 不限制 quartile，加速返回
```

#### Agent C — Consensus
```
使用 consensus-server MCP:
1. search_papers(query=问句, exclude_preprints=true)
2. 提取每篇论文的 takeaway
```

**等待 3 个 Agent 全部返回后**:
- 按标题/DOI 去重
- 快速筛选 5-8 篇核心论文（优先多源命中、高引用、近年）
- 识别 2-3 个 Research Gap

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" end
```

**不暂停，直接进入 Phase 2**

---

### Phase 2: 假设 + 实验 + 分析（目标 ≤2.5 分钟）

#### Step 2a: 假设提炼（串行，~30秒）

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" start "2a.假设提炼"
```

- 从 Research Gap 中**自动选择最具可行性的 1 个假设**
- 明确 H0 和 H1
- 不等待用户确认，直接推进

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" end
```

#### Step 2b: 实验设计 + 数据分析方案（并行）

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" start "2b.实验设计+分析方案"
```

**同时启动 2 个 Agent**（`run_in_background: true`）:

##### Agent D — 实验设计
```
根据假设生成精简实验方案:
- 设计类型、自变量、因变量
- 变量矩阵（简表）
- 样本量估算（一句话）
- 实验流程（5步以内）
```

##### Agent E — 数据分析方案
```
根据假设预设分析流程:
- 推荐统计方法（1-2种）
- 可视化方案（2-3种图表）
- 效应量指标
```

等待两个 Agent 返回后合并结果。

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" end
```

**不暂停，直接进入 Phase 3**

---

### Phase 3: 论文写作（目标 ≤3.5 分钟）

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" start "3.论文写作"
```

基于前面所有阶段的输出，**直接生成完整 IMRaD 论文草稿**（中文撰写）。

串行生成各节（每节输出是下一节的上下文）:

1. **Title + Abstract** — 标题 + 150-250 字摘要
2. **Introduction** — 研究背景、现有方法局限、研究动机与贡献（引用文献调研中的论文）
3. **Methods** — 实验设计、数据采集方案、统计分析计划
4. **Results** — 预期结果描述、图表占位说明（标记 `[TODO: 填入实验数据]`）
5. **Discussion** — 结果解读、与已有工作对比、局限性、未来方向
6. **References** — 基于文献调研的参考文献列表

**输出为单个 Markdown 文件**，保存到工作目录下 `output/paper_draft.md`。

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" end
```

**不暂停，直接进入 Phase 4**

---

### Phase 4: 快速审稿自检（目标 ≤1.5 分钟）

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" start "4.审稿自检"
```

**并行启动 3 个 Agent**（`run_in_background: true`），对论文草稿进行快速审稿:

#### Reviewer 1 — 方法论专家
```
重点: 实验设计合理性、统计方法、可复现性
输出: 3-5 条核心意见，每条 1-2 句话
```

#### Reviewer 2 — 领域专家
```
重点: 新颖性、与前沿的关系、实际应用价值
输出: 3-5 条核心意见，每条 1-2 句话
```

#### Reviewer 3 — 统计专家
```
重点: 数据分析正确性、效应量、统计功效
输出: 3-5 条核心意见，每条 1-2 句话
```

等待 3 个 Reviewer 返回后，汇总为:
- **综合建议**: Accept / Minor Revision / Major Revision / Reject
- **共识问题**（多人提到的）
- **P0/P1/P2 改进项**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" end
```

---

### 生成用时报告

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/timer.py" report
```

---

## 最终输出

输出 3 部分内容:

### 1. 流水线摘要
```markdown
# 科研流水线完成报告

## 研究问题
[用户输入的问题]

## 核心文献 (5-8 篇)
| # | 论文 | 年份 | 引用 | 核心贡献 |
|---|------|------|------|---------|

## 研究假设
- H0: ...
- H1: ...

## 实验设计要点
[精简方案]

## 论文草稿
已保存到 `output/paper_draft.md`
```

### 2. 审稿自检结果
```markdown
## 审稿建议: [Major/Minor Revision]
### 改进项
- [ ] P0: ...
- [ ] P1: ...
- [ ] P2: ...
```

### 3. 用时统计
```
============================================================
  PIPELINE TIMING REPORT
============================================================

  1. 1.文献调研           ████████████░░░░░░░░   2m 15s  (25%)
  2. 2a.假设提炼          ███░░░░░░░░░░░░░░░░░     28s   (5%)
  3. 2b.实验设计+分析方案  ██████████░░░░░░░░░░   1m 45s  (19%)
  4. 3.论文写作           █████████████████░░░░   3m 10s  (35%)
  5. 4.审稿自检           ████████░░░░░░░░░░░░░   1m 22s  (15%)

  TOTAL                                          9m 00s  (100%)
============================================================
```

## 演示要点

- **10 分钟完成全流程**: 传统科研这些步骤可能需要数周，AI 流水线 10 分钟内完成
- **4 Phase 架构**: 比原始 6 Stage 减少 33% 的阶段切换开销
- **3 次并行编排**: Phase 1 三源搜索 + Phase 2b 实验&分析 + Phase 4 三角色审稿
- **零等待自动流转**: 全程无需用户干预，一键到底
- **完整交付物**: 文献报告 + 实验方案 + 论文草稿 + 审稿意见
