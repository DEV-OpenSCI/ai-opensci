---
description: 全流水线科研编排——4 Phase 并行架构，结构化接口，状态持久化，10分钟内生成完整论文。
---

# Research Pipeline

ARGUMENTS: $ARGUMENTS

Execute the research-pipeline skill from the ai-opensci plugin. Follow the instructions in the skill file at `skills/research-pipeline/SKILL.md`.

**CRITICAL — Orchestration Rules:**

1. **Timer**: Call timer script at start/end of EVERY phase
   - `python3 scripts/timer.py start-pipeline`
   - `python3 scripts/timer.py start "phase_name"`
   - `python3 scripts/timer.py end`
   - `python3 scripts/timer.py report`

2. **State**: Initialize and maintain `output/pipeline_state.json`
   - Write checkpoint after each phase (distilled output only)
   - Track status: PENDING → RUNNING → SUCCESS/FAILED/SKIPPED

3. **Structured Messages**: All Agent inputs/outputs use JSON format as defined in SKILL.md
   - Do NOT pass natural language between agents
   - Distill information: only pass summaries + key fields, never full upstream output

4. **Termination Conditions**:
   - TIMEOUT: 600 seconds total
   - MAX_RETRIES: 2 per node
   - MAX_AGENT_CALLS: 12 total

5. **Error Handling** (4 levels):
   - L1: Auto-retry (MCP timeout) — retry once after 2s
   - L2: Degrade (1-2 sources fail in fan-out) — skip failed, continue with rest
   - L3: Human intervention (critical node fails) — pause, show completed parts
   - L4: Full stop (timeout/budget exceeded) — terminate, output what's done

6. **Completion Criteria** (explicit, do NOT let agents decide):
   - Phase 1: ≥3 core papers
   - Phase 2a: h0 + h1 present
   - Phase 3: paper_draft.md exists and ≥1000 words
   - Phase 4: ≥1 reviewer succeeded (SKIPPABLE)

7. **Zero Pauses**: Run full pipeline without user confirmation between phases
