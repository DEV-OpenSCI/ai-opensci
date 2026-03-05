---
name: peer-review
description: 模拟同行评审——多角色并行审稿，汇总为综合评审意见。展示并行 Agent 编排（多角色模式）。
argument-hint: <path to paper file or paste content>
user-invocable: true
---

# Peer Review — 并行多角色模拟审稿

你将模拟学术期刊的同行评审流程，由 3 个不同角色的 reviewer 并行审稿。

## 用户输入

论文文件路径或内容: `$ARGUMENTS`

## 执行流程 (Parallel Multi-Role Pattern)

### Step 1: 获取论文内容

- 如果是文件路径: 使用 `pdf-reader-server` MCP 的 `read_pdf` 和 `extract_paper_structure` 读取
- 如果是文本内容: 直接使用

### Step 2: 并行审稿 (3 个 Agent 同时启动)

使用 Agent 工具启动 3 个并行的 `reviewer-agent`，每个扮演不同角色:

**Reviewer 1 — 方法论专家 (Methodologist)**
```
角色: methodologist
重点: 实验设计合理性、统计方法选择、可复现性
严格程度: 高
```

**Reviewer 2 — 领域专家 (Domain Expert)**
```
角色: domain_expert
重点: 新颖性、与领域前沿关系、实际应用价值
严格程度: 中
```

**Reviewer 3 — 统计专家 (Statistician)**
```
角色: statistician
重点: 数据分析正确性、效应量、p值解读、统计功效
严格程度: 高
```

### Step 3: Meta-Review 汇总

等待 3 个 reviewer 返回后，作为 Meta-Reviewer 汇总:

1. **共识问题**: 多个 reviewer 都指出的问题（高优先级）
2. **分歧点**: 不同 reviewer 意见冲突的地方
3. **综合建议**: Accept / Minor Revision / Major Revision / Reject

### Step 4: 输出

```markdown
# Peer Review Summary

## Meta-Review Decision
**Recommendation**: [Major Revision]
**Confidence**: [4/5]

## Consensus Issues (所有 Reviewer 一致同意)
1. [问题]: [具体描述]

## Individual Reviews

### Reviewer 1 (Methodologist)
[完整审稿意见]

### Reviewer 2 (Domain Expert)
[完整审稿意见]

### Reviewer 3 (Statistician)
[完整审稿意见]

## Action Items (按优先级)
- [ ] **P0**: [必须修改]
- [ ] **P1**: [强烈建议修改]
- [ ] **P2**: [建议改进]

## Rebuttal Template
[为每个主要问题提供 rebuttal 的建议框架]
```

## 演示要点

这个 skill 演示了:
- **并行 Agent 编排 (Multi-Role)**: 3 个 agent 同时运行，扮演不同角色
- **结果汇总与冲突解决**: Meta-Reviewer 合并并行结果
- **MCP 集成**: 使用 pdf-reader-server 读取论文
- **实用价值**: 投稿前的自检，提前发现潜在问题
