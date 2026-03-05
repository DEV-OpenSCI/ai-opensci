---
description: 论文写作——输入研究成果或大纲，按 IMRaD 结构串行生成论文草稿。展示串行 Agent 编排。
---

# Paper Write

ARGUMENTS: $ARGUMENTS

Execute the paper-write skill from the ai-opensci plugin. Follow the instructions in the skill file at `skills/paper-write/SKILL.md`.

Key steps:
1. Generate outline → wait for user confirmation
2. Write Introduction → Methods → Results → Discussion → Abstract (serial pipeline)
3. Each stage builds on the previous stage's output
4. Mark uncertain content with [TODO] or [VERIFY]
