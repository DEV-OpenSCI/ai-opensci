---
name: data-analysis
description: 数据分析——给定数据文件路径，自动探索数据、选择统计方法、生成分析脚本和可视化。展示代码生成与执行能力。
argument-hint: <path to data file>
user-invocable: true
---

# Data Analysis — 自动化数据分析

你将对给定的数据文件进行完整的统计分析和可视化。

## 用户输入

数据文件路径: `$ARGUMENTS`

## 执行流程

### Step 1: 数据加载与探索

使用 `analysis-agent` 读取数据文件并生成 EDA 报告:

```python
import pandas as pd
import numpy as np

# 加载数据
df = pd.read_csv("$ARGUMENTS")  # 自动识别格式

# 基本信息
print(f"Shape: {df.shape}")
print(f"Columns: {df.columns.tolist()}")
print(f"Dtypes:\n{df.dtypes}")
print(f"Missing values:\n{df.isnull().sum()}")
print(f"Descriptive stats:\n{df.describe()}")
```

### Step 2: 自动统计分析

根据数据特征自动选择分析方法:
1. 识别变量类型（连续 / 分类）
2. 检验正态性
3. 选择参数/非参数方法
4. 执行假设检验
5. 计算效应量

### Step 3: 生成可视化

创建出版级图表:
- 分布图 (histogram + KDE)
- 箱线图 (带数据点)
- 相关性热力图
- 结果对比图 (bar/violin plot with error bars)

图表设置:
```python
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams.update({
    'font.size': 12,
    'figure.figsize': (8, 6),
    'figure.dpi': 300,
    'savefig.bbox': 'tight',
})
```

### Step 4: 输出

1. **分析报告** (Markdown): 数据概览 + 统计结果 + 结论
2. **完整脚本** (.py): 可独立运行的 Python 分析脚本
3. **图表文件** (.png): 高分辨率出版级图表

所有脚本必须:
- 设置 `np.random.seed(42)` 确保可复现
- 包含完整的 import
- 有充分注释
- 输出路径使用相对路径

## 演示要点

这个 skill 演示了:
- **Agent 调用**: 使用 analysis-agent 完成数据分析
- **代码生成 + 执行**: 自动生成并运行 Python 脚本
- **Hooks 联动**: 保存 .py 文件时触发可复现性检查 hook
