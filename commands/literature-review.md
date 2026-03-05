---
description: 文献调研——通过 Semantic Scholar、Elicit、Consensus 三源并行搜索，筛选 5-8 篇高质量核心论文。展示并行 Agent 编排 + MCP Server。
---

# Literature Review

ARGUMENTS: $ARGUMENTS

Execute the literature-review skill from the ai-opensci plugin. Follow the instructions in the skill file at `skills/literature-review/SKILL.md`.

Key steps:
1. Parse research question into keyword/question/query forms for 3 data sources
2. Launch 3 parallel agents:
   - Agent A: Semantic Scholar (keyword search + citation tracking)
   - Agent B: Elicit (research question search + quality filtering)
   - Agent C: Consensus (question search + stance extraction)
3. Merge, deduplicate (by DOI), and quality-filter results
4. Select 5-8 core papers with cross-source validation
5. Generate report with stance analysis and research gaps
