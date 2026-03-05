---
description: 全流水线科研编排——从文献调研到论文写作，4 Phase 并行架构，10分钟内生成完整论文。
---

# Research Pipeline

ARGUMENTS: $ARGUMENTS

Execute the research-pipeline skill from the ai-opensci plugin. Follow the instructions in the skill file at `skills/research-pipeline/SKILL.md`.

**CRITICAL**:
- You MUST call the timer script at the start and end of EVERY phase
- You MUST NOT pause for user confirmation between phases — run the full pipeline automatically
- Target completion: ≤10 minutes total

Timer commands:
- Pipeline start: `python3 scripts/timer.py start-pipeline`
- Phase start: `python3 scripts/timer.py start "phase_name"`
- Phase end: `python3 scripts/timer.py end`
- Final report: `python3 scripts/timer.py report`

Pipeline phases (4-phase architecture):
1. Literature Review (parallel 3-source search) → auto-continue
2. Hypothesis + Experiment Design + Analysis Plan (hypothesis serial → design+analysis parallel) → auto-continue
3. Paper Writing (full IMRaD draft in Chinese, save to output/paper_draft.md) → auto-continue
4. Quick Peer Review (parallel 3-role, concise output) → timing report

Key optimizations:
- Zero pauses: no user confirmation between phases
- Max parallelism: 3 parallel searches, 2 parallel design agents, 3 parallel reviewers
- Lean depth: no citation chasing, 8 results per source, concise reviews
- Auto hypothesis selection: pick the most feasible one without asking
