---
name: paper-write
description: 论文写作——输入研究成果或大纲，按 IMRaD 结构串行生成论文草稿。
argument-hint: <research topic or outline>
user-invocable: true
---

# Paper Write — 串行论文写作

## 用户输入

研究主题/大纲: `$ARGUMENTS`

---

## 编排架构

```
┌───────────────────────────────────┐
│     Orchestrator (本 Skill)       │
│  Stage 1 → 2 → 3 → 4 → 5 → 6   │  ← Sequential Pipeline
├───────────────────────────────────┤
│     writing-agent (串行调用)       │
│     analysis-agent (Stage 4 协作) │
├───────────────────────────────────┤
│     State Store (paper_state.json)│
└───────────────────────────────────┘
```

## 终止条件

```
TIMEOUT_SECONDS  = 300    # 总超时 5 分钟
MAX_RETRIES      = 1      # 单节写作失败最大重试
```

---

## 执行流程

### Stage 1: 大纲生成

**输入（结构化）：**
```json
{
  "task_id": "paper-outline-<timestamp>",
  "from": "orchestrator",
  "to": "writing-agent",
  "type": "execute",
  "payload": {
    "task": "generate_outline",
    "research_topic": "$ARGUMENTS"
  },
  "metadata": { "timeout_seconds": 60 }
}
```

**期望响应：**
```json
{
  "status": "success",
  "output": {
    "title": "论文标题",
    "sections": [
      { "name": "introduction", "key_points": ["要点1", "要点2"] },
      { "name": "methods", "key_points": ["..."] },
      { "name": "results", "key_points": ["..."] },
      { "name": "discussion", "key_points": ["..."] }
    ],
    "figure_plan": ["图1描述", "图2描述"]
  }
}
```

**Checkpoint 写入**：保存大纲到 `output/paper_state.json`。

**暂停**：展示大纲，等待用户确认后继续。

### Stage 2-5: 逐节写作（Serial Pipeline）

每节按顺序生成。**信息蒸馏**：每个 Stage 只传入大纲 + 前一节的**摘要**（不传全文）。

**Stage 输入模板：**
```json
{
  "task_id": "paper-<section>-<timestamp>",
  "from": "orchestrator",
  "to": "writing-agent",
  "type": "execute",
  "payload": {
    "task": "write_section",
    "language": "zh-CN",
    "section": "introduction | methods | results | discussion",
    "outline": { /* Stage 1 的大纲 */ },
    "previous_section_summary": "前一节的 3 句话摘要",
    "references": [ /* 如有文献列表 */ ]
  },
  "metadata": { "timeout_seconds": 60 }
}
```

**Stage 4 (Results) 特殊处理：**

如有数据文件，先调用 analysis-agent：

```json
{
  "task_id": "paper-analysis-<timestamp>",
  "from": "orchestrator",
  "to": "analysis-agent",
  "type": "execute",
  "payload": {
    "task": "generate_results",
    "data_file": "<路径>",
    "hypothesis": { "h0": "...", "h1": "..." }
  }
}
```

将 analysis-agent 的统计结果（蒸馏后）传给 writing-agent 撰写 Results 节。

无数据时：Results 节标记 `[TODO: 填入实验数据]`。

**每节期望响应：**
```json
{
  "status": "success",
  "output": {
    "section": "introduction",
    "content": "该节完整 Markdown 内容",
    "summary": "3 句话摘要（供下一节使用）",
    "word_count": 600
  }
}
```

**每节完成后 Checkpoint 写入**：追加到 `paper_state.json`。

### Stage 6: Abstract（依赖全文信息）

```json
{
  "payload": {
    "task": "write_abstract",
    "all_sections_summary": {
      "introduction": "3 句话摘要",
      "methods": "3 句话摘要",
      "results": "3 句话摘要",
      "discussion": "3 句话摘要"
    }
  }
}
```

> **信息蒸馏**：传入各节摘要，不传全文。

### 组装输出

Orchestrator 将各节内容组装为完整论文，保存到 `output/paper_draft.md`。

---

## 完成判断标准

- [ ] `output/paper_draft.md` 文件存在
- [ ] 包含全部 6 节（标题、摘要、引言、方法、结果、讨论）
- [ ] 包含参考文献节
- [ ] 正文为中文（参考文献条目除外）
- [ ] 总字数 ≥ 1500 字

全部满足 → SUCCESS；缺少非关键节（References）→ SUCCESS + 标注；缺少关键节 → `needs_review`。

---

## 错误处理

```
Level 1 — 自动重试
  触发：单节写作超时或返回空
  策略：重试 1 次

Level 2 — 降级
  触发：Results 节的 analysis-agent 失败
  策略：Results 节全部标记 [TODO]，继续后续节

Level 3 — 人工介入
  触发：Introduction 或 Methods 节失败（关键节）
  策略：暂停，输出已完成部分，等待用户决定

Level 4 — 全局终止
  触发：超过 TIMEOUT_SECONDS / 连续 2 个关键节失败
  策略：写入 paper_state.json status=FAILED，组装已完成节输出部分草稿
```

---

## 输出

论文内容使用**中文**撰写，Markdown 格式，图片路径确保正确。

```markdown
# [中文标题]

## 摘要
[150-250 字，中文]

## 1. 引言
[中文撰写：研究背景 → 现有局限 → 动机 → 贡献]

## 2. 方法
[中文撰写：实验设计 → 数据采集 → 分析方法]

## 3. 结果
[中文撰写：统计结果 + [TODO] 占位]

## 4. 讨论
[中文撰写：结果解读 → 对比 → 局限 → 未来方向]

## 参考文献
[1] Author et al. (Year). Title. Venue. DOI （英文保留原文）
```

> **语言规则**：正文全部使用中文，章节标题使用中文，仅参考文献条目保留英文原文。

标记需要确认的内容为 `[TODO]` 或 `[VERIFY]`。
