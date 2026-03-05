---
name: data-analysis
description: 数据分析——给定数据文件，自动探索、统计分析、生成可视化和完整 Python 脚本。
argument-hint: <path to data file>
user-invocable: true
---

# Data Analysis — 自动化数据分析

## 用户输入

数据文件路径: `$ARGUMENTS`

---

## 编排架构

```
┌──────────────────────────────────┐
│     Orchestrator (本 Skill)      │
│  验证输入 → 分析 → 验证输出      │  ← Sequential (单 Agent + 验证)
├──────────────────────────────────┤
│         analysis-agent           │
├──────────────────────────────────┤
│    Validator (脚本执行校验)       │  ← Orchestrator 执行
└──────────────────────────────────┘
```

## 状态存储

```
STATE_FILE = output/analysis_state.json
```

Step 1 完成后写入 checkpoint（文件类型 + 加载方式），Step 2 完成后记录分析结果摘要，Step 3 每次验证迭代更新 retry_count 和 last_error。

## 终止条件

```
TIMEOUT_SECONDS  = 180    # 总超时 3 分钟
MAX_RETRIES      = 2      # 脚本执行失败最大重试
```

---

## 执行流程

### Step 1: 输入验证（Orchestrator，确定性逻辑）

**路由规则（不依赖 LLM）：**

| 文件扩展名 | 加载方式 |
|-----------|---------|
| `.csv` | `pd.read_csv()` |
| `.xlsx` / `.xls` | `pd.read_excel()` |
| `.json` | `pd.read_json()` |
| `.tsv` | `pd.read_csv(sep='\t')` |
| 其他 | 报错，请用户提供支持的格式 |

验证文件存在且可读，不存在则输出 `{"status": "failed", "reason": "文件不存在: <路径>"}`。

### Step 2: 数据分析（analysis-agent）

**Agent 输入：**

```json
{
  "task_id": "analysis-<timestamp>",
  "from": "orchestrator",
  "to": "analysis-agent",
  "type": "execute",
  "payload": {
    "task": "full_analysis",
    "data_file": "$ARGUMENTS",
    "load_method": "csv | excel | json",
    "output_dir": "output/"
  },
  "metadata": { "timeout_seconds": 150, "retry_count": 0 }
}
```

**Agent 内部执行步骤：**

1. 加载数据 → 生成 EDA 概览（shape / dtypes / missing / describe）
2. 识别变量类型（连续 / 分类）
3. 正态性检验 → 选择参数/非参数方法
4. 执行假设检验 + 效应量计算
5. 生成可视化（分布图 / 箱线图 / 相关热力图 / 对比图）
6. 保存脚本到 `output/scripts/analysis.py`
7. 保存图表到 `output/figures/`

**Agent 响应：**

```json
{
  "status": "success",
  "output": {
    "data_overview": {
      "shape": [100, 5],
      "columns": ["col1", "col2", "col3", "col4", "col5"],
      "missing_values": { "col1": 0, "col3": 3 },
      "dtypes": { "col1": "float64", "col2": "object" }
    },
    "statistical_results": [
      {
        "test": "Independent t-test",
        "statistic": 2.45,
        "p_value": 0.016,
        "effect_size": { "metric": "Cohen's d", "value": 0.72 },
        "ci_95": [0.15, 1.29],
        "conclusion": "组间差异显著，中等效应量"
      }
    ],
    "figures": ["output/figures/distribution.png", "output/figures/comparison.png"],
    "script": "output/scripts/analysis.py"
  }
}
```

### Step 3: 验证（Orchestrator 执行）

**验证逻辑（确定性）：**

1. 检查 `output/scripts/analysis.py` 是否存在
2. 执行脚本：`python3 output/scripts/analysis.py`
3. 检查 exit code = 0
4. 检查 `output/figures/` 下至少生成 1 个 `.png` 文件

**验证失败处理：**
- 脚本报错 → 蒸馏 stderr 为结构化错误摘要后传回 analysis-agent：
  ```json
  { "error_type": "ImportError", "message": "No module named 'seaborn'", "line": 12 }
  ```
  不传完整 stderr，仅传第一个错误的类型、消息和行号。重试最多 2 次。
- 无图表输出 → 标记为 `needs_review`，脚本和报告仍正常输出

### Step 4: 输出

**完成判断标准：**
- [ ] `output/scripts/analysis.py` 存在且可执行
- [ ] 脚本包含 `np.random.seed(42)`
- [ ] 脚本包含完整 import 语句
- [ ] 统计结果包含 p 值和效应量
- [ ] 至少生成 1 个图表文件

```markdown
# 数据分析报告

## 数据概览
- 样本量: N = 100
- 变量: 5 列（3 连续 + 2 分类）
- 缺失值: col3 有 3 个缺失

## 统计分析结果
| 检验 | 统计量 | p 值 | 效应量 | 95% CI | 结论 |
|------|--------|------|--------|--------|------|
| Independent t-test | t=2.45 | 0.016* | d=0.72 | [0.15, 1.29] | 显著 |

## 可视化
![分布图](output/figures/distribution.png)
![对比图](output/figures/comparison.png)

## 分析脚本
完整脚本: `output/scripts/analysis.py`

## 结论与建议
[基于数据的客观结论，区分统计显著性和实际意义]
```

---

## 错误处理

```
Level 1 — 自动重试
  触发：脚本执行报错（ImportError / TypeError 等）
  策略：分析 stderr，修正脚本后重试（最多 2 次）

Level 2 — 降级
  触发：可视化生成失败（matplotlib 配置问题）
  策略：跳过图表，仅输出统计结果和脚本

Level 3 — 人工介入
  触发：数据格式可解析但变量含义不明确
  策略：输出 EDA 概览，请用户指定目标变量

Level 4 — 全局终止
  触发：数据文件不存在 / 格式完全无法解析 / 超过 TIMEOUT_SECONDS
  策略：写入 STATE_FILE status=FAILED，输出错误报告
```
