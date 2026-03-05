---
description: 论文写作——按 IMRaD 结构串行生成论文草稿，信息蒸馏传递，带 checkpoint。
---

# Paper Write

ARGUMENTS: $ARGUMENTS

Execute the paper-write skill from the ai-opensci plugin. Follow the instructions in the skill file at `skills/paper-write/SKILL.md`.

**Orchestration Rules:**

1. **Structured Messages**: All Agent inputs/outputs use JSON format as defined in SKILL.md
2. **Information Distillation**: Each stage only receives outline + previous section's 3-sentence summary, NOT full text
3. **State**: Maintain `output/paper_state.json` with checkpoint after each section
4. **Termination**: TIMEOUT 300s, MAX_RETRIES 1 per section
5. **Error Handling**:
   - L1: Single section timeout → retry once
   - L2: Results analysis-agent fails → mark Results as [TODO], continue
   - L3: Introduction or Methods fails → pause, show completed parts
6. **Completion Criteria** (explicit):
   - `output/paper_draft.md` exists
   - Contains all 6 sections (Title, Abstract, Intro, Methods, Results, Discussion)
   - Contains References section
   - Total ≥1500 words
7. **User Confirmation**: Pause after outline (Stage 1) for user approval
8. **Language**: 论文正文必须使用中文撰写。章节标题用中文（"引言"而非"Introduction"）。仅参考文献条目保留英文。每次 Agent 调用必须包含 `"language": "zh-CN"`

Pipeline:
1. Generate outline → pause for confirmation
2. Write sections serially: 引言 → 方法 → 结果 → 讨论 → 摘要
3. Each section passes 3-sentence summary to next (distillation)
4. Assemble into `output/paper_draft.md`（中文论文）
