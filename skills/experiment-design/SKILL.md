---
name: experiment-design
description: 实验设计助手——输入研究假设，生成完整实验方案（变量、对照、样本量、统计方法）。
argument-hint: <research hypothesis>
user-invocable: true
---

# Experiment Design — 实验方案生成

## 用户输入

研究假设: `$ARGUMENTS`

---

## 编排架构

```
┌──────────────────────────────────┐
│     Orchestrator (本 Skill)      │
│  解析假设 → 生成方案 → 输出      │  ← Sequential (单 Agent)
├──────────────────────────────────┤
│         analysis-agent           │
└──────────────────────────────────┘
```

本 Skill 为单 Agent 顺序执行，无并行编排。

## 状态存储

```
STATE_FILE = output/experiment_state.json
```

Step 1 完成后写入 checkpoint（解析结果 + 路由类型），Step 2 完成后更新为 SUCCESS/FAILED。

## 终止条件

```
TIMEOUT_SECONDS  = 120    # 总超时 2 分钟
MAX_RETRIES      = 1      # 失败最大重试
```

---

## 执行流程

### Step 1: 解析假设（Orchestrator，确定性逻辑）

从 `$ARGUMENTS` 中提取结构化信息：

```json
{
  "hypothesis_text": "$ARGUMENTS",
  "iv": "自变量（被操控的变量）",
  "dv": "因变量（被测量的结果）",
  "controls": ["控制变量1", "控制变量2"],
  "direction": "one-tailed | two-tailed"
}
```

**假设类型路由（确定性，不依赖 LLM）：**

| 关键词信号 | 假设类型 | 推荐设计 | 统计方法 |
|-----------|---------|---------|---------|
| "A vs B"、"差异"、"比较" | 两组差异 | RCT | t-test / Mann-Whitney |
| "多组"、"多个"、"各组" | 多组比较 | 析因设计 | ANOVA |
| "前后"、"干预"、"处理前后" | 因果关系 | 前后对照 + 对照组 | Mixed ANOVA |
| "关系"、"相关"、"影响" | 相关性 | 观察性研究 | 相关/回归 |
| "剂量"、"浓度"、"梯度" | 剂量效应 | 梯度设计 | 回归分析 |
| 未匹配 | 默认 | RCT | t-test |

### Step 2: 生成实验设计（analysis-agent）

**Agent 输入：**

```json
{
  "task_id": "exp-design-<timestamp>",
  "from": "orchestrator",
  "to": "analysis-agent",
  "type": "execute",
  "payload": {
    "task": "experiment_design",
    "hypothesis": {
      "h0": "零假设",
      "h1": "备择假设",
      "iv": "...", "dv": "...", "controls": ["..."],
      "direction": "two-tailed"
    },
    "recommended_design": "RCT",
    "recommended_test": "Independent t-test"
  },
  "metadata": { "timeout_seconds": 90, "retry_count": 0 }
}
```

**Agent 响应：**

```json
{
  "status": "success",
  "output": {
    "design_type": "2x2 混合设计",
    "variables": {
      "iv": [{ "name": "...", "levels": ["Level1", "Level2"] }],
      "dv": [{ "name": "...", "measure": "量表/行为指标" }],
      "controls": ["控制变量1", "控制变量2"]
    },
    "sample_size": {
      "effect_size": "d = 0.5 (中等)",
      "alpha": 0.05,
      "power": 0.80,
      "n_per_group": 34,
      "total": 68,
      "with_dropout_20pct": 85
    },
    "statistical_plan": [
      "描述性统计",
      "正态性检验 (Shapiro-Wilk)",
      "Independent t-test",
      "效应量 (Cohen's d)",
      "95% 置信区间"
    ],
    "protocol": [
      "被试招募", "知情同意", "随机分组",
      "实验操作", "数据采集", "数据分析"
    ],
    "threats_and_mitigations": [
      { "threat": "选择偏差", "mitigation": "随机分组 + 分层" }
    ]
  }
}
```

### Step 3: 输出

**完成判断标准：**
- [ ] 输出包含 design_type
- [ ] 输出包含 sample_size（含 n_per_group 和 total）
- [ ] 输出包含 ≥3 步 statistical_plan
- [ ] 输出包含 ≥4 步 protocol

```markdown
# 实验设计方案

## 研究假设
- H0 (零假设): ...
- H1 (备择假设): ...

## 实验设计
- 设计类型: [2x2 混合设计]
- 自变量: ...（水平: Level1, Level2）
- 因变量: ...
- 控制变量: ...

## 变量矩阵
| 条件 | IV1-Level1 | IV1-Level2 |
|------|-----------|-----------|
| IV2-Level1 | Cell(1,1) | Cell(1,2) |
| IV2-Level2 | Cell(2,1) | Cell(2,2) |

## 样本量
- 效应量: d = 0.5（中等）
- alpha = 0.05, power = 0.80
- 最小样本量: N = 68（每组 n = 34）
- 考虑脱落率 (20%): 建议招募 N = 85

## 统计分析计划
1. 描述性统计
2. 正态性检验 (Shapiro-Wilk)
3. 主分析: [具体检验方法]
4. 效应量报告
5. 多重比较校正（如适用）

## 实验流程 (Protocol)
1. 被试招募
2. 知情同意
3. 随机分组
4. 实验操作
5. 数据采集
6. 数据分析

## 潜在威胁与对策
| 威胁 | 对策 |
|------|------|
| 选择偏差 | 随机分组 + 分层 |
```

---

## 错误处理

```
Level 1 — 自动重试
  触发：analysis-agent 超时或返回空
  策略：重试 1 次

Level 2 — 降级
  触发：假设类型无法匹配关键词
  策略：使用默认设计（RCT + t-test），在输出中注明"已使用默认设计"

Level 3 — 人工介入
  触发：假设解析失败（无法识别 IV/DV）
  策略：请用户明确自变量和因变量后重新执行

Level 4 — 全局终止
  触发：超过 TIMEOUT_SECONDS / MAX_RETRIES 耗尽
  策略：写入 STATE_FILE status=FAILED，输出已有部分结果
```
