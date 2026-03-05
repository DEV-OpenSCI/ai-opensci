---
description: 文献调研——通过 Semantic Scholar、Elicit、Consensus 三源并行搜索，筛选 5-8 篇高质量核心论文。
---

# Literature Review

ARGUMENTS: $ARGUMENTS

Execute the literature-review skill from the ai-opensci plugin. Follow the instructions in the skill file at `skills/literature-review/SKILL.md`.

**Orchestration Rules:**

1. **Structured Messages**: All Agent inputs/outputs use JSON format as defined in SKILL.md
2. **Termination**: TIMEOUT 180s, MAX_RETRIES 1 per source
3. **Error Handling**:
   - L1: Auto-retry MCP timeout once (2s delay)
   - L2: 1-2 sources fail → skip failed, continue with rest
   - L3: All sources fail → output error, do NOT fabricate results
4. **Completion Criteria** (explicit):
   - ≥3 papers selected
   - ≥1 Research Gap identified
   - Each paper has title + year + contribution
5. **Partial Failure**: Report data source status table (SUCCESS/SKIPPED per source)

Pipeline:
1. Convert research question to 3 query forms (keywords / question / answerable query)
2. Launch 3 parallel literature-agents (run_in_background: true)
3. Aggregate: deduplicate by DOI → score & rank → select top 5-8
4. Save to paper-store via save_papers_batch
5. Output report with stance analysis + research gaps
