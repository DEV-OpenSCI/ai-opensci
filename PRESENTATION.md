# 科研AI工作流的实践

---
我个人理解ASCI这次科研调研目的不是怎么写论文，而是看看我们内部怎么使用AI,如何让AI提高生产力，在提高生产力中如何调优，让我们加深对AI的理解；
所以我的侧重点不是在写论文，而是做了一个科研AI工作流的实践

先说一个场景：写论文，一般是什么流程？

> 找文献 → 定假设 → 设计实验 → 跑数据 → 写论文 → 投稿被拒 → 改论文 → 再投

是不是很像软件工程里的：

> 需求调研 → 方案设计 → 开发 → 测试 → 上线 → Bug 反馈 → 修复 → 再上线

既然流程这么像，那程序员最擅长的事情——**把重复流程自动化、把工具链串起来**

---

## 第一部分：科研流水线全景图

传统科研和我们今天要讲的 AI 流水线的对比：

```
传统科研                          AI 流水线 (ai-opensci)
─────────                        ──────────────────────
Google Scholar 手动搜              → Scholar + Elicit + Consensus 三源并行搜索
读 50 篇论文找 gap                → AI 提炼 takeaway + 立场分析 + 自动保存 PDF
脑子里想假设                      → 基于 Research Gap 自动生成假设
Excel 算样本量                    → 自动生成实验设计 + 统计方案（并行）
SPSS/R 手动跑                     → 自动生成分析脚本 + 执行验证 + 可视化
痛苦地写 Introduction             → IMRaD 结构串行生成草稿（信息蒸馏传递）
投稿前心里打鼓                    → 3 个 AI Reviewer 并行审稿 + Meta-Review
```

关键信息：**不是替代科研者的思考，而是把每个环节中重复、机械的部分自动化**。

科研的核心竞争力是"提出好问题"和"设计好实验"——这两件事 AI 暂时替代不了。但其他环节，程序员 + AI 可以把效率提升一个数量级。

---

## 第二部分：技术架构——用程序员的语言讲

这个项目叫 `ai-opensci`，是一个 **Claude Code 插件**。

Claude Code 的插件生态有几个核心概念，我用科研场景一一对应：

### 2.1 MCP Server —— "外部 API 的标准化接口"

MCP（Model Context Protocol）就是让 AI 能调用外部工具的协议。你可以把它理解为——给 AI 装了几个"API 适配器"。

我们做了 **7 个 MCP Server**：

```
搜索层 (3 源并行)               存储层                  分析层
┌──────────────┐               ┌──────────────┐       ┌──────────────┐
│ scholar-server│               │ paper-store  │       │ pdf-reader   │
│ (Semantic     │               │ (下载 PDF +   │       │ (解析本地    │
│  Scholar API) │               │  元数据管理)  │       │  PDF 论文)   │
├──────────────┤               └──────────────┘       ├──────────────┤
│ elicit-server │                                      │ crossref     │
│ (Elicit API)  │                                      │ (DOI 解析)   │
├──────────────┤                                      └──────────────┘
│ consensus     │
│ (Consensus    │               补充搜索层
│  API)         │               ┌──────────────┐
└──────────────┘               │ arxiv-server  │
                                │ (arXiv 预印本)│
                                └──────────────┘
```

每个 server 就是一个 Python 脚本，用 FastMCP 框架写，大概 100-200 行代码。以 `scholar-server` 为例：

```python
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("scholar-server")

@mcp.tool()
async def search_papers(query: str, limit: int = 10):
    """Search academic papers by keyword."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query": query, "limit": limit, "fields": "title,year,citationCount,..."}
        )
    # ... format and return results

mcp.run()
```

就这么简单。`@mcp.tool()` 装饰器让这个函数变成了 AI 可以调用的工具。

**对程序员来说，MCP 的价值在于：你可以用最熟悉的方式写 API 调用，AI 自动知道什么时候该调用它。**

### 2.2 Agent —— "有专长的 AI 角色"

我们定义了 4 个专业 Agent：

| Agent | 职责 | 类比 |
|-------|------|------|
| `literature-agent` | 搜文献、做综述 | 研究助理 |
| `analysis-agent` | 数据分析、出图 | 统计顾问 |
| `writing-agent` | 论文写作、润色 | 写作教练 |
| `reviewer-agent` | 模拟审稿 | 匿名审稿人 |

每个 Agent 就是一个 Markdown 文件，定义了它的"人设"和工作流。比如 `reviewer-agent` 支持 3 种角色：方法论专家、领域专家、统计专家——模拟真实期刊的多 Reviewer 审稿机制。

### 2.3 Skill —— "一键触发的标准化指令"

Skill 是用户直接调用的入口，输入 `/ai-opensci:literature-review "你的研究问题"` 就能启动整个文献调研流程。

我们有 6 个 Skill：

```
/literature-review  → 三源并行搜索，筛选 5-8 篇核心论文
/experiment-design  → 生成完整实验方案
/data-analysis      → 自动化数据分析 + 可视化
/paper-write        → IMRaD 结构串行写作
/peer-review        → 3 角色并行模拟审稿
/research-pipeline  → 以上全部串起来，一键跑完
```

### 2.4 Hooks —— "自动化守护"

Hooks 是事件驱动的自动检查。我们设了两个：

- **保存 .py 文件后**：自动检查有没有设 `random_seed`（科研可复现性）
- **写入文件前**：自动检测有没有 `patient_id`、`email` 等敏感字段（数据安全）

这就像 Git 的 pre-commit hook，但是给 AI 加的。

---

## 第三部分：两种 Agent 编排模式

这是今天最重要的技术点——**Agent 编排**。

### 模式一：并行 Fan-out + 聚合

场景：文献调研 `/literature-review`

```
用户: "LLM 在药物发现中的应用"
         │
    ┌────┼────────┐
    ▼    ▼        ▼           ← 3 个 Agent 同时启动（结构化 JSON 输入）
 [Scholar] [Elicit] [Consensus]
 关键词搜索  问题搜索  问句搜索
    │    │        │
    └────┼────────┘
         ▼                    ← 确定性聚合（去重 → 评分 → 筛选）
    5-8 篇核心论文              ← 部分失败自动降级
         │
         ▼
    保存 PDF + 元数据到 Paper Store
         │
         ▼
    输出调研报告 + 立场分析 + Research Gap
```

为什么要并行？因为三个数据源各有优势：
- **Semantic Scholar**：引用数据最全，覆盖 2 亿+ 论文
- **Elicit**：支持自然语言查询，能过滤 Q1 期刊和研究类型
- **Consensus**：每篇论文给一个 AI 生成的 takeaway——这篇论文支持还是反对你的研究问题

三源交叉验证 + 部分失败降级：即使 1-2 个源不可用，仍能用剩余源完成。

### 模式二：串行流水线 + 信息蒸馏

场景：论文写作 `/paper-write`

```
大纲生成 → [用户确认] → Introduction → Methods → Results → Discussion → Abstract
   │                        │            │          │           │           │
   ▼                     3句摘要→     3句摘要→   3句摘要→    3句摘要→    各节摘要
writing-               writing-    writing-   analysis-   writing-    writing-
 agent                  agent       agent    + writing     agent       agent
```

关键设计：**信息蒸馏**——每节只传 3 句话摘要给下一节，不传全文。
- 避免上下文膨胀导致质量下降
- Methods 要和 Introduction 里提出的方法一致
- Abstract 要概括全文——所以放在最后写，传入各节摘要

**串行不意味着慢，意味着信息不丢失。**

### 模式三：多角色并行 + 确定性聚合（最有趣的）

场景：模拟审稿 `/peer-review`

```
你的论文
    │
    ├── Reviewer 1: 方法论专家   → 结构化 JSON 意见
    ├── Reviewer 2: 领域专家     → 结构化 JSON 意见     ← 同时
    └── Reviewer 3: 统计专家     → 结构化 JSON 意见
                │
                ▼
         Meta-Reviewer（确定性聚合逻辑，非 LLM 路由）
         → P0: 共识问题（≥2 人提到的 major）
         → P1: 单人 major
         → P2: minor
         → 综合 recommendation: 取最严格
         → Rebuttal 模板
```

关键：即使 1-2 个 Reviewer 超时，也能用成功的结果输出部分审稿意见。

这模拟的是真实期刊的审稿流程。投稿前先让 AI 帮你挑一遍刺，比被真人 Reviewer 拒稿强多了。

---

## 第四部分：Live Demo

### Demo 1: 文献调研 (展示并行 + MCP + 存储)

```bash
/ai-opensci:literature-review "How do large language models improve drug discovery pipeline efficiency?"
```

现场演示：
1. 看 3 个 Agent 并行启动搜索
2. 看搜索结果汇总和质量筛选
3. 看 PDF 自动下载到本地
4. 看最终的 5-8 篇核心论文报告

### Demo 2: 模拟审稿 (展示多角色并行)

```bash
/ai-opensci:peer-review ./draft/paper.pdf
```

现场演示：
1. PDF 自动解析
2. 3 个 Reviewer 同时审稿
3. 看不同角色的审稿风格差异
4. Meta-Review 汇总 + Rebuttal 模板

### Demo 3: 全流水线 (展示计时统计)

```bash
/ai-opensci:research-pipeline "Can LLMs reduce the time-to-market for new drugs?"
```

跑完后看用时统计（4 Phase 架构，零等待自动流转）：

```
============================================================
  PIPELINE TIMING REPORT
============================================================

  1. 1.文献调研           ████████████░░░░░░░░   2m 15s  (25%)
  2. 2a.假设提炼          ███░░░░░░░░░░░░░░░░░     28s   (5%)
  3. 2b.实验设计+分析方案  ██████████░░░░░░░░░░   1m 45s  (19%)
  4. 3.论文写作           █████████████████░░░░   3m 10s  (35%)
  5. 4.审稿自检           ████████░░░░░░░░░░░░░   1m 22s  (15%)

  TOTAL                                          9m 00s  (100%)
============================================================
```

**传统做这些事情需要几周。AI 流水线，10 分钟以内。**

当然，10 分钟产出的是"草稿级"的输出，不是终稿。但它把你从零到一的冷启动时间压缩了 90%。

---

## 第五部分：项目全景 (3 min)

快速回顾一下整个项目的数字：

```
ai-opensci/
├── 7 个 MCP Server (Python)
│   ├── scholar-server      Semantic Scholar 学术搜索
│   ├── elicit-server       Elicit AI 研究助手
│   ├── consensus-server    Consensus 立场分析
│   ├── arxiv-server        arXiv 预印本
│   ├── crossref-server     DOI/期刊信息
│   ├── pdf-reader-server   本地 PDF 解析
│   └── paper-store         文献下载与管理
│
├── 4 个 Agent (Markdown)
│   ├── literature-agent    文献调研专家
│   ├── analysis-agent      数据分析专家
│   ├── writing-agent       学术写作专家
│   └── reviewer-agent      审稿专家 (支持 3 种角色)
│
├── 6 个 Skill/Command
│   ├── literature-review   三源并行 + 本地存储
│   ├── experiment-design   实验方案生成
│   ├── data-analysis       自动分析 + 可视化
│   ├── paper-write         串行写作流水线
│   ├── peer-review         多角色并行审稿
│   └── research-pipeline   全流水线 + 计时统计
│
├── 2 个 Hook
│   ├── check_reproducibility   可复现性守护
│   └── check_data_safety       数据安全守护
│
└── 1 个计时器 (timer.py)
```

整个项目的代码量不大，Python MCP Server 每个 100-200 行，Agent/Skill 都是 Markdown 配置。**程序员的杠杆在于：你不需要写多少代码，你需要的是理解"怎么把工具串起来"。**

---

## 第六部分：边界与反思 (3 min)

### AI 能做什么

- 搜索和筛选文献（比人快 100 倍）
- 生成实验设计的框架（不是最终方案）
- 写作草稿和润色（不是代写）
- 预审稿（提前发现低级问题）

### AI 不能做什么

- **提出真正有创意的研究问题**——这是科研最核心的价值
- **替代实验本身**——湿实验还是要做的
- **保证正确性**——所有 AI 输出必须人工验证
- **替代科研伦理判断**

### 关于学术诚信

三条红线：
1. **AI 辅助 ≠ AI 代劳**：AI 生成的是草稿，研究者要对最终内容负责
2. **AI 输出必须验证**：尤其是文献引用和统计数据，AI 会产生幻觉
3. **方法要透明**：论文 Methods 里应该写明使用了 AI 辅助工具

---

## 结尾 (2 min)

回到开头的类比——科研像软件工程。

但有一点不同：软件工程追求"自动化一切"，科研不应该。科研的价值在于**人的洞察力**——看到别人没看到的 gap，设计出巧妙的实验来验证假设。

AI 流水线做的事情是：**把那些不需要洞察力的环节自动化，让研究者把 100% 的精力放在需要洞察力的环节上**。

搜 50 篇论文不需要洞察力，但从这 50 篇论文里发现一个没人注意到的 gap——需要。
写 Introduction 的第一稿不需要洞察力，但决定论文的核心 argument——需要。
检查统计方法是否正确不需要洞察力，但选择什么样的实验设计来回答你的问题——需要。

这就是我作为程序员能给科研带来的东西：**不是替代思考，而是释放思考的带宽**。

谢谢大家。

---

## 附：Q&A 预备

**Q: 这些 MCP Server 的 API 调用有费用吗？**
A: Semantic Scholar 和 arXiv 完全免费。Elicit 需要 Pro 计划（约 $10/月）。Consensus 需要申请 API access（$0.10/次调用）。paper-store 和 pdf-reader 是本地的，不花钱。

**Q: Agent 的输出质量够用吗？**
A: 取决于场景。文献搜索和筛选的准确率很高（因为是调真实 API，不是 AI 编造）。写作和审稿的质量是"靠谱的草稿"级别，不是终稿。

**Q: 这个插件公开吗？**
A: 是的，计划开源。安装后一行命令就能用：`/ai-opensci:research-pipeline "你的研究问题"`。

**Q: 不用 Claude Code，能用其他 AI 工具做到类似的效果吗？**
A: 单个环节可以（比如用 ChatGPT 润色论文）。但"把所有环节串成一条自动化流水线"是 Claude Code 插件生态的独特优势——MCP 让 AI 调外部 API，Agent 让 AI 有专业分工，Skill 让用户一键触发，Hooks 提供自动化守护。这套组合拳目前其他平台做不到。

**Q: 并行 Agent 搜索的延迟怎么样？**
A: 三源并行搜索一般在 10-30 秒内完成。比串行快 3 倍左右。从计时器的统计来看，文献调研是最耗时的环节（约 38%），但也就是不到一分钟的事。
