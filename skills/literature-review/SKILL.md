---
name: literature-review
description: 文献调研——输入研究问题，通过 Semantic Scholar、Elicit、Consensus 三源并行搜索，筛选 5-8 篇高质量核心论文。
argument-hint: <research question or keywords>
user-invocable: true
---

# Literature Review — 三源并行文献调研

## 用户输入

研究问题或关键词: `$ARGUMENTS`

---

## 编排架构

```
┌─────────────────────────────────────┐
│       Orchestrator (本 Skill)       │
├────────────┬───────────┬───────────┤
│ lit-agent  │ lit-agent │ lit-agent │  ← Parallel Fan-out
│ (Scholar)  │ (Elicit)  │(Consensus)│
├────────────┴───────────┴───────────┤
│   Aggregator (去重 + 筛选 + 保存)   │  ← Orchestrator 执行
└─────────────────────────────────────┘
```

## 状态存储

```
STATE_FILE = output/literature_state.json
```

每步完成后写入 checkpoint：
- Step 2 完成：记录各源状态（SUCCESS/FAILED）和返回论文数
- Step 3 完成：记录聚合结果摘要（`{paper_count, top_score, gaps_count}`）
- Step 4 完成：记录保存状态

## 终止条件

```
TIMEOUT_SECONDS  = 180    # 总超时 3 分钟
MAX_RETRIES      = 1      # 单源最大重试
```

---

## 执行流程

### Step 1: 输入转化（Orchestrator，确定性逻辑）

将 `$ARGUMENTS` 转化为三种检索形式：

```json
{
  "keywords": "核心术语（给 Semantic Scholar）",
  "research_question": "完整研究问题（给 Elicit）",
  "answerable_query": "可回答的问句（给 Consensus）"
}
```

### Step 2: 三源并行检索（Parallel Fan-out）

**同时**启动 3 个 literature-agent（`run_in_background: true`）。

**Agent 输入格式（结构化）：**

```json
{
  "task_id": "lit-<source>-<timestamp>",
  "from": "orchestrator",
  "to": "literature-agent",
  "type": "execute",
  "payload": {
    "source": "semantic_scholar | elicit | consensus",
    "query": "<对应版本的检索词>",
    "limit": 8,
    "exclude_preprints": true
  },
  "metadata": { "timeout_seconds": 120, "retry_count": 0 }
}
```

**Agent 响应格式（结构化）：**

```json
{
  "task_id": "lit-<source>-<timestamp>",
  "status": "success | failed",
  "output": {
    "papers": [
      {
        "title": "...", "authors": "...", "year": 2024,
        "venue": "...", "citations": 156, "doi": "...",
        "abstract_summary": "1-2 句核心发现",
        "type": "empirical | meta_analysis | review | frontier",
        "takeaway": "支持/反对/中立（仅 Consensus 源）"
      }
    ],
    "source": "semantic_scholar | elicit | consensus",
    "result_count": 8
  },
  "error": null
}
```

### Step 2.5: 信息蒸馏（Orchestrator 执行）

Agent 返回完整 papers 数组后，Orchestrator 在传入聚合器前蒸馏为摘要：

```json
{
  "source": "semantic_scholar",
  "status": "success",
  "paper_count": 8,
  "papers_summary": [
    { "title": "...", "doi": "...", "citations": 156, "type": "empirical", "key_contribution": "1 句话" }
  ]
}
```

> **蒸馏规则**：只传递 `title, doi, citations, type, key_contribution`，不传完整 abstract/authors/venue 到聚合步骤。聚合完成后按需回查完整元数据。

### Step 3: 聚合（Orchestrator 执行，处理部分失败）

**部分失败处理：**
- 3/3 成功 → 正常聚合
- 2/3 成功 → 聚合成功源，在报告中标注失败源
- 1/3 成功 → 使用该源结果，降低筛选标准（引用数阈值降至 ≥3）
- 0/3 成功 → 输出 `{"status": "failed", "reason": "所有数据源不可用"}`

**聚合逻辑（确定性）：**

1. 按 DOI 去重（无 DOI 则按标题模糊匹配）
2. 评分排序：多源命中 +3 分 / 引用数 ≥50 +2 分 / 近 2 年 +1 分 / Meta-Analysis +1 分
3. 取 Top 5-8 篇
4. 提取立场分析（来自 Consensus 的 takeaway）
5. 从未覆盖区域识别 Research Gap

### Step 4: 保存到本地

调用 `paper-store` 的 `save_papers_batch`：

```json
{
  "papers": [
    {
      "title": "...", "authors": "...", "year": 2024,
      "abstract": "...", "doi": "...", "venue": "...",
      "citations": 156, "source": "Semantic Scholar + Elicit",
      "takeaway": "..."
    }
  ]
}
```

保存失败时：重试 1 次，仍失败则跳过保存（SKIPPED），报告中注明。

### Step 5: 输出报告

**完成判断标准（显式）：**
- [ ] 至少 3 篇论文入选
- [ ] 至少识别 1 个 Research Gap
- [ ] 论文列表中每篇包含 title + year + contribution

全部满足 → 输出报告；否则标记 `needs_review`。

**输出格式：**

```markdown
# 文献调研报告: [研究主题]

## 数据源状态
| 数据源 | 状态 | 返回数量 |
|--------|------|---------|
| Semantic Scholar | SUCCESS | 8 |
| Elicit | SUCCESS | 6 |
| Consensus | SKIPPED (API key 不可用) | 0 |

## 研究现状概述
[2-3 段总结]

## 核心论文 (5-8 篇)
| # | 论文标题 | 年份 | 引用 | 类型 | 核心贡献 | 数据源 |
|---|---------|------|------|------|---------|--------|

## 论文立场分析
- **支持**: N 篇 — [摘要]
- **反对/质疑**: N 篇 — [摘要]
- **条件性结论**: N 篇 — [摘要]

## 研究空白 (Research Gaps)
1. [Gap 1]: 描述 + 依据
2. [Gap 2]: 描述 + 依据

## 推荐阅读顺序
1. 先读综述 → 建立全景
2. 再读核心实证 → 理解方法
3. 最后读前沿工作 → 把握进展

## 参考文献
[APA 格式，含 DOI]

## 本地文献库
已保存 N 篇论文到 `~/ai-opensci-papers/`
```

---

## 错误处理

```
Level 1 — 自动重试
  触发：MCP 调用超时、返回空结果
  策略：重试 1 次（间隔 2s）

Level 2 — 降级处理
  触发：1-2 个数据源失败
  策略：跳过失败源，用剩余源继续，报告中注明

Level 3 — 人工介入
  触发：聚合后论文数 < 3 且无法自动扩展
  策略：输出已有结果 + 建议用户调整关键词

Level 4 — 全局终止
  触发：全部源失败 / 超过 TIMEOUT_SECONDS
  策略：写入 STATE_FILE status=FAILED，输出错误报告，不编造结果
```
