---
description: 模拟同行评审——3个不同角色 Reviewer 并行审稿，汇总综合评审意见。展示并行多角色 Agent。
---

# Peer Review

ARGUMENTS: $ARGUMENTS

Execute the peer-review skill from the ai-opensci plugin. Follow the instructions in the skill file at `skills/peer-review/SKILL.md`.

Key steps:
1. Read paper content (via PDF reader MCP if file path given)
2. Launch 3 parallel reviewer agents: Methodologist, Domain Expert, Statistician
3. Collect all reviews and act as Meta-Reviewer
4. Generate consolidated review with action items and rebuttal template
