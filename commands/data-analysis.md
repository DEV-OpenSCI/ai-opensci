---
description: 数据分析——给定数据文件，自动探索、统计分析、生成可视化和可复现 Python 脚本。
---

# Data Analysis

ARGUMENTS: $ARGUMENTS

Execute the data-analysis skill from the ai-opensci plugin. Follow the instructions in the skill file at `skills/data-analysis/SKILL.md`.

**Orchestration Rules:**

1. **Structured Messages**: Agent input/output use JSON format as defined in SKILL.md
2. **Deterministic Routing** (file extension, no LLM):
   - `.csv` → `pd.read_csv()`
   - `.xlsx/.xls` → `pd.read_excel()`
   - `.json` → `pd.read_json()`
   - `.tsv` → `pd.read_csv(sep='\t')`
   - other → error with supported formats list
3. **Termination**: TIMEOUT 180s, MAX_RETRIES 2 for script execution
4. **Validation**: After script generation, execute and verify exit code + output files
5. **Error Handling**:
   - L1: Script execution error → pass stderr back to agent, retry (max 2)
   - L2: Visualization fails → skip figures, output stats + script only
   - L3: File not found / unparseable → terminate with error
6. **Completion Criteria** (explicit):
   - `output/scripts/analysis.py` exists and executable
   - Script contains `np.random.seed(42)` and full imports
   - Statistical results include p-value + effect size
   - ≥1 figure generated in `output/figures/`

Pipeline:
1. Validate input file exists and determine load method
2. Send to analysis-agent for EDA + statistics + visualization
3. Validate: execute generated script, check exit code and outputs
4. Output: analysis report + script + figures
