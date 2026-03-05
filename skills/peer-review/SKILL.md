---
name: peer-review
description: 模拟同行评审——3 个角色 Reviewer 并行审稿，汇总综合评审意见。
argument-hint: <path to paper file or paste content>
user-invocable: true
---

# Peer Review — 并行多角色审稿

## 用户输入

论文文件路径或内容: `$ARGUMENTS`

---

## 编排架构

```
┌──────────────────────────────────────┐
│        Orchestrator (本 Skill)        │
├──────────┬───────────┬──────────────┤
│ reviewer │ reviewer  │   reviewer   │  ← Parallel Fan-out
│ (方法论) │ (领域)    │   (统计)     │
├──────────┴───────────┴──────────────┤
│       Meta-Review Aggregator        │  ← Orchestrator 执行
└──────────────────────────────────────┘
```

## 状态存储

```
STATE_FILE = output/review_state.json
```

Step 1 完成后写入 checkpoint（论文格式 + 字数），Step 2 每个 Reviewer 完成后更新其状态，Step 3 聚合后记录最终 recommendation。

## 终止条件

```
TIMEOUT_SECONDS  = 180    # 总超时 3 分钟
MAX_RETRIES      = 1      # 单 Reviewer 最大重试
```

---

## 执行流程

### Step 1: 获取论文内容（Orchestrator，确定性逻辑）

**路由规则（不依赖 LLM）：**
- 输入以 `.pdf` 结尾 → 调用 `pdf-reader-server` 的 `read_pdf` + `extract_paper_structure`
- 输入以 `.md` 结尾 → 调用 Read 工具直接读取
- 其他 → 视为文本内容直接使用

读取失败时：重试 1 次，仍失败则输出 `{"status": "failed", "reason": "论文读取失败"}`。

### Step 2: 并行审稿（Parallel Fan-out）

**同时启动 3 个 reviewer-agent**（`run_in_background: true`）。

**Agent 输入格式（结构化，3 个 Agent 共用结构，仅 role 不同）：**

```json
{
  "task_id": "review-<role>-<timestamp>",
  "from": "orchestrator",
  "to": "reviewer-agent",
  "type": "execute",
  "payload": {
    "role": "methodologist | domain_expert | statistician",
    "paper_content": "<论文内容（见蒸馏规则）>",
    "paper_file": "<文件路径（如有）>",
    "mode": "full"
  },
  "metadata": { "timeout_seconds": 120, "retry_count": 0 }
}
```

**信息蒸馏规则（Orchestrator 强制执行）：**
- 论文 ≤ 8000 字 → 传入全文
- 论文 > 8000 字 → 蒸馏后传入：
  ```json
  {
    "title": "论文标题",
    "section_titles": ["1. Introduction", "2. Methods", "3. Results", "4. Discussion"],
    "introduction_full": "Introduction 全文",
    "other_sections_summary": {
      "methods": "3 句话摘要",
      "results": "3 句话摘要",
      "discussion": "3 句话摘要"
    }
  }
  ```

**Agent 响应格式（结构化）：**

```json
{
  "task_id": "review-<role>-<timestamp>",
  "status": "success",
  "output": {
    "role": "methodologist",
    "summary": "1-2 句论文概述",
    "strengths": ["优点1", "优点2"],
    "weaknesses": [
      { "severity": "major", "issue": "问题描述", "suggestion": "改进建议" },
      { "severity": "minor", "issue": "问题描述", "suggestion": "改进建议" }
    ],
    "questions": ["需要作者回答的问题"],
    "recommendation": "accept | minor_revision | major_revision | reject",
    "confidence": 4
  }
}
```

### Step 3: Meta-Review 聚合（Orchestrator 执行）

**部分失败处理：**
- 3/3 成功 → 正常汇总
- 2/3 成功 → 汇总成功部分，注明缺失角色
- 1/3 成功 → 使用该结果，注明"仅单 Reviewer 意见，可信度有限"
- 0/3 成功 → 输出 `{"status": "failed", "reason": "所有 Reviewer 失败"}`

**聚合前蒸馏（Orchestrator 执行）：**

将各 Reviewer 完整输出蒸馏为共识摘要后再聚合：

```json
{
  "reviewer_summaries": [
    { "role": "methodologist", "recommendation": "minor_revision", "major_count": 1, "minor_count": 2, "confidence": 4 }
  ],
  "consensus_weaknesses": ["≥2 Reviewer 共同提到的问题"],
  "disagreements": ["recommendation 不一致的分歧点"]
}
```

**聚合逻辑（确定性，基于蒸馏摘要）：**

1. **共识问题提取**：≥2 个 Reviewer 提到的同类 weakness → 标记为 P0
2. **分歧检测**：recommendation 不一致时列出分歧点
3. **优先级排序**：P0（共识 major）→ P1（单人 major）→ P2（minor）
4. **综合 recommendation**：取最严格的 recommendation
5. **详情回查**：聚合完成后按 P0/P1 条目回查完整 weakness 描述和 suggestion

### Step 4: 输出

**完成判断标准：**
- [ ] ≥1 个 Reviewer 成功返回结构化结果
- [ ] 输出包含 recommendation + 至少 1 条 weakness

```markdown
# Peer Review Summary

## Meta-Review Decision
**Recommendation**: [Major Revision]
**Confidence**: [4/5]
**Reviewer 状态**: 3/3 成功

## Consensus Issues (≥2 Reviewer 一致)
1. **[P0]** [问题]: [描述] → [建议]

## Individual Reviews

### Reviewer 1 (Methodologist) — Confidence: 4/5
**Recommendation**: Minor Revision
**Strengths**: ...
**Weaknesses**: ...

### Reviewer 2 (Domain Expert) — Confidence: 3/5
...

### Reviewer 3 (Statistician) — Confidence: 4/5
...

## Action Items (按优先级)
- [ ] **P0**: [必须修改]
- [ ] **P1**: [强烈建议修改]
- [ ] **P2**: [建议改进]

## Rebuttal Template
| # | Reviewer | Issue | Suggested Response |
|---|---------|-------|--------------------|
| 1 | R1 | ... | ... |
```

---

## 错误处理

```
Level 1 — 自动重试
  触发：单个 Reviewer 超时
  策略：重试 1 次（间隔 2s）

Level 2 — 降级
  触发：1-2 个 Reviewer 失败
  策略：用成功 Reviewer 的结果继续，注明缺失角色

Level 3 — 人工介入
  触发：聚合后所有 weakness 均为 minor，但 recommendation 为 reject
  策略：输出完整审稿结果，请用户判断

Level 4 — 全局终止
  触发：全部 Reviewer 失败 / 论文读取失败 / 超过 TIMEOUT_SECONDS
  策略：写入 STATE_FILE status=FAILED，输出错误报告
```
