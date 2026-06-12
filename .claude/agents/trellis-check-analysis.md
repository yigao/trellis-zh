# trellis-check 智能体详细分析文档

> 分析对象：`.claude/agents/trellis-check.md`（主定义）、`.claude/skills/trellis-check/SKILL.md`（内联使用）、`.codex/agents/trellis-check.toml`（Codex 平台）
> 关联文档：`inject-subagent-context-analysis.md`（上下文注入钩子）、`trellis-implement.md`（实现智能体）

---

## 一、概述

`trellis-check` 是 Trellis 项目管理系统中的 **代码质量检查智能体（Check Agent）**。它在 Trellis 工作流的**阶段 2.2（检查）** 被主会话分派，负责：

- **审查代码变更**：对照项目规范和 PRD 逐项检查
- **自行修复问题**：使用 Write/Edit 工具直接修改代码（而非仅报告）
- **运行验证**：执行 lint、type-check、tests 并修复失败
- **报告结果**：输出结构化的检查报告

`trellis-check` 与 `trellis-implement` 形成"实现→检查"的双智能体循环。当 check 发现需要更多实现工作时，它向主会话报告建议；主会话决定是否再次派发 implement。

---

## 二、文件架构

`trellis-check` 由三个文件定义，覆盖不同使用场景：

```
.claude/
├── agents/
│   └── trellis-check.md          ← Claude Code 子智能体定义（Agent 工具调用）
├── skills/
│   └── trellis-check/
│       └── SKILL.md              ← 内联 Skill 定义（/trellis-check 命令）
└── hooks/
    └── inject-subagent-context.py ← 上下文注入钩子（PreToolUse）

.codex/
└── agents/
    └── trellis-check.toml        ← Codex 平台子智能体定义
```

### 2.1 三文件对比

| 维度 | Agent 定义 | Skill 定义 | Codex 定义 |
|------|-----------|-----------|-----------|
| **文件** | `.claude/agents/trellis-check.md` | `.claude/skills/trellis-check/SKILL.md` | `.codex/agents/trellis-check.toml` |
| **触发方式** | 主会话 `Agent` 工具调用 | 用户 `/trellis-check` 命令 | Codex 平台 spawn_agent |
| **执行环境** | 独立子智能体（隔离上下文） | 主会话内联执行 | 独立子智能体（workspace-write 沙箱） |
| **上下文注入** | 钩子自动注入（PreToolUse） | 无钩子 — 自己读取 | 手动加载协议（class-2 平台） |
| **工具集** | Read, Write, Edit, Bash, Glob, Grep, Exa MCP | 继承主会话全部工具 | 继承 Codex 工具（多智能体已禁用） |
| **递归防护** | 有（禁止再派子智能体） | 无（内联执行无此问题） | 有（禁止再派子智能体） |
| **格式** | Markdown + YAML frontmatter | Markdown + YAML frontmatter | TOML |

### 2.2 为什么有三种定义？

```
用户输入 "/trellis-check"
  │
  ├─→ Skill 被调用（主会话内联）
  │     └─ 适用场景：用户主动检查、快速质量验证
  │
用户派发 implement 后自动 → check
  │
  └─→ Agent 被分派（子智能体隔离）
        ├─ Claude Code: 钩子自动注入上下文
        └─ Codex: 子智能体手动加载上下文
```

**Skill（内联）** 用于用户主动触发的快速检查，共享主会话上下文。
**Agent（子智能体）** 用于工作流自动分派，拥有隔离的干净上下文窗口。

---

## 三、Agent 定义逐段分析

### 3.1 YAML Frontmatter（元数据）

```yaml
---
name: trellis-check
description: |
  Code quality check expert. Reviews code changes against specs and self-fixes issues.
tools: Read, Write, Edit, Bash, Glob, Grep, mcp__exa__web_search_exa, mcp__exa__get_code_context_exa
---
```

| 字段 | 值 | 说明 |
|------|---|------|
| `name` | `trellis-check` | 智能体类型标识，钩子用它匹配 `AGENT_CHECK` 常量 |
| `description` | Code quality check expert... | 简短描述，显示在工具选择 UI 中 |
| `tools` | 8 个工具 | 精确控制可用工具：读写文件、Shell、搜索、Exa MCP |

**工具选择分析**：
- `Read` — 读取规范文件和代码
- `Write` / `Edit` — **自行修复**的核心工具
- `Bash` — 运行 `git diff`、lint、type-check
- `Glob` / `Grep` — 搜索代码模式
- `mcp__exa__*` — 外部文档搜索（Exa MCP）

**注意**：没有 `Agent` 工具 — 物理上防止了子智能体再派发子智能体（递归防护的结构性保障）。

### 3.2 递归防护（Recursion Guard）

```
你已经是主会话分派出来的 trellis-check 子智能体。请直接执行审查和修复工作。

- 不要派生另一个 trellis-check 或 trellis-implement 子智能体。
- 如果 SessionStart 上下文……说要分派 trellis-implement / trellis-check，
  请将其视为已由你当前角色满足的主会话指令。
- 只有主会话才能分派 Trellis 的 implement/check 智能体。
  如果需要更多实现工作，请报告建议而不是派生子智能体。
```

**设计原理**：防止无限递归。由于子智能体的系统提示可能包含与主会话相同的 `<guidelines>` 块（其中包含"派发 trellis-implement / trellis-check"的指令），子智能体必须理解自己**已经**是那个被派发的智能体。

**三层防护**：
1. **提示词防护**（Agent 定义中的递归防护说明）
2. **工具集防护**（Agent 定义中不含 `Agent` 工具）
3. **平台级防护**（Codex 中 `multi_agent = false` 禁用 spawn_agent）

### 3.3 Trellis 上下文加载协议

```
请在你的输入内容中查找 <!-- trellis-hook-injected --> 标记。

- 如果标记存在：prd / spec / research 文件已在你的输入内容中自动加载。
  直接进行质量检查工作。
- 如果标记不存在：钩子注入未触发（Windows + Claude Code、--continue 恢复、
  fork 分发、钩子已禁用等情况）。请从分派提示的第一行
  Active task: <path> 找到活动任务路径，然后自行读取
  <task-path>/prd.md 和 <task-path>/check.jsonl 中列出的规范文件，再进行工作。
```

**这是 trellis-check 的上下文来源决策树**：

```
子智能体启动
  │
  ├─ 输入中有 <!-- trellis-hook-injected -->？
  │   ├─ YES → 上下文已注入，直接工作（Class-1 平台正常路径）
  │   └─ NO  → 查找 Active task: <path>（分派提示第一行）
  │             ├─ 找到 → 自行读取 prd.md + check.jsonl
  │             └─ 未找到 → 运行 task.py current 获取任务路径
  │                           ├─ 找到 → 自行读取上下文
  │                           └─ 未找到 → 询问用户
```

**设计意图**：钩子是"自动挡"——大多数情况下透明工作。但当钩子因平台限制（Windows + Claude Code 的 PreToolUse 静默跳过）或恢复场景（`--continue`）失败时，子智能体有完整的"手动挡"后备方案。

### 3.4 核心职责

```
1. 获取代码变更 - 使用 git diff 获取未提交的代码
2. 对照规范检查 - 验证代码是否遵循指南
3. 自行修复 - 自己动手修复问题，而不仅仅是报告问题
4. 运行验证 - 执行类型检查和代码风格检查
```

**核心原则：自己动手修复（Self-Fix）**

与传统的"审查者只报告"模式不同，`trellis-check` 被赋予 Write/Edit 权限，要求直接修复发现的问题。这减少了"报告→修复→再检查"的往返次数。

### 3.5 四步工作流

```
步骤 1: 获取变更
  ├─ git diff --name-only  → 列出已更改的文件
  └─ git diff              → 查看具体变更内容

步骤 2: 对照规范检查
  ├─ 阅读 .trellis/spec/ 中的相关规范
  ├─ 检查目录结构惯例
  ├─ 检查命名惯例
  ├─ 检查代码模式
  ├─ 检查类型定义
  └─ 检查潜在 bug

步骤 3: 自行修复
  ├─ 直接修复问题（Edit 工具）
  ├─ 记录修复的内容
  └─ 继续检查其他问题

步骤 4: 运行验证
  ├─ 运行 lint 命令
  ├─ 运行 type-check 命令
  └─ 失败 → 修复 → 重新运行（循环直到通过）
```

### 3.6 报告格式

Agent 定义规定了结构化报告格式：

```markdown
## Self-Check Complete（自行检查完成）

### Files Checked（已检查文件）
- 列出所有被检查的文件

### Issues Found and Fixed（发现并修复的问题）
1. <file>:<line> - <修复的内容>

### Issues Not Fixed（未修复的问题）
（无法自行修复的问题，附原因）

### Verification Results（验证结果）
- TypeCheck: Passed / Failed
- Lint: Passed / Failed

### Summary（总结）
Checked X files, found Y issues, all fixed.
```

---

## 四、Skill 定义分析

Skill（`.claude/skills/trellis-check/SKILL.md`）用于**内联执行**——当用户输入 `/trellis-check` 时在主会话中运行。

### 4.1 与 Agent 定义的关键差异

| 维度 | Agent（子智能体） | Skill（内联） |
|------|-----------------|-------------|
| **上下文** | 隔离，只含注入的 spec + prd | 共享主会话全部上下文 |
| **递归防护** | 需要（防止再派子智能体） | 不需要（内联执行） |
| **上下文加载** | 依赖钩子或手动协议 | 自己运行 `get_context.py` |
| **工作流步骤** | 4 步（获取→检查→修复→验证） | 6 步（识别→读规范→运行检查→对照清单→跨层维度→报告修复） |

### 4.2 Skill 的六步工作流

```
步骤 1: 识别变更内容
  └─ git diff --name-only HEAD + git status

步骤 2: 阅读适用的 Spec
  ├─ py -3 ./.trellis/scripts/get_context.py --mode packages
  └─ 对每个变更的 package/layer，阅读 spec 索引及其引用的指南文件

步骤 3: 运行项目检查
  └─ lint + type-check + tests → 修复所有失败

步骤 4: 对照 Checklist 审查
  ├─ 代码质量：Linter、类型检查、测试、调试日志、类型安全绕过
  ├─ 测试覆盖：新函数有测试？Bug 修复有回归测试？行为变更更新已有测试？
  └─ Spec 同步：.trellis/spec/ 是否需要更新？

步骤 5: 跨层维度（如变更涉及 3 层以上）
  ├─ A. 数据流：Storage→Service→API→UI 追踪
  ├─ B. 代码复用：搜索已有模式、提取共享常量
  ├─ C. 导入/依赖：路径正确性、无循环依赖
  └─ D. 同层一致性：同一概念在其他位置是否一致

步骤 6: 报告并修复
  └─ 报告违规项 → 直接修复 → 重新运行项目检查
```

### 4.3 Skill 独有的"跨层维度"检查

Skill 的步骤 5 是 Agent 定义中未明确列出的深度检查：

**A. 数据流**：追踪数据在各层之间的完整路径
- 读取流程：Storage → Service → API → UI
- 写入流程：UI → API → Service → Storage
- 类型/模式在各层间传递正确？
- 错误正确传播至调用者？

**B. 代码复用**：防止"又多了一份拷贝"
- 在创建新代码前搜索已有类似代码（`grep -r "pattern" src/`）
- 如果 2 处以上定义了相同值 → 提取为共享常量
- 批量修改后，所有出现都已更新？

**C. 导入/依赖**：防止循环依赖和路径错误

**D. 同层一致性**：同一概念在其他位置是否表现一致

---

## 五、Codex 平台定义分析

`.codex/agents/trellis-check.toml` 是 Codex 平台的子智能体定义，与 Claude Code 版本有显著差异。

### 5.1 关键差异

```toml
name = "trellis-check"
description = "Workspace-write Trellis reviewer that self-fixes spec drift, lint/type-check failures, and missing tests."
sandbox_mode = "workspace-write"

[features]
multi_agent = false

[features.multi_agent_v2]
enabled = false
```

| 特性 | Claude Code | Codex |
|------|------------|-------|
| **沙箱模式** | 无（继承主会话） | `workspace-write`（显式声明） |
| **多智能体** | 无 Agent 工具即禁用 | `multi_agent = false` 显式禁用 |
| **上下文加载** | 钩子自动注入 | 手动加载协议（3 步） |
| **分派协议** | 钩子处理 | 依赖主会话 `Active task:` 行 |

### 5.2 Codex 的手动上下文加载协议

Codex 作为 class-2 平台，**没有钩子系统**。因此子智能体必须自己加载上下文：

```
Step 1: 找到活动任务路径（3 种方法按优先级尝试）
  ├─ 1. 分派提示第一行 "Active task: <path>"
  ├─ 2. 运行 py -3 ./.trellis/scripts/task.py current --source
  └─ 3. 询问用户

Step 2: 加载任务上下文
  ├─ 1. 读取 prd.md（需求）和 info.md（技术设计）
  ├─ 2. 读取 check.jsonl（检查规范索引）
  └─ 3. 逐条读取 JSONL 中引用的每个 spec 文件
```

### 5.3 JSONL 解析规则

```json
{"file": ".trellis/spec/backend/api-layer/index.md", "reason": "API 层规范"}
{"file": ".trellis/spec/backend/data-layer/", "type": "directory", "reason": "数据层所有规范"}
{"_example": "没有 file 字段的种子行，将被静默跳过"}
```

处理逻辑：
```
逐行读取 JSONL
  → 跳过空行
  → JSON 解码（失败则跳过该行）
  → 提取 file 或 path 字段
  → 无 file 字段 → 跳过（种子行/注释行）
  → type == "directory" → 读取目录中所有 .md 文件
  → type == "file"（默认）→ 读取单个文件
  → 文件不存在 → 静默跳过
```

### 5.4 降级策略

Codex 版本有完善的降级路径：

```
check.jsonl 无已整理条目？
  └─ 回退方案：读 prd.md + 列出可用 spec（get_context.py --mode packages）
       → 自己根据任务领域选择合适的 spec → 继续工作

prd.md 不存在？
  └─ 询问用户 → 不猜测，不盲目继续
```

---

## 六、上下文注入系统集成

`trellis-check` 的上下文注入由 `.claude/hooks/inject-subagent-context.py`（PreToolUse 钩子）处理。

### 6.1 注入流程

```
主会话调用 Agent(subagent_type="trellis-check", prompt="...")
  │
  ▼
PreToolUse 钩子触发
  │
  ├─ 检测子智能体类型 == "trellis-check"
  ├─ 解析活动任务路径
  ├─ 读取 <task>/check.jsonl
  ├─ 读取 <task>/prd.md
  ├─ 构建注入提示词（build_check_prompt）
  └─ 更新 tool_input.prompt
  │
  ▼
子智能体启动，收到已注入完整上下文的 prompt
```

### 6.2 Check 专用上下文

| 上下文来源 | 文件 | 说明 |
|-----------|------|------|
| **检查规范** | `<task>/check.jsonl` 中引用的所有文件 | 开发规范、编码约定、检查清单 |
| **需求文档** | `<task>/prd.md` | 用于验证需求是否被满足 |

与 Implement 智能体的对比：
- Implement 加载 `implement.jsonl` + `prd.md` + `info.md`（3 项）
- Check 加载 `check.jsonl` + `prd.md`（2 项，不需要技术设计文档）

### 6.3 Finish 阶段变体

当原始 prompt 包含 `[finish]` 标记时，钩子使用 `build_finish_prompt()` 构建不同的提示词：

| 维度 | 常规 Check | Finish Check |
|------|-----------|-------------|
| **触发** | 阶段 2.2 自动分派 | prompt 含 `[finish]` |
| **角色** | 代码和跨层检查器 | PR 前最终检查 |
| **工作流** | 获取变更→检查→修复→验证 | 审查变更→验证需求→规范同步→最终检查→确认就绪 |
| **规范更新** | 不建议 | 可以更新 spec 文件（含 update-spec.md 7 段式模板） |
| **重点** | 发现并修复问题 | 确认所有需求已满足、规范已同步 |

---

## 七、完整生命周期

```
┌─────────────────────────────────────────────────────────┐
│                    主会话（Main Session）                  │
│                                                         │
│  阶段 2.1: 派发 trellis-implement                        │
│    └─ implement 完成，返回报告                            │
│                                                         │
│  阶段 2.2: 派发 trellis-check                            │
│    │                                                    │
│    └─ Agent(subagent_type="trellis-check", prompt="...") │
│                                                         │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              PreToolUse 钩子（Claude Code）               │
│                                                         │
│  inject-subagent-context.py:                            │
│    1. 检测到 trellis-check 类型                          │
│    2. 加载 check.jsonl + prd.md                         │
│    3. 构建注入后的 prompt                                │
│    4. 返回更新后的 tool_input                            │
│                                                         │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│               trellis-check 子智能体                      │
│                                                         │
│  上下文加载判断:                                          │
│    ├─ <!-- trellis-hook-injected --> 存在？               │
│    │   ├─ YES → 直接工作                                 │
│    │   └─ NO  → 手动加载（Active task: / task.py）       │
│                                                         │
│  工作流执行:                                              │
│    ├─ 步骤 1: git diff 获取变更                           │
│    ├─ 步骤 2: 对照 spec 检查代码                          │
│    ├─ 步骤 3: 自行修复问题（Write/Edit）                   │
│    └─ 步骤 4: 运行 lint + type-check 验证                 │
│                                                         │
│  输出: 结构化检查报告                                     │
│                                                         │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    主会话（Main Session）                  │
│                                                         │
│  收到检查报告:                                            │
│    ├─ 全部通过 → 阶段 2.3: trellis-update-spec           │
│    ├─ 有问题但已修复 → 阶段 2.3                          │
│    └─ 有未修复问题 → 决定是否重新派发 implement            │
│                                                         │
│  阶段 3: 完成工作                                         │
│    └─ 提交 → /trellis:finish-work                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 八、与 trellis-implement 的对比

| 维度 | trellis-implement | trellis-check |
|------|-------------------|---------------|
| **角色** | 代码实现者 | 代码审查者 |
| **阶段** | 阶段 2.1（执行） | 阶段 2.2（验证） |
| **输入** | prd.md + info.md + implement.jsonl | prd.md + check.jsonl |
| **核心动作** | 编写代码 | 审查 + 修复代码 |
| **git 操作** | 禁止 commit/push/merge | 无限制（但通常不 commit） |
| **工具** | 相同（8 个） | 相同（8 个） |
| **报告格式** | Implementation Complete | Self-Check Complete |
| **技术设计** | 需要 info.md（技术设计） | 不需要 |
| **递归防护** | 相同措辞 | 相同措辞 |
| **上下文大小** | ~8KB（implement.jsonl + prd + info） | ~5KB（check.jsonl + prd） |

---

## 九、设计亮点

### 9.1 自我修复而非仅报告

传统的代码审查工具只输出问题列表，由开发者手动修复。`trellis-check` 被赋予 Write/Edit 权限，直接修复能自动修复的问题——只有需要人工判断的问题才留给开发者。

### 9.2 多层上下文降级

```
Class-1 平台（Claude Code / Cursor）:
  钩子注入 → 完全自动

Class-1 平台（钩子失败）:
  Active task: 行 → 手动加载

Class-2 平台（Codex / Copilot / Gemini / Qoder）:
  Active task: 行 → 手动加载（标准路径）
  task.py current → 后备
  询问用户 → 最终后备
```

任何一层失败都有下一层兜底。

### 9.3 递归防护的三层保障

1. **提示词层**：明确告知"你已经是子智能体，不要再派发"
2. **工具集层**：Agent 定义中不包含 Agent 工具
3. **平台层**：Codex 中 `multi_agent = false` 物理禁用

### 9.4 双模式设计

同一智能体定义通过简单的标记位 `[finish]` 切换行为模式：
- **常规模式**：深度检查 + 自我修复（阶段 2.2）
- **Finish 模式**：PR 前轻量检查 + 规范同步（阶段 3）

---

## 十、边界情况与已知限制

| 场景 | 行为 |
|------|------|
| **无未提交变更** | 报告"nothing to check"，正常退出 |
| **check.jsonl 为空** | 降级为 prd-only 模式 |
| **prd.md 不存在** | 询问用户，不盲目工作 |
| **规范文件不存在** | 静默跳过该条目 |
| **lint/type-check 失败** | 修复后重新运行，循环直到通过 |
| **需要大规模重构** | 报告为 Issues Not Fixed，建议重新派发 implement |
| **钩子注入失败** | 子智能体自行加载（Active task: 行） |
| **Windows + Claude Code** | 钩子可能静默跳过，子智能体走手动加载路径 |

---

## 十一、总结

`trellis-check` 是 Trellis 质量保障体系的核心组件。它的设计哲学是：

1. **自动化优先**：能自动修的不报告，能自动加载的不手动
2. **降级优雅**：钩子失败 → 手动加载 → 询问用户，层层兜底
3. **职责清晰**：只做检查和修复，不做实现；需要大改时如实报告
4. **上下文隔离**：通过子智能体模式，不让审查的 spec 污染主会话上下文窗口
5. **平台无关**：同一套逻辑适配 Claude Code、Cursor、Codex、Copilot 等 8+ 平台
