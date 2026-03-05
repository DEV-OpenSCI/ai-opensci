---
description: 模拟同行评审——3 个角色 Reviewer 并行审稿，结构化输出，汇总综合评审意见。
---

# Peer Review

ARGUMENTS: $ARGUMENTS

Execute the peer-review skill from the ai-opensci plugin. Follow the instructions in the skill file at `skills/peer-review/SKILL.md`.

**Orchestration Rules:**

1. **Structured Messages**: All Reviewer inputs/outputs use JSON format as defined in SKILL.md
2. **Deterministic Routing** (input type detection, no LLM):
   - `.pdf` → use pdf-reader-server MCP
   - `.md` → use Read tool
   - other → treat as text content
3. **Termination**: TIMEOUT 180s, MAX_RETRIES 1 per reviewer
4. **Error Handling**:
   - L1: Single reviewer timeout → retry once
   - L2: 1-2 reviewers fail → aggregate successful ones, note missing roles
   - L3: All reviewers or paper reading fails → output error
5. **Partial Failure**: ≥2 reviewers → full Meta-Review; 1 reviewer → note limited confidence
6. **Completion Criteria** (explicit):
   - ≥1 reviewer succeeded with structured output
   - Output contains recommendation + ≥1 weakness
7. **Aggregation Logic** (deterministic):
   - P0: ≥2 reviewers report same major issue
   - P1: Single reviewer major issue
   - P2: Minor issues
   - Recommendation: take strictest among reviewers

Pipeline:
1. Read paper content (deterministic format routing)
2. Launch 3 parallel reviewer-agents (methodologist / domain_expert / statistician)
3. Meta-Review aggregation: consensus issues → priority sort → recommendation
4. Output structured review + action items + rebuttal template
