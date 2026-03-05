---
description: 实验设计——输入研究假设，生成完整实验方案（变量矩阵、样本量估算、统计方法、Protocol）。
---

# Experiment Design

ARGUMENTS: $ARGUMENTS

Execute the experiment-design skill from the ai-opensci plugin. Follow the instructions in the skill file at `skills/experiment-design/SKILL.md`.

**Orchestration Rules:**

1. **Structured Messages**: Agent input/output use JSON format as defined in SKILL.md
2. **Deterministic Routing** (hypothesis type by keyword matching, no LLM):
   - "A vs B" / "差异" / "比较" → RCT + t-test
   - "多组" / "多个" → Factorial + ANOVA
   - "前后" / "干预" → Pre-post + Mixed ANOVA
   - "关系" / "相关" / "影响" → Observational + Correlation/Regression
   - "剂量" / "梯度" → Gradient + Regression
   - No match → default RCT + t-test
3. **Termination**: TIMEOUT 120s, MAX_RETRIES 1
4. **Error Handling**:
   - L1: analysis-agent timeout → retry once
   - L2: Cannot parse IV/DV → ask user to clarify
5. **Completion Criteria** (explicit):
   - Output contains design_type
   - Output contains sample_size with n_per_group and total
   - Output contains ≥3 steps in statistical_plan
   - Output contains ≥4 steps in protocol

Pipeline:
1. Parse hypothesis: extract IV, DV, controls, direction
2. Route to design type by keyword matching
3. Send to analysis-agent for full experiment design
4. Output structured experiment plan
