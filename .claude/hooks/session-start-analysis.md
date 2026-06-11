# session-start.py 详细分析文档

> 分析对象：`.claude/hooks/session-start.py`（主版本，793 行）
> 对比参考：`.codex/hooks/session-start.py`（Codex 变体，482 行）

---

## 一、概述

`session-start.py` 是 Trellis 项目管理系统的 **SessionStart 钩子（Hook）**。当 AI 编程助手（Claude Code、Cursor、CodeBuddy 等）启动新会话时，宿主 CLI 调用此脚本，脚本向 AI 注入结构化的项目上下文——包括当前任务状态、工作流指南、spec 索引等，使 AI 无需手动探查即可理解项目全貌。

### 核心目标

| 目标 | 说明 |
|------|------|
| **上下文注入** | 在新会话启动时将项目状态、工作流、规范索引一次性注入 AI 上下文窗口 |
| **跨平台兼容** | 支持 Claude Code、Cursor、CodeBuddy、Droid、Gemini、Qoder、Kiro、Copilot、Codex 等 10+ 平台 |
| **任务状态驱动** | 根据当前任务状态（NO ACTIVE TASK / STALE / COMPLETED / PLANNING / READY）给出不同的 Next-Action 指令 |
| **零配置启动** | AI 启动后无需询问即可知道该做什么 |

### 两个版本对比

| 特性 | `.claude/hooks/` (主版本) | `.codex/hooks/` (Codex 版) |
|------|--------------------------|---------------------------|
| 行数 | 793 | 482 |
| 注释语言 | 中文 | 英文 |
| 子智能体通知 | 无（Claude 自有机制） | 有 `SUB_AGENT_NOTICE` |
| spec_scope 过滤 | ✅ 支持 monorepo package 过滤 | ❌ 不支持 |
| legacy spec 检测 | ✅ 迁移警告 | ❌ 不支持 |
| PLANNING 子状态 | ✅ Phase 1.3（jsonl 未整理） | ❌ 简化为 NOT READY |
| 研究提醒 | ✅ 内联 WebFetch/WebSearch 限制 | ❌ 无 |
| 平台检测 | 多方法（环境变量 + 脚本路径） | 仅 cwd 推断 |

---

## 二、整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    session-start.py 架构                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  stdin (JSON)                                                    │
│      │                                                           │
│      ▼                                                           │
│  ┌─────────────────┐                                            │
│  │ 1. 环境初始化     │  UTF-8 编码 / 警告抑制 / 路径规范化        │
│  └────────┬────────┘                                            │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ 2. 跳过检查      │  TRELLIS_HOOKS=0 / NON_INTERACTIVE=1      │
│  └────────┬────────┘                                            │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ 3. 平台检测      │  Claude / Cursor / CodeBuddy / ...         │
│  └────────┬────────┘                                            │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ 4. 上下文键解析   │  resolve_context_key() → 会话身份         │
│  └────────┬────────┘                                            │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ 5. 活动任务解析   │  resolve_active_task() → 当前任务指针     │
│  └────────┬────────┘                                            │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ 6. 配置加载      │  is_monorepo / packages / spec_scope       │
│  └────────┬────────┘                                            │
│           ▼                                                      │
│  ┌─────────────────┐       ┌──────────────────────────────┐     │
│  │ 7. 上下文构建     │ ───► │ <session-context>             │     │
│  │   (StringIO)     │      │ <first-reply-notice>          │     │
│  │                  │      │ <migration-warning> (可选)     │     │
│  │                  │      │ <current-state>               │     │
│  │                  │      │ <workflow>                    │     │
│  │                  │      │ <guidelines>                  │     │
│  │                  │      │ <task-status>                 │     │
│  │                  │      │ <ready>                       │     │
│  └────────┬────────┘      └──────────────────────────────┘     │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ 8. JSON 输出     │  stdout → hook 协议格式                    │
│  └─────────────────┘                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、模块详解

### 3.1 环境初始化（第 1-96 行）

#### 3.1.1 警告抑制（第 9-10 行）
```python
import warnings
warnings.filterwarnings("ignore")
```
必须在**所有 import 之前**过滤警告，防止依赖库（如 YAML 解析器）在钩子环境中产生噪音。

#### 3.1.2 Windows UTF-8 编码（第 79-95 行）
Windows 默认编码页（cp936/cp1252）无法处理中文任务名和 PRD 片段。脚本通过以下策略强制 UTF-8：

```
              ┌──────────────┐
              │ 检测 Windows  │
              └──────┬───────┘
                     │
            ┌────────▼────────┐
            │ stream.reconfi- │  优先：Python 3.7+
            │ gure(utf-8)     │
            └──────┬──────────┘
                   │ 失败
            ┌──────▼──────────┐
            │ TextIOWrapper   │  回退：Python 3.6 兼容
            │ (detach+wrap)   │
            └─────────────────┘
```

#### 3.1.3 Windows 路径规范化（第 22-66 行）
`_normalize_windows_shell_path()` 处理 4 种 Unix→Windows 路径映射：

| 模式 | 示例输入 | 输出 |
|------|---------|------|
| 已是 Windows | `C:\Users\...` | 不变 |
| MSYS/Git-Bash | `/c/Users/...` | `C:\Users\...` |
| Cygwin | `/cygdrive/c/Users/...` | `C:\Users\...` |
| WSL 挂载 | `/mnt/c/Users/...` | `C:\Users\...` |

**为什么需要此函数**：AI 编程助手在 Windows 上通过 Git Bash 运行时，环境变量中的项目路径可能是 Unix 风格。`Path.resolve()` 会将 `/d/Work/...` 误解析为 `D:/d/Work/...`（在 D 盘创建一个错误的绝对路径），导致仓库根目录检测失败。

### 3.2 跳过检查 `should_skip_injection()`（第 122-140 行）

```python
def should_skip_injection() -> bool:
    # 显式禁用钩子
    if os.environ.get("TRELLIS_HOOKS") == "0":      return True
    if os.environ.get("TRELLIS_DISABLE_HOOKS") == "1": return True

    # 各平台的非交互式标志
    non_interactive_vars = [
        "CLAUDE_NON_INTERACTIVE",
        "QODER_NON_INTERACTIVE",
        "CODEBUDDY_NON_INTERACTIVE",
        "FACTORY_NON_INTERACTIVE",
        "CURSOR_NON_INTERACTIVE",
        "GEMINI_NON_INTERACTIVE",
        "KIRO_NON_INTERACTIVE",
        "COPILOT_NON_INTERACTIVE",
    ]
    return any(os.environ.get(var) == "1" for var in non_interactive_vars)
```

两个跳过层级：
1. **Trellis 显式禁用**：通过 `TRELLIS_HOOKS=0` 或 `TRELLIS_DISABLE_HOOKS=1` 全局关闭
2. **平台非交互模式**：当 AI 助手以批处理/后台模式运行时（如子智能体派生、CI 管道），不应注入会话上下文

### 3.3 平台检测 `_detect_platform()`（第 150-183 行）

```
检测策略（优先级从高到低）：

1. input_data 特殊字段
   └─ cursor_version 字段存在 → "cursor"

2. 平台项目目录环境变量
   ├─ CLAUDE_PROJECT_DIR    → "claude"
   ├─ CURSOR_PROJECT_DIR    → "cursor"
   ├─ CODEBUDDY_PROJECT_DIR → "codebuddy"
   ├─ FACTORY_PROJECT_DIR   → "droid"
   ├─ GEMINI_PROJECT_DIR    → "gemini"
   ├─ QODER_PROJECT_DIR     → "qoder"
   ├─ KIRO_PROJECT_DIR      → "kiro"
   └─ COPILOT_PROJECT_DIR   → "copilot"

3. 脚本路径启发式
   └─ 从 sys.argv[0] 推断（.claude/ → claude, .cursor/ → cursor, ...）

4. 回退
   └─ None（未知平台）
```

### 3.4 上下文键解析（第 186-212 行）

`_resolve_context_key()` → 调用 `.trellis/scripts/common/active_task.py` 中的 `resolve_context_key()`：

```
输入：hook_input JSON + 平台名称
          │
          ▼
┌─────────────────────┐
│ TRELLIS_CONTEXT_ID? │  环境变量显式覆盖（子进程传递）
│ 是 → 直接返回        │
└─────────┬───────────┘
          │ 否
          ▼
┌─────────────────────┐
│ 在 hook_input 中     │
│ 查找 session_id /    │
│ conversation_id /    │
│ transcript_path      │
└─────────┬───────────┘
          │ 未找到
          ▼
┌─────────────────────┐
│ 在环境变量中查找      │
│ 平台特定的 SESSION_   │
│ ID / TRANSCRIPT_PATH  │
└─────────┬───────────┘
          │ 未找到
          ▼
┌─────────────────────┐
│ Cursor shell ticket  │  ← Cursor 特有：短期票据文件
│ (仅 cursor 平台)     │
└─────────┬───────────┘
          │ 未找到
          ▼
        None
```

**持久化到 Bash 环境**：`_persist_context_key_for_bash()` 将 `TRELLIS_CONTEXT_ID` 写入 `CLAUDE_ENV_FILE`，使后续 shell 命令（如 `task.py start`）可以访问会话身份。

### 3.5 活动任务解析（第 215-225 行）

`_resolve_active_task()` → 调用 `active_task.py::resolve_active_task()`：

```
输入：repo_root + hook_input + platform
              │
              ▼
    ┌─────────────────────┐
    │ 有 context_key?      │
    │ → 读取 .runtime/     │
    │   sessions/<key>.json │
    │ → 返回 current_task   │
    └─────────┬───────────┘
              │ 无匹配
              ▼
    ┌─────────────────────┐
    │ 恰好 1 个会话文件?    │  ← "session-fallback"
    │ → 返回其 current_task │    Class-2 平台子智能体
    └─────────┬───────────┘    (codex/copilot/gemini/qoder)
              │ 0 或 ≥2
              ▼
    ActiveTask(None, "none")
```

**Class-1 vs Class-2 平台**：
- **Class-1**（Claude, Cursor, OpenCode, Kiro, CodeBuddy, Droid）：hook 直接注入上下文，session_id 可靠
- **Class-2**（Codex, Copilot, Gemini, Qoder）：子智能体不继承父会话 ID，依赖单会话回退（session-fallback）

### 3.6 任务状态检测 `_get_task_status()`（第 287-392 行）

这是脚本的核心决策逻辑，产出 5 种状态：

```
                  ┌──────────────┐
                  │ 有活动任务?    │
                  └──┬────────┬──┘
                     │ 否      │ 是
                     ▼         ▼
         ┌──────────────┐  ┌──────────────┐
         │ NO ACTIVE     │  │ 任务目录存在?  │
         │ TASK          │  └──┬────────┬──┘
         │ → brainstorm  │     │ 否      │ 是
         └──────────────┘     ▼         ▼
                    ┌──────────────┐  ┌──────────────┐
                    │ STALE POINTER │  │ task.json     │
                    │ → task finish │  │ status=?      │
                    └──────────────┘  └──┬────────┬──┘
                                        │        │
                                 completed    pending/in_progress
                                        │        │
                                        ▼        ▼
                              ┌──────────────┐  ┌──────────────────┐
                              │ COMPLETED     │  │ prd.md 存在?      │
                              │ → spec+archive│  └──┬────────┬──────┘
                              └──────────────┘     │ 否      │ 是
                                                   ▼         ▼
                                          ┌──────────────┐ ┌──────────────────┐
                                          │ PLANNING      │ │ implement.jsonl   │
                                          │ (Phase 1.1)   │ │ 已整理?           │
                                          │ → brainstorm  │ └──┬────────┬──────┘
                                          └──────────────┘    │ 否      │ 是
                                                              ▼         ▼
                                                     ┌──────────────┐ ┌──────────┐
                                                     │ PLANNING      │ │ READY    │
                                                     │ (Phase 1.3)   │ │ → Phase  │
                                                     │ → curate jsonl│ │ 2.1      │
                                                     └──────────────┘ └──────────┘
```

每种状态的 **Next-Action** 指令：

| 状态 | Next-Action |
|------|------------|
| `NO ACTIVE TASK` | 加载 `trellis-brainstorm` skill，用户描述意图后通过 `task.py create` 创建任务 |
| `STALE POINTER` | 运行 `task.py finish` 清除过期指针，询问用户下一步 |
| `COMPLETED` | 加载 `trellis-update-spec` 捕获经验，然后 `task.py archive` |
| `PLANNING` (无 PRD) | 加载 `trellis-brainstorm`，生成 prd.md；如需研究则派生 `trellis-research` |
| `PLANNING (Phase 1.3)` | 整理 `implement.jsonl` / `check.jsonl`（spec + research 文件路径） |
| `READY` | 按阶段 2.1 调度 `trellis-implement` → 2.2 调度 `trellis-check` |

### 3.7 配置加载 `_load_trellis_config()`（第 395-436 行）

从 `.trellis/scripts/common/config.py` 加载：

```python
(is_mono, packages, spec_scope, task_pkg, default_pkg)
```

| 返回值 | 类型 | 说明 |
|--------|------|------|
| `is_mono` | `bool` | 是否多仓库模式（config.yaml 中有 packages） |
| `packages` | `dict` | 包名 → 配置映射 |
| `spec_scope` | `list/str/None` | 配置的 spec 作用域过滤 |
| `task_pkg` | `str/None` | 当前任务的 package（从 task.json 读取） |
| `default_pkg` | `str/None` | 默认 package |

### 3.8 Spec 作用域解析 `_resolve_spec_scope()`（第 485-541 行）

```
spec_scope 配置值策略：

┌─────────────────────────────────────────────────────┐
│ 未配置 (None)                                        │
│   → 单仓库: 全量扫描                                  │
│   → 多仓库: 全量扫描所有 package                       │
├─────────────────────────────────────────────────────┤
│ "active_task"                                       │
│   → 使用 task.json 中的 package                       │
│   → 回退到 default_package                           │
│   → 回退到全量扫描                                    │
├─────────────────────────────────────────────────────┤
│ ["pkg_a", "pkg_b"]                                  │
│   → 仅包含列表中的有效 package                         │
│   → 如果任务 package 不在范围内，打印警告               │
│   → 所有条目无效时：回退链（task → default → full）     │
└─────────────────────────────────────────────────────┘
```

### 3.9 Workflow 指南构建 `_build_workflow_overview()`（第 585-629 行）

从 `workflow.md` 提取并压缩工作流指南（~9 KB 总预算）：

```
workflow.md 结构                  注入策略
═══════════════                   ════════
## Table of Contents      ──►  完整内联（章节导航）
## Core Principles         ──►  跳过（AI 按需 Read）
## Trellis System          ──►  跳过（参考命令）
## Phase Index             ──►  提取（规则 + skill 路由表）
  [workflow-state:...]     ──►  剥离（UserPromptSubmit hook 消费）
## Phase 1                 ──►  提取（步骤级详细指南）
## Phase 2                 ──►  提取
## Phase 3                 ──►  提取
## Customizing Trellis      ──►  停止提取（fork 用户文档）
```

**面包屑标签剥离**：`_strip_breadcrumb_tag_blocks()` 移除 `[workflow-state:STATUS]...[/workflow-state:STATUS]` 块——这些块由 `inject-workflow-state.py`（UserPromptSubmit hook）在每轮对话中动态注入，在 SessionStart 中内联会造成重复。

### 3.10 Guidelines 部分（第 699-764 行）

```
<guidelines> 内容策略：

┌──────────────────────────────────────────┐
│ guides/ index.md                         │
│   → 始终内联（跨 package 思考指南，内容少）  │
├──────────────────────────────────────────┤
│ spec/<pkg>/ index.md (扁平)               │
│   → 仅列路径（主智能体按需 Read）            │
├──────────────────────────────────────────┤
│ spec/<pkg>/<layer>/ index.md (嵌套)       │
│   → 应用 spec_scope 过滤                   │
│   → 仅列路径                               │
├──────────────────────────────────────────┤
│ 子智能体使用说明                            │
│   → implement.jsonl / check.jsonl 自动注入 │
│   → 子智能体自我豁免规则                     │
└──────────────────────────────────────────┘
```

### 3.11 JSON 输出格式（第 777-788 行）

脚本输出两种格式以兼容不同平台：

```python
result = {
    # Claude Code / Qoder / CodeBuddy / Droid / Gemini / Copilot
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": context_text,
    },
    # Cursor sessionStart 格式（顶层 snake_case）
    "additional_context": context_text,
}
```

---

## 四、关键调用链

```
main()
 ├── should_skip_injection()                           [跳过? → exit(0)]
 ├── json.loads(sys.stdin.read())                      [读取 hook_input]
 ├── Path(project_dir_env_var).resolve()               [项目目录定位]
 ├── _resolve_context_key(trellis_dir, hook_input)     [会话身份]
 │   └── active_task.resolve_context_key()
 │       ├── TRELLIS_CONTEXT_ID 环境变量
 │       ├── hook_input 中的 session_id/conversation_id
 │       ├── 环境变量 (CLAUDE_SESSION_ID, ...)
 │       └── Cursor shell ticket 文件
 ├── _persist_context_key_for_bash(context_key)        [写入 CLAUDE_ENV_FILE]
 ├── _load_trellis_config(trellis_dir, hook_input)     [monorepo/packages/scope]
 │   └── config.is_monorepo() / get_packages() / get_spec_scope()
 ├── _resolve_spec_scope(is_mono, packages, ...)       [spec 过滤集合]
 ├── _check_legacy_spec(trellis_dir, is_mono, packages) [迁移警告]
 │
 ├── 构建输出 (StringIO):
 │   ├── <session-context>                             [会话说明]
 │   ├── FIRST_REPLY_NOTICE                            [首次回复指令]
 │   ├── <migration-warning> (可选)                    [旧版 spec 迁移]
 │   ├── <current-state>
 │   │   └── run_script(get_context.py, context_key)   [git状态/任务/日志]
 │   ├── <workflow>
 │   │   └── _build_workflow_overview(workflow.md)     [工作流注入]
 │   │       ├── 章节索引 (所有 ## 标题)
 │   │       ├── _extract_range(Phase Index → Customizing)
 │   │       └── _strip_breadcrumb_tag_blocks()
 │   ├── <guidelines>
 │   │   ├── guides/index.md (内联)
 │   │   ├── spec/<pkg>/index.md 列表
 │   │   └── spec_scope 过滤
 │   ├── <task-status>
 │   │   └── _get_task_status()                        [状态机决策]
 │   │       ├── _resolve_active_task()
 │   │       ├── task_dir / task.json / prd.md 检查
 │   │       └── _has_curated_jsonl_entry()
 │   └── <ready>                                       [启动就绪]
 │
 └── print(json.dumps(result))                         [stdout UTF-8]
```

---

## 五、数据流图

```
┌──────────────────────────────────────────────────────────────────────┐
│                        外部系统                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ 环境变量  │  │ stdin    │  │ 文件系统  │  │ 子进程    │            │
│  │ (平台ID) │  │ (hook    │  │ (.trellis │  │ (get_     │            │
│  │          │  │  input)  │  │  /tasks/) │  │  context) │            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
│       │             │             │             │                   │
│       ▼             ▼             ▼             ▼                   │
│  ┌────────────────────────────────────────────────────┐             │
│  │              session-start.py                       │             │
│  │                                                     │             │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │             │
│  │  │ 平台检测     │  │ 上下文键     │  │ 活动任务     │ │             │
│  │  │ _detect_     │  │ _resolve_   │  │ _resolve_   │ │             │
│  │  │ platform()   │  │ context_key │  │ active_task │ │             │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │             │
│  │         │                │                │         │             │
│  │         └────────────────┼────────────────┘         │             │
│  │                          │                          │             │
│  │         ┌────────────────┼────────────────┐         │             │
│  │         │          配置系统                │         │             │
│  │         │  ┌─────────────┐  ┌───────────┐ │         │             │
│  │         │  │ config.yaml │  │ spec_scope│ │         │             │
│  │         │  │ → packages  │  │ 过滤      │ │         │             │
│  │         │  └─────────────┘  └───────────┘ │         │             │
│  │         └────────────────┬────────────────┘         │             │
│  │                          │                          │             │
│  │         ┌────────────────┼────────────────┐         │             │
│  │         │          状态机                 │         │             │
│  │         │  NO_TASK → STALE → COMPLETED    │         │             │
│  │         │  → PLANNING → PLANNING(1.3)     │         │             │
│  │         │  → READY                        │         │             │
│  │         └────────────────┬────────────────┘         │             │
│  │                          │                          │             │
│  │         ┌────────────────┼────────────────┐         │             │
│  │         │          输出组装                │         │             │
│  │         │  StringIO → XML 标签块           │         │             │
│  │         │  → JSON serialization            │         │             │
│  │         └────────────────┬────────────────┘         │             │
│  └──────────────────────────┼──────────────────────────┘             │
│                             │                                        │
│                             ▼                                        │
│                    ┌────────────────┐                                │
│                    │ stdout (JSON)  │                                │
│                    │ → AI 上下文窗口 │                                │
│                    └────────────────┘                                │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 六、关键技术决策

### 6.1 为什么需要 `_normalize_windows_shell_path()`

**问题**：Windows 上的 Git Bash 将路径报告为 `/d/Work/mygame`，但 `Path.resolve()` 将其解释为"D 盘上的相对路径 `/d/Work/mygame`"→ 变成 `D:\d\Work\mygame`（错误）。

**解决**：在所有 `Path()` 调用前规范化路径，识别 3 种 Unix-on-Windows 模式。

### 6.2 为什么有两个跳过层级

- `TRELLIS_HOOKS=0`：用户/CI 的显式选择
- `NON_INTERACTIVE=1`：平台自声明——子智能体、批处理模式不应注入 9KB+ 上下文

### 6.3 为什么 breadcrumb 标签需要剥离

`[workflow-state:...]` 标签是**动态的**——由 `inject-workflow-state.py` 在每轮 `UserPromptSubmit` 时注入，反映当前状态（不同轮次可能不同）。SessionStart 中的 workflow.md 是**静态快照**——重复注入会造成上下文膨胀。

### 6.4 为什么需要 platform 参数透传

`_detect_platform()` 和后续函数都接受可选的 `platform` 参数。这是为 **Class-2 平台子智能体**设计的——它们不继承父会话的 hook_input，但父智能体在派生提示中可以显式指定 `platform`，使任务定位正确。

### 6.5 spec_scope 逐级回退链

```
配置的 spec_scope 列表
  → 所有条目无效? → task_pkg (from task.json)
    → task_pkg 无效? → default_pkg (from config.yaml)
      → default_pkg 无效? → 全量扫描 (None)
```

这种多级回退确保 spec 注入在任何配置错误下都能降级运行，而非完全失败。

---

## 七、与 `.codex/hooks/session-start.py` 的差异

| 差异点 | Claude 版 | Codex 版 |
|--------|----------|----------|
| **子智能体通知** | 无（Claude 的 Agent 工具自行处理） | `SUB_AGENT_NOTICE`：指示子智能体忽略 Trellis 工作流 |
| **任务状态粒度** | 6 种状态（含 Phase 1.3 子状态） | 4 种（合并 PLANNING 子状态为 NOT READY） |
| **spec_scope 过滤** | 完整实现（monorepo package 过滤） | 不支持（全量扫描） |
| **旧版 spec 迁移** | `_check_legacy_spec()` 检测并警告 | 不支持 |
| **配置加载** | `_load_trellis_config()` 返回 5 元组 | 简化（不加载 config） |
| **Next-Action 详细度** | 中文，包含 skill 名和完整命令 | 英文，简化 |
| **研究提醒** | 限制内联 WebFetch/WebSearch > 10 次 | 无 |
| **用户覆盖短语** | 列出中文覆盖短语 | 列出中文覆盖短语 |
| **输出格式** | `suppressOutput` + `additional_context` | `hookSpecificOutput` + `additional_context` |

---

## 八、错误处理策略

| 场景 | 处理策略 |
|------|---------|
| stdin 不是有效 JSON | 回退到空 dict `{}` |
| stdin 不是 dict | 回退到空 dict `{}` |
| 平台检测失败 | 返回 `None`，后续使用 cwd 推断 |
| 上下文键解析失败 | 回退到 `None`，`_persist_context_key_for_bash` 跳过 |
| config 加载异常 | 回退到 `(False, {}, None, None, None)` |
| workflow.md 不存在 | 返回 `"未找到 workflow.md"` |
| get_context.py 超时 | 5 秒超时 → 返回 `"无可用上下文"` |
| 子进程执行失败 | 返回 `"无可用上下文"` |
| spec 目录不存在 | 跳过 spec 索引列表 |
| task.json 解析失败 | 静默回退到空 dict |
| prd.md / jsonl 不存在 | 返回对应的 PLANNING / NOT READY 状态 |

**核心原则**：任何错误都不应阻止上下文注入——降级运行比完全失败好。

---

## 九、上下文预算

SessionStart 注入的总上下文约：

| 块 | 大约大小 | 说明 |
|----|---------|------|
| `<session-context>` | ~150 B | 固定模板 |
| `<first-reply-notice>` | ~350 B | 固定模板 |
| `<current-state>` | ~1.5 KB | git 状态 + 任务列表 + 日志 |
| `<workflow>` | ~7 KB | Phase Index + Phase 1/2/3 |
| `<guidelines>` | ~1.5 KB | guides 内联 + spec 路径列表 |
| `<task-status>` | ~1 KB | 状态 + Next-Action |
| `<ready>` | ~250 B | 固定模板 |
| **总计** | **~9-12 KB** | |

---

## 十、相关文件索引

| 文件 | 角色 |
|------|------|
| `.claude/hooks/session-start.py` | 本文分析对象（主版本） |
| `.codex/hooks/session-start.py` | Codex 平台变体 |
| `.trellis/scripts/common/active_task.py` | 活动任务解析 + 会话运行时管理 |
| `.trellis/scripts/common/config.py` | config.yaml 解析（monorepo/packages/spec_scope） |
| `.trellis/scripts/get_context.py` | Git 状态 + 任务上下文生成 |
| `.trellis/scripts/common/git_context.py` | get_context.py 的实际实现 |
| `.trellis/scripts/common/paths.py` | 仓库根目录发现 |
| `.trellis/workflow.md` | 完整工作流文档（Phase Index + Phase 1/2/3） |
| `.trellis/spec/guides/index.md` | 跨 package 思维指南索引 |
| `inject-workflow-state.py` | UserPromptSubmit hook（消费 breadcrumb 标签） |
| `.trellis/.runtime/sessions/*.json` | 会话运行时文件 |
| `.trellis/config.yaml` | 项目配置 |
