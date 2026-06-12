# trellis-implement 智能体详细分析文档

> 分析对象：`.claude/agents/trellis-implement.md`（Claude Code 定义）、`.codex/agents/trellis-implement.toml`（Codex 平台）
> 关联文档：`trellis-check-analysis.md`（Check 智能体）、`inject-subagent-context-analysis.md`（上下文注入钩子）

---

## 一、概述

`trellis-implement` 是 Trellis 项目管理系统中的 **代码实现智能体（Implement Agent）**。它在 Trellis 工作流的 **阶段 2.1（执行）** 被主会话分派，负责：

- **理解规范与需求**：阅读 `.trellis/spec/` 中的开发规范和任务的 `prd.md` + `info.md`
- **实现功能**：按照规范和技术设计编写代码
- **自行验证**：运行 lint 和 type-check 确保质量
- **报告结果**：输出结构化的 Implementation Complete 报告

`trellis-implement` 是"实现→检查"双智能体循环的**前半部分**。它产出代码，随后由 `trellis-check` 审查和修复。

---

## 二、文件架构

```
.claude/
├── agents/
│   └── trellis-implement.md     ← Claude Code 子智能体定义（Agent 工具调用）
└── hooks/
    └── inject-subagent-context.py ← 上下文注入钩子（PreToolUse）

.codex/
└── agents/
    └── trellis-implement.toml   ← Codex 平台子智能体定义
```

### 2.1 与 trellis-check 的文件架构差异

| 维度 | trellis-implement | trellis-check |
|------|-------------------|---------------|
| **Agent 定义** | `.claude/agents/trellis-implement.md` | `.claude/agents/trellis-check.md` |
| **Skill 定义** | ❌ 无（不存在内联 Skill） | ✅ `.claude/skills/trellis-check/SKILL.md` |
| **Codex 定义** | `.codex/agents/trellis-implement.toml` | `.codex/agents/trellis-check.toml` |
| **触发方式** | 仅通过 Agent 工具分派 | Agent 工具分派 + `/trellis-check` 命令 |
| **上下文 JSONL** | `implement.jsonl` | `check.jsonl` |
| **额外文件** | `prd.md` + `info.md` | `prd.md`（不需要 info.md） |

> **关键差异**：`trellis-implement` **没有内联 Skill 版本**。实现工作始终通过子智能体分派执行——这保证了实现的上下文隔离，避免主会话的对话历史污染实现过程。

---

## 三、Agent 定义逐段分析

### 3.1 YAML Frontmatter（元数据）

```yaml
---
name: trellis-implement
description: |
  Code implementation expert. Understands specs and requirements, then implements features. No git commit allowed.
tools: Read, Write, Edit, Bash, Glob, Grep, mcp__exa__web_search_exa, mcp__exa__get_code_context_exa
---
```

| 字段 | 值 | 说明 |
|------|---|------|
| `name` | `trellis-implement` | 智能体类型标识，钩子用它匹配 `AGENT_IMPLEMENT` 常量 |
| `description` | Code implementation expert... | 明确声明"不提交 git" |
| `tools` | 8 个工具 | 与 trellis-check **完全相同**的工具集 |

**工具选择分析**：
- `Read` — 读取规范文件、PRD、技术设计文档、现有代码
- `Write` / `Edit` — 创建新文件和修改现有代码
- `Bash` — 运行 lint、type-check、`grep -r` 搜索
- `Glob` / `Grep` — 搜索文件和代码模式
- `mcp__exa__*` — 外部技术文档搜索（API 参考、库文档等）

**与 trellis-check 的工具集完全相同**——区分两者的是提示词（系统提示）而非工具能力。两者都能读写代码，但 implement 的提示词引导它"创建和修改"，check 的提示词引导它"审查和修复"。

### 3.2 递归防护（Recursion Guard）

```
你已经是主会话分派出来的 trellis-implement 子智能体。请直接执行实现工作。

- 不要派生另一个 trellis-implement 或 trellis-check 子智能体。
- 如果 SessionStart 上下文……说要分派 trellis-implement / trellis-check，
  请将其视为已由你当前角色满足的主会话指令。
- 只有主会话才能分派 Trellis 的 implement/check 智能体。
  如果需要更多并行工作，请报告建议而不是派生子智能体。
```

**与 trellis-check 递归防护的唯一差异**：最后一句话。
- `trellis-check`：*"如果需要更多实现工作，请报告建议"*
- `trellis-implement`：*"如果需要更多并行工作，请报告建议"*

这反映了两个智能体的不同职责边界：check 不能做大型实现，implement 不能做并行分派。

**三层防护**（与 trellis-check 相同）：
1. **提示词防护**：Agent 定义中的递归防护说明
2. **工具集防护**：Agent 定义中不含 `Agent` 工具
3. **平台级防护**（Codex）：`multi_agent = false`

### 3.3 Trellis 上下文加载协议

```
请在你的输入内容中查找 <!-- trellis-hook-injected --> 标记。

- 如果标记存在：prd / spec / research 文件已在你的输入内容中自动加载。
  直接进行实现工作。
- 如果标记不存在：钩子注入未触发。请从分派提示的第一行
  Active task: <path> 找到活动任务路径，然后自行读取
  <task-path>/prd.md、<task-path>/info.md（如果存在）
  和 <task-path>/implement.jsonl 中列出的规范文件，再进行工作。
```

**关键差异 vs trellis-check 的加载协议**：

| 加载项 | implement | check |
|--------|-----------|-------|
| JSONL 索引 | `implement.jsonl` | `check.jsonl` |
| PRD | ✅ `prd.md` | ✅ `prd.md` |
| 技术设计 | ✅ `info.md`（如果存在） | ❌ 不需要 |

`info.md` 是 implement 独有的上下文来源——它包含架构决策、技术约束、实现方案等仅与编码相关的信息。check 不需要它，因为检查是验证"做对了没有"而非"怎么做"。

### 3.4 核心职责（五步）

```
1. 理解规范 - 阅读 .trellis/spec/ 中的相关规范文件
2. 理解需求 - 阅读 prd.md 和 info.md
3. 实现功能 - 按照规范和设计编写代码
4. 自行检查 - 确保代码质量
5. 报告结果 - 报告完成状态
```

**与 trellis-check 的四步对比**：

| 步骤 | implement | check |
|------|-----------|-------|
| 1 | 理解规范 | 获取代码变更 |
| 2 | 理解需求 | 对照规范检查 |
| 3 | 实现功能 | 自行修复 |
| 4 | 自行检查 | 运行验证 |
| 5 | 报告结果 | — |

implement 多了"理解需求"步骤（因为需要 prd + info），check 多了"运行验证"步骤（因为需要 lint + type-check + tests）。

### 3.5 禁止操作

```
不要执行以下 git 命令：
- git commit
- git push
- git merge
```

**这是 implement 独有的约束**。原因：
- 提交权保留给主会话——主会话在 trellis-check 通过后才执行提交
- 防止子智能体在质量验证前提交代码
- 保持 git 历史的清晰归属（提交者始终是开发者）

**trellis-check 没有此约束**——check 可以执行 git 命令（如 `git diff`），但通常也不需要 commit。

### 3.6 五步工作流

```
1. 理解规范
   └─ 根据任务类型阅读相关规范
      ├─ 规范层级：.trellis/spec/<package>/<layer>/
      └─ 共享指南：.trellis/spec/guides/

2. 理解需求
   └─ 阅读任务的 prd.md 和 info.md
      ├─ 核心需求是什么
      ├─ 技术设计的关键要点
      └─ 需要修改/创建哪些文件

3. 实现功能
   ├─ 按照规范和技术设计编写代码
   ├─ 遵循现有代码模式
   └─ 只做必要的工作，不过度工程化

4. 验证
   └─ 运行项目的 lint 和 type-check 命令来验证变更

5. 报告结果
   └─ 输出 Implementation Complete 报告
```

### 3.7 代码规范

```
- 遵循现有代码模式
- 不要添加不必要的抽象
- 只做必要的工作，不过度工程化
- 保持代码可读性
```

**这四条原则是对"AI 过度工程化"的防御**：
- "遵循现有代码模式" → 不要引入项目不熟悉的新范式
- "不要添加不必要的抽象" → 不要为了"未来可能需要"而写
- "只做必要的工作" → scope creep 防护
- "保持代码可读性" → 代码是写给人看的

### 3.8 报告格式

```markdown
## Implementation Complete（实现完成）

### Files Modified（已修改文件）
- `src/components/Feature.tsx` - 新组件
- `src/hooks/useFeature.ts` - 新钩子

### Implementation Summary（实现总结）
1. 创建了 Feature 组件...
2. 添加了 useFeature 钩子...

### Verification Results（验证结果）
- Lint: Passed
- TypeCheck: Passed
```

---

## 四、Codex 平台定义分析

`.codex/agents/trellis-implement.toml` 与 Claude Code 版本的关键差异：

### 4.1 配置对比

```toml
name = "trellis-implement"
description = "Workspace-write Trellis implementer that follows specs and keeps generated templates in sync."
sandbox_mode = "workspace-write"

[features]
multi_agent = false
[features.multi_agent_v2]
enabled = false
```

| 特性 | Claude Code | Codex |
|------|------------|-------|
| **描述侧重** | "understands specs and requirements" | "keeps generated templates in sync"（平台特有） |
| **沙箱** | 无 | `workspace-write` |
| **上下文加载** | 钩子自动注入 | 手动 3 步加载协议 |
| **多智能体** | 无 Agent 工具 | `multi_agent = false` 显式禁用 |

### 4.2 Codex 独有的约束

Codex 版本增加了 Claude Code 版本中未提及的规则：

```
Rules:
- Read before write. Follow .trellis/spec/ guidance relevant to the task.
- Keep changes focused on the requested scope.
- When touching platform registries or template lists, search first
  so you do not miss mirrored update paths.
- If you modify .trellis/scripts/, keep packages/cli/src/templates/trellis/scripts/ in sync.
- Do not make destructive git changes unless explicitly asked.
```

| 规则 | 含义 |
|------|------|
| **Read before write** | 修改前必须先读取文件 |
| **Keep changes focused** | scope creep 防护 |
| **Search mirrored paths** | 修改平台注册表或模板列表时，搜索所有镜像更新路径 |
| **Scripts 同步** | `.trellis/scripts/` 修改必须同步到 `packages/cli/src/templates/trellis/scripts/` |
| **不破坏性 git** | 比 Claude Code 的"禁止 commit"更宽泛——也包括 `git reset --hard` 等 |

### 4.3 Codex 的上下文加载协议

与 Claude Code 的钩子自动注入不同，Codex 子智能体必须手动加载：

```
Step 1: 找到活动任务路径（3 种方法按优先级）
  ├─ 1. 分派提示第一行 "Active task: <path>"
  ├─ 2. 运行 task.py current --source
  └─ 3. 询问用户

Step 2: 加载任务上下文
  ├─ 1. 读取 prd.md（需求）和 info.md（技术设计）
  ├─ 2. 读取 implement.jsonl（开发规范索引）
  └─ 3. 逐条读取 JSONL 中引用的每个 spec 文件

降级策略:
  ├─ implement.jsonl 无已整理条目 → 回退：prd-only + 自己匹配 spec
  └─ prd.md 不存在 → 询问用户
```

---

## 五、上下文注入系统集成

`trellis-implement` 的上下文由 `.claude/hooks/inject-subagent-context.py` 的 `get_implement_context()` 函数构建。

### 5.1 注入流程

```
主会话调用 Agent(subagent_type="trellis-implement", prompt="...")
  │
  ▼
PreToolUse 钩子触发
  │
  ├─ 检测子智能体类型 == "trellis-implement"
  ├─ 解析活动任务路径
  ├─ 读取 <task>/implement.jsonl
  ├─ 读取 <task>/prd.md
  ├─ 读取 <task>/info.md（如果存在）
  ├─ 构建注入提示词（build_implement_prompt）
  └─ 更新 tool_input.prompt
  │
  ▼
子智能体启动，收到已注入完整上下文的 prompt
```

### 5.2 Implement 专用上下文

| 上下文来源 | 文件 | 说明 |
|-----------|------|------|
| **开发规范** | `implement.jsonl` 中引用的所有文件 | 编码约定、API 设计规范、目录结构等 |
| **需求文档** | `prd.md` | 功能需求、验收标准 |
| **技术设计** | `info.md`（可选） | 架构决策、技术约束、实现方案 |

### 5.3 注入的提示词结构（`build_implement_prompt`）

```
<!-- trellis-hook-injected -->
角色定义：Implement 智能体
上下文区块：
  ├─ implement.jsonl 引用的所有 spec 文件内容
  ├─ prd.md 内容
  └─ info.md 内容（如果存在）
任务区块：原始 prompt
工作流指引：理解规范 → 理解需求 → 实现功能 → 自检
约束：
  ├─ 不执行 git commit
  ├─ 遵循规范
  └─ 报告文件列表
```

---

## 六、与 trellis-check 的完整对比

| 维度 | trellis-implement | trellis-check |
|------|-------------------|---------------|
| **阶段** | 阶段 2.1（执行） | 阶段 2.2（验证） |
| **角色** | 代码实现者 | 代码审查者 + 自修复者 |
| **Skill 版本** | ❌ 无 | ✅ `/trellis-check` |
| **上下文 JSONL** | `implement.jsonl` | `check.jsonl` |
| **额外文件** | `prd.md` + `info.md` | `prd.md` |
| **技术设计** | ✅ 需要 `info.md` | ❌ 不需要 |
| **git 约束** | **禁止** commit/push/merge | 无明确限制 |
| **工作流步骤** | 5 步（理解规范→理解需求→实现→自检→报告） | 4 步（获取变更→检查→修复→验证） |
| **工具集** | 相同 8 个 | 相同 8 个 |
| **报告标题** | Implementation Complete | Self-Check Complete |
| **核心原则** | 不过度工程化 | 自己动手修复 |
| **上下文大小** | ~8-10KB（implement.jsonl + prd + info） | ~5KB（check.jsonl + prd） |
| **递归防护** | 相同措辞 | 相同措辞 |

---

## 七、双智能体循环

`trellis-implement` 和 `trellis-check` 形成一个闭合的质量循环：

```
┌─────────────────────────────────────────────┐
│               主会话                          │
│                                             │
│  阶段 2.1: 派发 trellis-implement            │
│     │                                       │
│     ▼                                       │
│  ┌──────────────────────┐                   │
│  │ trellis-implement    │                   │
│  │ ├─ 理解规范 & 需求    │                   │
│  │ ├─ 实现功能          │                   │
│  │ ├─ 自行检查          │                   │
│  │ └─ 报告结果          │                   │
│  └──────────┬───────────┘                   │
│             │ 报告返回                       │
│             ▼                               │
│  阶段 2.2: 派发 trellis-check               │
│     │                                       │
│     ▼                                       │
│  ┌──────────────────────┐                   │
│  │ trellis-check        │                   │
│  │ ├─ 获取代码变更       │                  │
│  │ ├─ 对照规范检查       │                  │
│  │ ├─ 自行修复问题       │                  │
│  │ └─ 运行验证          │                   │
│  └──────────┬───────────┘                   │
│             │ 报告返回                       │
│             ▼                               │
│  ┌──────────────────────┐                   │
│  │ 问题分类：            │                   │
│  │ ├─ 全部修复 → 阶段 2.3│                   │
│  │ ├─ 有未修复 → 评估    │                   │
│  │ └─ 需重新实现 → 回到  │                   │
│  │    阶段 2.1           │                   │
│  └──────────────────────┘                   │
└─────────────────────────────────────────────┘
```

### 循环终止条件

| 条件 | 动作 |
|------|------|
| check 报告"全部通过" | 进入阶段 2.3（update-spec） |
| check 发现并全部自行修复 | 进入阶段 2.3 |
| check 发现需要产品决策的问题 | 主会话向用户报告 |
| check 发现需要大规模重构 | 主会话决定是否重新派发 implement |

---

## 八、设计亮点

### 8.1 无 Skill 版本的设计意图

`trellis-implement` 没有内联 Skill 版本，实现工作**始终**通过子智能体执行。原因：

1. **上下文隔离**：实现需要加载大量 spec 文件（implement.jsonl + prd + info），这些不应该污染主会话上下文
2. **专注度**：子智能体拥有干净的上下文窗口，不会被主会话的对话历史分心
3. **可预测性**：子智能体的上下文固定且已知，主会话只收到结果摘要

### 8.2 "不过度工程化"原则

Agent 定义中反复强调：
- "只做必要的工作，不过度工程化"
- "不要添加不必要的抽象"
- "遵循现有代码模式"

这是对 AI 编码助手常见"过度设计"倾向的针对性约束。

### 8.3 禁止 git commit 的架构意义

```
实现权（子智能体）≠ 提交权（主会话）
```

- 子智能体可以自由修改代码
- 但只有主会话（经过 check 验证后）才能提交
- 这保证了每次提交都经过了完整的"实现→检查"循环

### 8.4 降级路径的多层保障

```
Class-1 平台（Claude Code）:
  钩子注入 → 完全自动 → 子智能体直接工作

Class-1 平台（钩子失败：Windows / --continue / fork / hooks 禁用）:
  Active task: 行 → 手动加载 implement.jsonl → 工作

Class-2 平台（Codex / Copilot / Gemini / Qoder）:
  Active task: 行 → 手动加载（标准路径）
  task.py current → 后备
  询问用户 → 最终后备
```

---

## 九、边界情况与已知限制

| 场景 | 行为 |
|------|------|
| **info.md 不存在** | 正常——只加载 prd.md + implement.jsonl（info.md 是可选的） |
| **implement.jsonl 为空** | 降级为 prd-only + 自己匹配 spec |
| **prd.md 不存在** | 询问用户，不盲目工作 |
| **规范文件不存在** | 静默跳过该条目 |
| **需要 git 操作** | 拒绝（commit/push/merge 被明确禁止） |
| **需要并行工作** | 在报告中建议主会话派发额外子智能体 |
| **lint/type-check 失败** | 自行修复后重新运行 |
| **Codex: 修改 .trellis/scripts/** | 必须同步更新 `packages/cli/src/templates/trellis/scripts/` |

---

## 十、总结

`trellis-implement` 的设计围绕三个核心原则：

1. **规范驱动**：所有实现以 `.trellis/spec/` 中的规范为准绳，而非凭空发挥
2. **克制实现**："只做必要的"——不过度工程化、不引入不必要抽象、遵循现有模式
3. **上下文隔离**：实现工作在独立的子智能体窗口中完成，不污染主会话

它与 `trellis-check` 形成了 Trellis 的质量闭环：implement 产出 → check 审查修复 → 主会话提交。每个环节各司其职，子智能体永不越界。
