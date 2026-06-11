# inject-subagent-context.py 详细分析文档

> 分析对象：`.claude/hooks/inject-subagent-context.py`（748 行）
> 依赖模块：`.trellis/scripts/common/active_task.py`（626 行）
> 关联文档：`inject-workflow-state-analysis.md`（UserPromptSubmit 钩子分析）、`session-start-analysis.md`（SessionStart 钩子分析）

---

## 一、概述

`inject-subagent-context.py` 是 Trellis 项目管理系统的 **PreToolUse 钩子（Hook）**。当用户在 AI 编程助手中派生（spawn）一个 Trellis 子智能体（implement、check、research）时，宿主 CLI 在 `Task` / `Agent` 工具调用执行之前调用此脚本，脚本拦截原始 prompt，从文件系统加载任务相关的上下文文件，将其注入到子智能体的 prompt 中，然后返回更新后的工具输入。

**核心理念**：钩子负责注入全部上下文——子智能体以完整信息自主工作，无需恢复、无需分段，行为由 Python 代码而非 AI 提示词控制。

### 与其他钩子的对比

| 特性 | session-start.py | inject-workflow-state.py | **inject-subagent-context.py** |
|------|-----------------|--------------------------|-------------------------------|
| 触发时机 | 会话启动（一次性） | 每次用户输入（每轮） | 派生子智能体时（PreToolUse） |
| 上下文大小 | ~9-12 KB | ~300-800 B | 可变（取决于 JSONL 条目数） |
| 作用对象 | 主会话 AI | 主会话 AI | 子智能体（implement/check/research） |
| 核心操作 | 注入项目状态 | 注入工作流面包屑 | 注入任务上下文文件 |
| 输出目标 | stdout → 注入到系统提示 | stdout → 注入到用户提示 | stdout → 更新工具输入 |

---

## 二、架构设计

### 2.1 上下文来源体系

```
任务目录 ({task_dir})/
├── implement.jsonl    ← Implement 智能体专用上下文索引
├── check.jsonl        ← Check 智能体专用上下文索引
├── prd.md             ← 需求文档（PRD）
└── info.md            ← 技术设计文档
```

每个 JSONL 文件是一个上下文索引，每一行 JSON 描述一个需要注入的文件或目录：

```json
{"file": "path/to/spec.md", "reason": "开发规范 — API 设计约定"}
{"file": "path/to/guides/", "type": "directory", "reason": "思维指南目录"}
```

### 2.2 智能体类型与上下文矩阵

| 智能体类型 | 常量 | JSONL 文件 | 额外文件 | 需要任务目录 |
|-----------|------|-----------|---------|------------|
| Implement | `trellis-implement` | `implement.jsonl` | `prd.md` + `info.md` | ✅ 必须 |
| Check | `trellis-check` | `check.jsonl` | `prd.md` | ✅ 必须 |
| Research | `trellis-research` | 无（动态构建） | Spec 目录树 | ❌ 可选 |

### 2.3 特殊阶段：Finish

当用户 prompt 中包含 `[finish]` 标记时，`trellis-check` 智能体使用 **Finish 上下文**（更轻量，专注于最终验证和规范同步），而非常规的 Check 上下文（完整规范用于自修复循环）。

---

## 三、执行流程详解

### 3.1 主函数 `main()` 流程

```
stdin JSON 解析
  → 环境变量检查（TRELLIS_HOOKS / TRELLIS_DISABLE_HOOKS）
  → 钩子输入解析（_parse_hook_input）
  → 子智能体类型过滤
  → 仓库根目录查找
  → 活动任务解析（get_current_task）
  → 任务目录检查（implement/check 必须存在）
  → Finish 阶段检测（[finish] 标记）
  → 上下文加载 + 提示词构建
  → 多平台输出格式组装
  → stdout JSON 输出
```

### 3.2 平台检测 `_detect_platform()`

采用三层检测策略，优先级从高到低：

| 层级 | 检测方式 | 可靠性 |
|------|---------|--------|
| 1 | `cursor_version` 字段（Cursor 特有） | 高 |
| 2 | 环境变量（`CLAUDE_PROJECT_DIR`, `CURSOR_PROJECT_DIR` 等 8 个） | 高 |
| 3 | 脚本路径分析（`sys.argv[0]` 中包含 `.claude`/`.cursor` 等） | 中 |

支持 8 个平台：Claude Code、Cursor、CodeBuddy、Droid (Factory)、Gemini、Qoder、Kiro、Copilot。

### 3.3 钩子输入解析 `_parse_hook_input()`

处理三种主要平台输入格式：

| 平台 | tool_name 格式 | 子智能体类型位置 |
|------|---------------|----------------|
| Claude Code / Qoder / CodeBuddy / Droid | `Task` / `Agent` | `tool_input.subagent_type` |
| Cursor | `Task` / `Subagent` | `tool_input.subagent_type`（支持 protobuf oneof 编码） |
| Gemini CLI | 智能体名称本身 | `tool_name` 即智能体名 |
| Copilot CLI | camelCase（`toolName`） | `toolName` 字段 |
| Kiro | `agentSpawn` hook | 顶层 `agent_name` 字段 |

### 3.4 子智能体名称提取 `_extract_subagent_name()`

这是最复杂的解析函数之一，处理以下编码方式：

1. **直接字符串**：`"trellis-implement"`
2. **字典 - name 键**：`{"name": "trellis-implement"}`
3. **字典 - subagent_type_name / subagentTypeName 键**
4. **Cursor protobuf oneof - custom 嵌套**：
   - `{"custom": {"name": "trellis-implement"}}`
   - `{"type": {"case": "custom", "value": {"name": "trellis-implement"}}}`
5. **case/value 顶层嵌套**：`{"case": "custom", "value": {"name": "..."}}`
6. **回退匹配**：在字典中搜索 `AGENTS_ALL` 中的已知智能体名称

---

## 四、上下文构建详解

### 4.1 Implement 智能体上下文 (`get_implement_context`)

```
读取顺序:
┌──────────────────────────────────────┐
│ 1. implement.jsonl (所有引用文件)      │  ← 开发规范、编码约定
├──────────────────────────────────────┤
│ 2. prd.md (需求文档)                  │  ← 功能需求、验收标准
├──────────────────────────────────────┤
│ 3. info.md (技术设计文档)              │  ← 架构决策、技术约束
└──────────────────────────────────────┘
```

注入的提示词结构（`build_implement_prompt`）：
- `<!-- trellis-hook-injected -->` 标记
- 角色定义：Implement 智能体
- 上下文区块：所有注入文件
- 任务区块：原始 prompt
- 工作流指引：理解规范 → 理解需求 → 实现功能 → 自检
- 约束：不执行 git commit、遵循规范、报告文件列表

### 4.2 Check 智能体上下文 (`get_check_context`)

```
读取顺序:
┌──────────────────────────────────────┐
│ 1. check.jsonl (所有引用文件)          │  ← 检查规范、检查清单
├──────────────────────────────────────┤
│ 2. prd.md (需求文档)                  │  ← 用于验证需求是否满足
└──────────────────────────────────────┘
```

注入的提示词结构（`build_check_prompt`）：
- 角色定义：Check 智能体（代码和跨层检查器）
- 上下文区块
- 任务区块
- 工作流指引：获取变更 → 对照规范检查 → 自行修复 → 运行验证
- 约束：自己修复而非仅报告、完整检查清单、L1-L5 影响范围分析

#### Finish 阶段变体 (`build_finish_prompt`)

当原始 prompt 包含 `[finish]` 时触发，上下文来源相同但提示词不同：
- 角色定义：PR 前最终检查
- 工作流指引：审查变更 → 验证需求 → 规范同步（含 update-spec.md 7 段式模板）→ 运行最终检查 → 确认就绪
- 特殊约束：可以更新 spec 文件、编辑前必须读取目标 spec、不为微小变更更新规范

### 4.3 Research 智能体上下文 (`get_research_context`)

Research 智能体**不依赖任务目录**，上下文动态构建：

```
上下文来源:
┌──────────────────────────────────────┐
│ 1. Spec 目录树（动态扫描）              │  ← .trellis/spec/ 下的包和层结构
├──────────────────────────────────────┤
│ 2. 搜索提示                            │  ← Spec 路径、搜索工具说明
└──────────────────────────────────────┘
```

注入的提示词结构（`build_research_prompt`）：
- 核心原则：只做查找和解释信息
- 项目信息：Spec 目录结构
- 搜索工具表：Glob、Grep、Read、Exa Web Search、Exa Code Context
- 严格边界：仅允许描述存在什么、在哪里、如何工作
- 禁止项：提改进建议、批评实现、建议重构、修改文件

---

## 五、JSONL 解析机制 (`read_jsonl_entries`)

### 5.1 条目格式

```json
{"file": ".trellis/spec/backend/api-layer/index.md", "reason": "API 层开发规范"}
{"file": ".trellis/spec/backend/data-layer/", "type": "directory", "reason": "数据层所有规范"}
{"_example": "此条目没有 file 字段，将被静默跳过（种子行）"}
```

### 5.2 解析逻辑

```
逐行读取 JSONL
  → 跳过空行
  → JSON 解码（失败则跳过）
  → 提取 file 或 path 字段
  → 无 file 字段 → 静默跳过（种子/注释行）
  → type == "directory" → 读取目录中所有 .md 文件（最多 20 个）
  → type == "file"（默认） → 读取单个文件
  → 文件不存在 → 静默跳过
```

### 5.3 警告机制

| 条件 | 警告信息 |
|------|---------|
| JSONL 文件不存在 | `警告: {jsonl_path} 未找到 — 子智能体将仅收到 prd.md` |
| JSONL 无已整理条目 | `警告: {jsonl_path} 没有已整理的条目（仅有种子/空行）— 子智能体将仅收到 prd.md` |

---

## 六、输出格式（多平台兼容）

脚本输出一个包含三种格式的 JSON 对象，各平台选择自己能理解的字段：

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "updatedInput": { "...": "..." }
  },
  "permission": "allow",
  "updated_input": { "...": "..." },
  "updatedInput": { "...": "..." }
}
```

| 字段 | 目标平台 |
|------|---------|
| `hookSpecificOutput.updatedInput` | Claude Code / Qoder / CodeBuddy / Droid |
| `updated_input` | Cursor |
| `updatedInput` | Gemini CLI |

所有平台的 `updatedInput` 值相同——原始 `tool_input` 字典的副本，但 `prompt` 字段被替换为注入上下文后的完整提示词。

---

## 七、错误处理与边界情况

### 7.1 优雅降级策略

| 场景 | 行为 |
|------|------|
| stdin JSON 解析失败 | `sys.exit(0)` — 静默退出，不阻止工具调用 |
| 非 Trellis 子智能体类型 | `sys.exit(0)` — 不做任何修改 |
| 找不到仓库根目录 | `sys.exit(0)` — 非 git 项目，跳过 |
| 任务目录解析失败 | implement/check → `sys.exit(0)`；research → 继续 |
| 任务目录不存在 | implement/check → `sys.exit(0)` |
| 上下文为空 | `sys.exit(0)` — 不注入空上下文 |
| JSONL 文件不存在 | 向 stderr 输出警告，返回空列表 |
| 引用文件不存在 | 静默跳过该条目 |
| JSONL 条目 JSON 解码失败 | 静默跳过该行 |

### 7.2 Windows 兼容性

```python
# 在 Windows 上强制 stdout 使用 UTF-8
# 修复输出非 ASCII 字符时的 UnicodeEncodeError
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
```

### 7.3 环境变量开关

| 环境变量 | 效果 |
|---------|------|
| `TRELLIS_HOOKS=0` | 完全跳过钩子 |
| `TRELLIS_DISABLE_HOOKS=1` | 完全跳过钩子 |

---

## 八、与 active_task.py 的集成

`inject-subagent-context.py` 通过 `get_current_task()` 函数调用 `active_task.py` 中的 `resolve_active_task()`：

```
inject-subagent-context.py
  └── get_current_task(repo_root, input_data)
        └── _detect_platform(input_data)  ← 本地检测（与 active_task.py 的检测独立）
        └── active_task.resolve_active_task(repo_root, input_data, platform)
              └── resolve_context_key()  ← 解析会话身份
              └── _resolve_single_session_fallback()  ← 第二类平台回退
              └── 返回 ActiveTask(task_path, source_type, context_key)
```

关键点：
- 钩子脚本中的 `_detect_platform()` 与 `active_task.py` 中的 `_detect_platform()` **相互独立**——前者用于传递给 `resolve_active_task()` 的平台提示，后者是最终裁决
- `get_current_task()` 只使用 `ActiveTask.task_path` 字段
- Research 智能体不强制要求任务目录，因此任务解析失败不会阻止其执行

---

## 九、配置常量与可定制性

```python
# 路径常量（修改此处可重命名目录）
DIR_WORKFLOW = ".trellis"
DIR_SPEC = "spec"
FILE_TASK_JSON = "task.json"

# 子智能体常量（修改此处可重命名子智能体类型）
AGENT_IMPLEMENT = "trellis-implement"
AGENT_CHECK = "trellis-check"
AGENT_RESEARCH = "trellis-research"

# 需要任务目录的智能体
AGENTS_REQUIRE_TASK = (AGENT_IMPLEMENT, AGENT_CHECK)
```

---

## 十、设计原理：为什么子智能体的上下文"大"是合理的

### 10.1 常见疑问

> 钩子把 spec 文件注入子智能体 prompt，子智能体的上下文不就变得和主体一样大了吗？这不是拆东墙补西墙？

### 10.2 核心答案：上下文隔离 ≠ 上下文缩小

关键是理解**主体的上下文负担来自哪里**：

| 上下文来源 | 主会话 | 子智能体 |
|-----------|--------|---------|
| **对话历史** | 几十轮交互、可能 30-60K token，且持续增长 | **零** — 全新窗口 |
| **SessionStart 注入** | 项目状态 + 工作流 + spec 索引 + guidelines ≈ 10KB | **零** — 不注入 |
| **每轮 workflow-state** | 每轮累加的状态面包屑 | **零** |
| **之前讨论过的无关文件** | 大量已读但不再相关的代码 | **零** |
| **任务上下文（spec）** | 主体不加载 | 精准注入 implement.jsonl + prd.md + info.md |

### 10.3 量化对比

```
主体上下文窗口:
  ┌────────────────────────────────────────────┐
  │ 对话历史 (~40KB)  │  项目状态 (~10KB)       │
  │ 工作流指南 (~5KB)  │  讨论噪音 (~15KB)       │
  │ 每轮注入 (~1KB/轮) │  已读文件缓存 (~??KB)   │
  └────────────────────────────────────────────┘
  总计: 70KB+，随对话持续增长，终点未知

子智能体上下文窗口:
  ┌────────────────────────────────────────────┐
  │ 注入的 spec 上下文 (~8KB)  │ 任务 prompt    │
  └────────────────────────────────────────────┘
  总计: ~8KB，固定不变，可预测
```

**子智能体的 prompt 虽然包含 spec 文件（"大"），但它没有历史包袱。** 主体真正的上下文开销是对话历史的累积——那才是无底洞。

### 10.4 架构收益

```
每轮交互的 token 流向:

无钩子方案（主体自己读 spec 实现）:
  Round 1: 主体读 specA (2KB) + specB (3KB) + prd.md (1KB)
           → 这些文件永久占据主体的上下文缓存，后续每轮都在消耗
  Round 2: 主体读 specC (2KB) → 缓存 8KB
  Round N: ...上下文持续膨胀

有钩子方案（子智能体扛上下文）:
  Round 1: 主体派 implement (50B) → 子智能体加载 8KB → 返回结果 (200B)
           子智能体上下文释放，主体只保留 "已完成" 这一事实
  Round 2: 主体派 check (50B) → 子智能体加载 5KB → 返回结果 (200B)
  Round N: 主体上下文始终轻盈
```

### 10.5 一句话总结

> 钩子不是"帮主体省 token 然后让子智能体扛"，而是**让主体无需污染自己的上下文窗口去加载 spec 文件**——主体只做轻量调度，子智能体在隔离环境中负重前行，完事后它的整个上下文窗口被释放，主体只收到结果摘要。

---

## 十一、设计亮点

1. **关注点分离**：钩子负责上下文注入，子智能体负责执行——各司其职
2. **上下文隔离**：主体不加载 spec 文件，子智能体用干净窗口处理完即释放（详见第十章）
3. **代码控制而非提示词控制**：上下文选择逻辑由 Python 代码决定，不受 AI 提示词工程的不确定性影响
4. **多平台一次编写**：通过 `_extract_subagent_name()` 的深度解析和三层输出格式，覆盖 8+ 平台
5. **JSONL 索引模式**：JSONL 作为上下文索引，解耦了"需要哪些文件"和"文件内容是什么"
6. **优雅降级**：几乎所有错误分支都是静默退出，不会因钩子故障而阻止用户的工具调用
7. **可观测性**：通过 stderr 输出警告，帮助调试上下文缺失问题（不污染 stdout JSON 输出）
8. **Finish 阶段复用**：Check 智能体通过简单的 `[finish]` 标记切换为更轻量的 PR 前检查模式
