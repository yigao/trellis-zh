---
name: trellis-brainstorm
description: "Guides collaborative requirements discovery before implementation. Creates task directory, seeds PRD, asks high-value questions one at a time, researches technical choices, and converges on MVP scope. Use when requirements are unclear, there are multiple valid approaches, or the user describes a new feature or complex task."
---

# Brainstorm（头脑风暴） - 需求发现（AI 编码增强）

**核心规则**：就本计划的方方面面 relentlessly 向我提问，直到我们达成共识。沿着设计树的每一个分支走，逐个解决决策之间的依赖关系。对每个问题，给出你的推荐答案。

每次只问一个问题。

如果某个问题可以通过探索代码库来回答，则直接探索代码库。

---

引导 AI 在**实现之前**进行协作式需求发现，针对 AI 编码 workflow（工作流）进行了优化：

* **Task 优先**（立即捕捉想法）
* **行动先于提问**（减少低价值问题）
* **技术选型优先研究**（避免让用户凭空列举选项）
* **发散 → 收敛**（扩展思维，然后锁定 MVP）

---

## 何时使用

当用户描述开发 task 时，从 `/trellis:start` 触发，尤其在以下情况下：

* 需求不明确或持续变化
* 存在多个可行的实现路径
* 存在权衡取舍（UX、可靠性、可维护性、成本、性能）
* 用户可能一开始不知道最佳选项

---

## 核心原则（不可妥协）

1. **Task 优先（尽早捕捉）**
   始终确保在开始时已存在 task，以便用户的想法能立即被记录。

2. **行动先于提问**
   如果你能通过仓库代码、文档、配置、convention（惯例）或快速 research（研究）获得答案——先去做。

3. **每条消息只问一个问题**
   绝不要用一长串问题淹没用户。每次问一个，更新 PRD（产品需求文档），重复。

4. **优先提供具体选项**
   对于偏好/决策类问题，提供 2–3 个可行且具体的方法，并说明各自的权衡。

5. **技术选型优先 research**
   如果决策依赖行业 convention / 类似工具 / 成熟的 pattern，先做 research，然后提出选项。

6. **发散 → 收敛**
   初步理解需求后，主动考虑未来的演进方向、相关场景以及失败/边界情况——然后收敛到 MVP 并明确界定 out-of-scope。

7. **不问元问题**
   不要问"我应该搜索吗？"或"能不能把代码贴过来让我继续？"
   如果需要信息：搜索/检查。如果被阻塞：问最小阻塞问题。

---

## 步骤 0：确保 Task 存在（始终执行）

在任何问答之前，确保 task 存在。如果不存在，立即创建一个。

* 使用从用户消息中提炼的**临时工作标题**。
* 标题不完美也没关系——稍后在 PRD 中优化。

```bash
TASK_DIR=$(py -3 ./.trellis/scripts/task.py create "brainstorm: <short goal>" --slug <auto>)
```

使用不带日期前缀的 slug。`task.py create` 会自动添加 `MM-DD-` 目录前缀。

立即创建/填充 `prd.md`，写入你已知的内容：

```markdown
# brainstorm: <short goal>

## Goal

<one paragraph: what + why>

## What I already know

* <facts from user message>
* <facts discovered from repo/docs>

## Assumptions (temporary)

* <assumptions to validate>

## Open Questions

* <ONLY Blocking / Preference questions; keep list short>

## Requirements (evolving)

* <start with what is known>

## Acceptance Criteria (evolving)

* [ ] <testable criterion>

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* <what we will not do in this task>

## Technical Notes

* <files inspected, constraints, links, references>
* <research notes summary if applicable>
```

---

## 步骤 1：自动获取 context（上下文）（提问之前先做）

在问诸如"代码长什么样？"之类的问题之前，自己先收集 context：

### 仓库检查清单

* 识别可能受影响的模块/文件
* 定位已有的 pattern（类似功能、convention、错误处理风格）
* 检查配置、脚本、现有命令定义
* 注意任何约束（运行时、依赖策略、构建工具）

### 文档检查清单

* 查找已有的 PRD/spec/模板
* 查找命令使用示例、README、ADR（如果有的话）

将发现写入 PRD：

* 添加到 `What I already known`
* 将约束/链接添加到 `Technical Notes`

---

## 步骤 2：复杂度分级（仍然有用，不影响 task 创建）

| 复杂度       | 标准                                                   | 操作                                        |
| ------------ | ------------------------------------------------------ | ------------------------------------------- |
| **Trivial**  | 单行修复、拼写错误、显而易见改动                       | 跳过 brainstorm，直接 implement（实现）     |
| **Simple**   | 目标明确、1–2 个文件、范围清晰                         | 问 1 个确认性问题，然后 implement           |
| **Moderate** | 多个文件、一定的不确定性                               | 轻量 brainstorm（2–3 个高价值问题）         |
| **Complex**  | 目标模糊、涉及架构选择、多种实现路径                   | 完整 brainstorm                             |

> 注意：Task 已在步骤 0 中创建。复杂度分级只影响 brainstorm 的深度。

---

## 步骤 3：问题门控（只问高价值问题）

在问任何问题之前，先过以下门控：

### 门控 A —— 我能否在不打扰用户的情况下自行获得答案？

如果答案可以通过以下方式获取：

* 仓库检查（代码/配置）
* 文档/spec/convention
* 快速市场/开源 research

→ **不要问。** 去获取、总结、更新 PRD。

### 门控 B —— 这是元/懒惰问题吗？

示例：

* "我应该搜索吗？"
* "能不能把代码贴过来让我继续？"
* "代码长什么样？"（在仓库可访问的情况下）

→ **不要问。** 直接行动。

### 门控 C —— 这是什么类型的问题？

* **阻塞型（Blocking）**：没有用户输入无法继续
* **偏好型（Preference）**：多个有效选择，取决于产品/UX/风险偏好
* **可自行推导型（Derivable）**：应该通过检查/research 来回答

→ 只问**阻塞型**或**偏好型**。

---

## 步骤 4：Research 优先模式（技术选型时强制执行）

### 触发条件（满足任一 → research 优先）

* Task 涉及选择方案、库、协议、框架、模板系统、插件机制或 CLI UX convention
* 用户询问"最佳实践"、"别人怎么做的"、"推荐"
* 用户无法合理列举选项

### 委派给 `trellis-research` 子 agent（不在主线程中做 research）

对于每个 research 主题，**通过 Task 工具派发一个 `trellis-research` 子 agent（智能体）**——不要在主对话中内联执行 WebFetch / WebSearch / `gh api`。

原因：
- 子 agent 拥有自己的 context 窗口 → 不会用原始工具输出污染 brainstorm context
- 它会将发现持久化到 `{TASK_DIR}/research/<topic>.md`（这是合约——参见 `workflow.md` 阶段 1.2）
- 它只向主 agent 返回 `{文件路径, 一句话摘要}`
- 独立主题可以**并行**处理——一次工具调用中派发多个子 agent

> **Codex 例外**：在 Codex CLI 上，不要为 research 优先模式派发 `trellis-research`——在主 session（会话）中内联做 research（WebFetch / WebSearch），并自行将发现写入 `{TASK_DIR}/research/<topic>.md`。原因：Codex 的 `spawn_agent` 使用 `fork_turns="none"`（隔离 context，不继承父 session）运行子 agent，因此 research 子 agent 无法通过 `task.py current` 解析活动 task 路径，会静默中止而不产出文件。Codex 上的内联 research 可以避免此故障模式。`workflow.md` 中的 3+ 内联 research 调用限制（B 规则）对 Codex 特例放宽。

Agent 类型：`trellis-research`
Task 描述模板：`"Research <specific question>; persist findings to \`{TASK_DIR}/research/<topic-slug>.md\`."`

❌ 坏的做法（禁止这样做）：
```
Main agent: WebFetch(url-A) → WebFetch(url-B) → Bash(gh api ...)
          → WebSearch(q1) → WebSearch(q2) → ... (10+ inline calls)
          → Write(research/topic.md)
```
→ 用原始 HTML/JSON 污染主 context，消耗 token。

✅ 好的做法：
```
Main agent: Task(subagent_type="trellis-research",
                 prompt="Research topic A; persist to research/topic-a.md")
          + Task(subagent_type="trellis-research",
                 prompt="Research topic B; persist to research/topic-b.md")
          + Task(subagent_type="trellis-research",
                 prompt="Research topic C; persist to research/topic-c.md")
→ Reads research/topic-{a,b,c}.md after they finish.
```

### Research 步骤（传入每个子 agent 的 prompt）

每个 `trellis-research` 子 agent 应该：

1. 识别其主题的 2–4 个可比较的工具/pattern
2. 总结常见的 convention 及其存在原因
3. 将 convention 映射到我们仓库的约束条件
4. 将发现写入 `{TASK_DIR}/research/<topic>.md`

然后主 agent 读取持久化文件并在 PRD 中产出 **2–3 个可行方案**。

### Research 输出格式（PRD）

PRD 本身应只引用持久化的 research 文件，而非复制其内容。添加 `## Research References` 章节，指向 `research/*.md`。

可选地，添加收敛章节，列出从 research 中得出的可行方案：

```markdown
## Research References

* [`research/<topic-a>.md`](research/<topic-a>.md) — <one-line takeaway>
* [`research/<topic-b>.md`](research/<topic-b>.md) — <one-line takeaway>

## Research Notes

### What similar tools do

* ...
* ...

### Constraints from our repo/project

* ...

### Feasible approaches here

**Approach A: <name>** (Recommended)

* How it works:
* Pros:
* Cons:

**Approach B: <name>**

* How it works:
* Pros:
* Cons:

**Approach C: <name>** (optional)

* ...
```

然后问**一个**偏好问题：

* "Which approach do you prefer: A / B / C (or other)?"

---

## 步骤 5：扩展扫描（发散）—— 初步理解后必须执行

在你能总结目标之后，主动拓宽思路，然后再收敛。

### 扩展类别（每类保持 1–2 点）

1. **未来演进**

   * 这个功能在 1–3 个月内可能变成什么？
   * 现在有哪些扩展点值得保留？

2. **相关场景**

   * 有哪些相邻的命令/流程应与此保持一致？
   * 是否存在功能对等期望（create 与 update、import 与 export 等）？

3. **失败和边界情况**

   * 冲突、离线/网络故障、重试、幂等性、兼容性、回滚
   * 输入验证、安全边界、权限检查

### 扩展消息模板（发给用户）

```markdown
I understand you want to implement: <current goal>.

Before diving into design, let me quickly diverge to consider three categories (to avoid rework later):

1. Future evolution: <1–2 bullets>
2. Related scenarios: <1–2 bullets>
3. Failure/edge cases: <1–2 bullets>

For this MVP, which would you like to include (or none)?

1. Current requirement only (minimal viable)
2. Add <X> (reserve for future extension)
3. Add <Y> (improve robustness/consistency)
4. Other: describe your preference
```

然后更新 PRD：

* MVP 包含的 → `Requirements`
* 排除的 → `Out of Scope`

---

## 步骤 6：问答循环（收敛）

### 规则

* 每条消息只问一个问题
* 尽量使用多选格式
* 每次用户回答之后：

  * 立即更新 PRD
  * 将已回答的条目从 `Open Questions` 移至 `Requirements`
  * 用可测试的复选框更新 `Acceptance Criteria`
  * 明确 `Out of Scope`

### 问题优先级（推荐）

1. **MVP 范围边界**（包含/排除什么）
2. **偏好决策**（在提供具体选项之后）
3. **失败/边界行为**（仅针对 MVP 关键路径）
4. **成功指标和验收标准**（什么能证明它有效工作）

### 首选问题格式（多选）

```markdown
For <topic>, which approach do you prefer?

1. **Option A** — <what it means + trade-off>
2. **Option B** — <what it means + trade-off>
3. **Option C** — <what it means + trade-off>
4. **Other** — describe your preference
```

---

## 步骤 7：提出方案 + 记录决策（复杂 task）

在需求足够清晰之后，提出 2–3 个方案（如果尚未通过 research 优先模式完成）：

```markdown
Based on current information, here are 2–3 feasible approaches:

**Approach A: <name>** (Recommended)

* How:
* Pros:
* Cons:

**Approach B: <name>**

* How:
* Pros:
* Cons:

Which direction do you prefer?
```

将结果作为 ADR-lite 章节记录到 PRD 中：

```markdown
## Decision (ADR-lite)

**Context**: Why this decision was needed
**Decision**: Which approach was chosen
**Consequences**: Trade-offs, risks, potential future improvements
```

---

## 步骤 8：最终确认 + 实现计划

当开放问题解决后，用结构化的总结确认完整需求：

### 最终确认格式

```markdown
Here's my understanding of the complete requirements:

**Goal**: <one sentence>

**Requirements**:

* ...
* ...

**Acceptance Criteria**:

* [ ] ...
* [ ] ...

**Definition of Done**:

* ...

**Out of Scope**:

* ...

**Technical Approach**:
<brief summary + key decisions>

**Implementation Plan (small PRs)**:

* PR1: <scaffolding + tests + minimal plumbing>
* PR2: <core behavior>
* PR3: <edge cases + docs + cleanup>

Does this look correct? If yes, I'll proceed with implementation.
```

### 子 Task 拆分（复杂 task）

对于包含多个独立工作项的复杂 task，创建子 task：

```bash
# Create child tasks
CHILD1=$(py -3 ./.trellis/scripts/task.py create "Child task 1" --slug child1 --parent "$TASK_DIR")
CHILD2=$(py -3 ./.trellis/scripts/task.py create "Child task 2" --slug child2 --parent "$TASK_DIR")

# Or link existing tasks
py -3 ./.trellis/scripts/task.py add-subtask "$TASK_DIR" "$CHILD_DIR"
```

---

## PRD 目标结构（最终）

`prd.md` 应收敛为：

```markdown
# <Task Title>

## Goal

<why + what>

## Requirements

* ...

## Acceptance Criteria

* [ ] ...

## Definition of Done

* ...

## Technical Approach

<key design + decisions>

## Decision (ADR-lite)

Context / Decision / Consequences

## Out of Scope

* ...

## Technical Notes

<constraints, references, files, research notes>
```

---

## 反模式（严格禁止）

* 向用户询问可以从仓库中自行获得的代码/context
* 在提供具体选项之前让用户选择方案
* 关于是否要做 research 的元问题
* 只盯着最初需求而不考虑演进/边界
* 让 brainstorm 随意漂移而不更新 PRD

---

## 与启动 Workflow 的集成

brainstorm 完成后（步骤 8 确认获批），流程继续到 Task Workflow 的**阶段 2：准备实现**：

```text
Brainstorm
  Step 0: Create task directory + seed PRD
  Step 1–7: Discover requirements, research, converge
  Step 8: Final confirmation → user approves
  ↓
Task Workflow Phase 2 (Prepare for Implementation)
  Code-Spec Depth Check (if applicable)
  → Research codebase (based on confirmed PRD)
  → Configure code-spec context (jsonl files)
  → Activate task
  ↓
Task Workflow Phase 3 (Execute)
  Implement → Check → Complete
```

Task 目录和 PRD 在 brainstorm 中已存在，因此 Task Workflow 的阶段 1 完全跳过。

---

## 相关命令

| 命令 | 何时使用 |
|---------|-------------|
| `/trellis:start` | 触发 brainstorm 的入口点 |
| `/trellis:finish-work` | 实现完成后 |
| `/trellis:update-spec` | 工作过程中出现新 pattern 时 |
