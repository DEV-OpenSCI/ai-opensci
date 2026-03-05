---
name: paper-write
description: 论文写作——输入研究成果或大纲，按 IMRaD 结构串行生成论文草稿。展示串行 Agent 编排模式。
argument-hint: <research topic or outline>
user-invocable: true
---

# Paper Write — 串行 Agent 论文写作流水线

你将按照 IMRaD 结构，通过串行 Agent 编排生成论文草稿。

## 用户输入

研究主题/大纲: `$ARGUMENTS`

## 执行流程 (Serial Pipeline Pattern)

这个 skill 展示 **串行流水线** 模式：每个 agent 的输出作为下一个 agent 的输入。

### Stage 1: 大纲生成 → writing-agent

首先生成论文整体大纲:
- 确定论文标题
- 列出各节的要点
- 确定图表计划
- 确认用户同意后继续

### Stage 2: Introduction → writing-agent

基于大纲撰写引言:
- 研究背景（广→窄）
- 现有方法和局限
- 研究动机和贡献
- 论文组织结构

### Stage 3: Methods → writing-agent

基于引言中提出的方法撰写方法部分:
- 问题形式化
- 方法描述
- 算法/实验细节
- 实现细节

### Stage 4: Results → writing-agent + analysis-agent

如有数据:
1. 调用 `analysis-agent` 生成统计结果
2. 调用 `writing-agent` 将结果写成论文 Results 节
3. 包含图表描述和统计报告

### Stage 5: Discussion → writing-agent

基于前面所有内容:
- 结果解读
- 与已有工作对比
- 局限性分析
- 未来工作方向

### Stage 6: Abstract → writing-agent

最后写摘要（因为需要全文信息）:
- 150-250 词
- 覆盖背景、方法、关键结果、结论

## 输出

完整的论文草稿 (Markdown 格式)，注意论文内容要强制用"中文"写，如果md中用到图片要确保图片的路径正确保证图片正常显示:

```markdown
# [Title]

## Abstract
...

## 1. Introduction
...

## 2. Methods
...

## 3. Results
...

## 4. Discussion
...

## References
[TODO: 添加完整参考文献]
```

标记所有需要用户确认的内容为 `[TODO]` 或 `[VERIFY]`。

## 演示要点

这个 skill 演示了:
- **串行 Agent 编排**: A → B → C 流水线，前一步输出是后一步输入
- **多 Agent 协作**: writing-agent 和 analysis-agent 在 Results 阶段协作
- **人机交互**: 大纲阶段等待用户确认后再继续
