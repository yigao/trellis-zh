# inject-workflow-state.py 详细分析文档

> 分析对象：`.claude/hooks/inject-workflow-state.py`（主版本，382 行）
> 对比参考：`.codex/hooks/inject-workflow-state.py`（Codex 变体，388 行）
> 关联文档：`session-start-analysis.md`（SessionStart 钩子分析）

---

## 一、概述

`inject-workflow-state.py` 是 Trellis 项目管理系统的 **UserPromptSubmit 钩子（Hook）**（在 Gemini 平台上对应 `BeforeAgent` 事件）。每当用户在 AI 编程助手中输入提示词时，宿主 CLI 调用此脚本，脚本输出一个简短的 `<workflow-state>` XML 块，告知 AI **当前活动任务及其预期工作流步骤**。

与 `session-start.py`（SessionStart 钩子，仅在会话启动时执行一次）不同，本脚本是**每轮**（per-turn）执行的——用户每次发送消息都会触发，确保 AI 始终感知最新状态。

### 核心目标

| 目标 | 说明 |
|------|------|
| **每轮状态提醒** | 每次用户输入时，向 AI 注入当前任务 ID、状态和预期下一步操作 |
| **轻量化** | 输出仅 300-800 字节（对比 SessionStart 的 9-12 KB），不显著占用上下文窗口 |
| **唯一真相来源** | 面包屑文本完全从 `workflow.md` 的 `[workflow-state:STATUS]` 标签块解析——无硬编码回退字典 |
| **跨平台兼容** | 支持 Claude Code、Cursor、Codex、Qoder、CodeBuddy、Droid、Gemini、Copilot 等 10+ 平台 |
| **Codex 特殊处理** | 为 Codex 平台附加子智能体通知、引导通知和派发模式横幅 |

### 与 session-start.py 的关键区别

| 特性 | session-start.py | inject-workflow-state.py |
|------|-----------------|--------------------------|
| 触发时机 | 会话启动（一次性） | 每次用户输入（每轮） |
| 上下文大小 | ~9-12 KB | ~300-800 B |
| 注入内容 | 完整项目上下文（git/任务/工作流/spec） | 仅任务状态 + 工作流步骤 |
| 输出事件名 | `SessionStart` | `UserPromptSubmit`（Gemini: `BeforeAgent`） |
| 状态机 | 内置（6 种状态判定 + Next-Action） | 无状态机——从 workflow.md 被动读取 |
| 依赖模块 | config.py, active_task.py, git_context.py | active_task.py, trellis_config.py |
| Codex 额外内容 | 无（通过 platform 参数支持） | 子智能体通知 + 引导通知 + 模式横幅 |

---

## 二、整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                 inject-workflow-state.py 架构                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  stdin (JSON)                                                    │
│      │                                                           │
│      ▼                                                           │
│  ┌─────────────────┐                                            │
│  │ 1. 环境初始化     │  Windows UTF-8 编码 (stdin/stdout/stderr)   │
│  └────────┬────────┘                                            │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ 2. 跳过检查      │  TRELLIS_HOOKS=0 / TRELLIS_DISABLE_HOOKS=1 │
│  └────────┬────────┘                                            │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ 3. Trellis根目录  │  find_trellis_root() — 向上遍历查找       │
│  └────────┬────────┘                                            │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ 4. 平台检测      │  _detect_platform() — 9种策略              │
│  └────────┬────────┘                                            │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ 5. 加载面包屑模板 │  load_breadcrumbs() — 解析 workflow.md     │
│  └────────┬────────┘                                            │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ 6. 读取配置      │  _read_trellis_config() — config.yaml      │
│  └────────┬────────┘                                            │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ 7. 活动任务解析   │  get_active_task() → (task_id, status, src)│
│  └────────┬────────┘                                            │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ 8. 面包屑键解析   │  resolve_breadcrumb_key() — Codex inline   │
│  └────────┬────────┘                                            │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ 9. 构建面包屑     │  build_breadcrumb() → <workflow-state>     │
│  └────────┬────────┘                                            │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ 10. Codex 组装   │  仅 Codex: 子智能体通知 + 引导 + 模式横幅  │
│  └────────┬────────┘                                            │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ 11. JSON 输出    │  hookSpecificOutput → stdout               │
│  └─────────────────┘                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、模块详解

### 3.1 环境初始化（第 41-56 行）

Windows 默认编码页（cp936/cp1252）无法处理中文任务名和 PRD 片段。脚本在**所有逻辑之前**强制 stdin/stdout/stderr 使用 UTF-8：

```
              ┌──────────────┐
              │ 检测 Windows  │
              └──────┬───────┘
                     │
            ┌────────▼────────┐
            │ stream.reconfi- │  优先：Python 3.7+
            │ gure(utf-8)     │  (TextIOWrapper.reconfigure)
            └──────┬──────────┘
                   │ 失败
            ┌──────▼──────────┐
            │ TextIOWrapper   │  回退：Python 3.6 兼容
            │ (detach+wrap)   │  (BinaryIO.detach → TextIOWrapper)
            └─────────────────┘
```

**为什么需要单独处理每个流**：不依赖宿主 CLI 的命令行接线方式（`python -X utf8` 行为因平台而异），而是按流逐一确保 UTF-8。

### 3.2 Codex 子智能体通知（第 60-74 行）

```python
CODEX_SUB_AGENT_NOTICE = """<sub-agent-notice>
子智能体通知 — 如果通过 spawn_agent 派生，请先阅读

如果你的父会话通过 spawn_agent 派生你，并附带了显式的任务消息...
- 严格按照父消息的内容执行，然后返回。
- 忽略此通知下方的所有 Trellis 工作流指引。
- 不要调用 task.py start、task.py add-context 或 task.py archive。
...
</sub-agent-notice>"""
```

**为什么 Codex 需要此通知**：Codex 的 `spawn_agent` 机制会使子智能体也运行 hook，从而看到工作流指引。但子智能体的职责是执行父智能体的具体指令，不应按照 Trellis 工作流自主行动。此通知指示子智能体忽略下方的 Trellis 工作流，直接执行父消息。

### 3.3 Codex 无任务引导通知（第 83-97 行）

```python
CODEX_NO_TASK_BOOTSTRAP_NOTICE = """<trellis-bootstrap>
你正在 Trellis 管理的 Codex 会话中运行，当前没有活动任务。
如果你在本会话中尚未加载 Trellis 上下文，请先读取一次 `trellis-start` skill：
  $trellis-start
...
</trellis-bootstrap>"""
```

**设计理念**：替代重量级的 SessionStart 上下文注入（9.5 KB）。当没有活动任务时（`status == "no_task"`），此轻量提醒持续显示——文本量小，AI 读一次后不会再重复读取。一旦创建任务，面包屑状态翻转，此通知自动消失。

### 3.4 Trellis 根目录发现 `find_trellis_root()`（第 104-115 行）

```
输入: start (Path) — 当前工作目录
         │
         ▼
┌─────────────────────┐
│ cur = start.resolve()│
│ 向上遍历父目录        │
│ while cur != parent  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ (cur/".trellis")    │  每层检查 .trellis/ 目录
│ .is_dir()?          │
└─────────┬───────────┘
     │ 是          │ 否 → 继续向上
     ▼             ▼
  返回 cur     cur = cur.parent
              （直到根目录）
                  │
                  ▼
            返回 None
            （非 Trellis 项目）
```

**为什么需要向上遍历**：处理 CWD 偏移——用户可能在子目录中启动 AI 助手、monorepo 的 package 子目录等场景。

### 3.5 平台检测 `_detect_platform()`（第 122-155 行）

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
   └─ 从 sys.argv[0] 推断（.claude/ → claude, .cursor/ → cursor,
      .codex/ → codex, .gemini/ → gemini, .qoder/ → qoder,
      .codebuddy/ → codebuddy, .factory/ → droid, .kiro/ → kiro）

4. 回退
   └─ None（未知平台）
```

### 3.6 活动任务解析 `get_active_task()`（第 167-191 行）

这是整个脚本最核心的函数，通过调用 `active_task.py::resolve_active_task()` 获取当前任务指针：

```
get_active_task(root, input_data)
         │
         ▼
┌────────────────────────────┐
│ _resolve_active_task()     │  调用 .trellis/scripts/common/
│   → active_task.py         │  active_task.py 中的会话感知
│   → 参数: platform=        │  解析器
│     _detect_platform()     │
└─────────┬──────────────────┘
          │
          ▼
┌────────────────────────────┐
│ active.task_path 为 None?  │
│   → return None            │  无活动任务
└─────────┬──────────────────┘
          │ 有值
          ▼
┌────────────────────────────┐
│ task_dir 非绝对路径?        │
│   → task_dir = root / path │  相对于 Trellis 根目录解析
└─────────┬──────────────────┘
          │
          ▼
┌────────────────────────────┐
│ active.stale?              │  任务目录已被删除/移动
│   → return (dir_name,      │  标记为 stale_{source_type}
│      stale_{source}, src)  │
└─────────┬──────────────────┘
          │ 未过期
          ▼
┌────────────────────────────┐
│ task.json 存在?            │
│   → 读取并解析 JSON        │
│   → 返回 (task_id, status, │
│           source)          │
└─────────┬──────────────────┘
          │ 不存在/解析失败
          ▼
       return None
```

**返回值**: `Optional[tuple[str, str, str]]` — `(task_id, status, source)`
- `task_id`: 任务标识符（来自 task.json 的 `id` 字段或目录名）
- `status`: 任务状态（`planning` / `in_progress` / `completed` / `stale_*`）
- `source`: 任务来源（`session` / `session-fallback`）

**`stale` 状态的含义**：`active_task.py` 中的 `resolve_active_task()` 会验证任务目录是否真实存在。如果会话文件记录了 `current_task` 指向 `tasks/some-task/`，但该目录已被删除或移动，则 `active.stale = True`——此时返回状态 `stale_<source_type>`。

### 3.7 面包屑模板加载 `load_breadcrumbs()`（第 205-227 行）

从 `workflow.md` 解析 `[workflow-state:STATUS]...[/workflow-state:STATUS]` 标签块：

```
_TAG_RE 正则模式:
  \[workflow-state:([A-Za-z0-9_-]+)\]\s*\n
  (.*?)
  \n\s*\[/workflow-state:\1\]

支持 STATUS 值: 字母、数字、下划线、连字符
  → "in_progress", "in-review", "blocked-by-team" 均可

workflow.md 结构片段:
  [workflow-state:in_progress]
  **流程**：trellis-implement → trellis-check → ...
  [/workflow-state:in_progress]

返回值: {status: body_text}
  → 空 dict 表示 workflow.md 缺失或不可读
```

**设计原则——无回退字典**：如果 workflow.md 缺失或标签不存在，`build_breadcrumb()` 会回退为通用行 `"请参阅 workflow.md 了解当前步骤。"`。这样用户能看到损坏的状态并修复 workflow.md，而不是 hook 静默掩盖问题。

### 3.8 配置加载 `_read_trellis_config()`（第 230-246 行）

通过 `trellis_config.py` 助手加载 `.trellis/config.yaml`：

```
_read_trellis_config(root)
         │
         ▼
┌────────────────────────────┐
│ 扩展 sys.path              │  钩子脚本位于 scripts 树之外
│ → root/.trellis/scripts    │  需要先扩展 sys.path
└─────────┬──────────────────┘
          │
          ▼
┌────────────────────────────┐
│ from common.trellis_config │  按需导入（仅导入安全——轻量
│ import read_trellis_config │  级 config 读取器）
└─────────┬──────────────────┘
          │
     ┌────┴────┐
     │ 成功     │ 失败
     ▼         ▼
  返回dict   返回 {}
```

### 3.9 Codex 模式横幅 `_codex_mode_banner()`（第 249-265 行）

为 Codex 平台生成 `<codex-mode>` 横幅：

```
从 .trellis/config.yaml 读取 codex.dispatch_mode
         │
    ┌────┴────┐
    │ "inline" │ "sub-agent" │ 缺失/无效
    ▼          ▼             ▼
  inline    sub-agent      inline (默认)
```

**为什么默认 `inline`**：Codex 子智能体以 `fork_turns="none"` 隔离运行，无法继承父会话的任务上下文。`inline` 模式告诉 AI 在主会话中直接编辑代码；`sub-agent` 模式告诉 AI 派发子智能体。

### 3.10 面包屑键解析 `resolve_breadcrumb_key()`（第 268-289 行）

基于 Codex dispatch_mode 选择面包屑标签键：

```
resolve_breadcrumb_key(status, platform, config)

platform == "codex"?
  │
  ├─ 是 → dispatch_mode?
  │        ├─ "inline" (默认) → f"{status}-inline"
  │        └─ "sub-agent"     → status (原样)
  │
  └─ 否 → status (原样，非 Codex 平台)
```

**为什么需要 `-inline` 后缀**：workflow.md 中为内联模式定义了并行标签块。例如：
- `[workflow-state:in_progress]` — 子智能体派发模式的工作流
- `[workflow-state:in_progress-inline]` — 内联模式的工作流（主会话直接编辑）

此函数根据 `dispatch_mode` 选择合适的标签键，实现了**同一状态、不同工作流**的动态切换。

### 3.11 面包屑构建 `build_breadcrumb()`（第 292-315 行）

构建完整的 `<workflow-state>` XML 块：

```
build_breadcrumb(task_id, status, templates, source, breadcrumb_key)

1. 查找模板正文:
   lookup_key = breadcrumb_key or status
   → templates.get(lookup_key)    优先：带后缀的键
   → templates.get(status)         回退：原始状态键
   → "请参阅 workflow.md ..."     最终回退：通用行

2. 构建标题:
   task_id is None → f"状态: {status}"
   task_id 存在    → f"任务: {task_id} ({status})"
   source 存在     → 追加 "\n来源: {source}"

3. 组装:
   <workflow-state>
   {header}
   {body}
   </workflow-state>
```

**输出示例**（有任务）：
```xml
<workflow-state>
任务: trellis-python (in_progress)
来源: session-fallback:claude_d77f67d7-b3a3-4e90-baf3-cf3c89491de9
**流程**：trellis-implement → trellis-check → trellis-update-spec → 提交（阶段 3.4）→ `/trellis:finish-work`。
...
</workflow-state>
```

**输出示例**（无任务）：
```xml
<workflow-state>
状态: no_task
- 无活跃 task。
**A 直接回答** — 纯粹的问答...
**B 先建任务** — ...
**C 内联修改** — ...
</workflow-state>
```

### 3.12 入口 `main()`（第 322-381 行）

完整的执行流程图见下一节。关键步骤：

```
main()
 ├── 1. 跳过检查: TRELLIS_HOOKS=0 或 TRELLIS_DISABLE_HOOKS=1 → exit(0)
 ├── 2. 读取 stdin JSON（失败 → 空 dict）
 ├── 3. 确定 CWD（stdin.cwd → os.getcwd()）
 ├── 4. find_trellis_root(cwd) → None 则 exit(0)（非 Trellis 项目）
 ├── 5. load_breadcrumbs(root) → templates dict
 ├── 6. _detect_platform(data) → platform
 ├── 7. _read_trellis_config(root) → config dict
 ├── 8. get_active_task(root, data)
 │     ├── None → resolve_breadcrumb_key("no_task", ...)
 │     │          → build_breadcrumb(None, "no_task", ...)
 │     └── 有值 → resolve_breadcrumb_key(status, ...)
 │                → build_breadcrumb(task_id, status, ..., source, ...)
 ├── 9. platform == "codex" → 组装额外内容
 │     ├── CODEX_SUB_AGENT_NOTICE
 │     ├── CODEX_NO_TASK_BOOTSTRAP_NOTICE (仅 task=None)
 │     ├── _codex_mode_banner(config)
 │     └── breadcrumb（最后，AI 读到此）
 ├── 10. 确定 hookEventName
 │      ├── gemini → "BeforeAgent"
 │      └── 其他   → "UserPromptSubmit"
 └── 11. 输出 JSON → stdout
```

### 3.13 Gemini 平台特殊处理（第 366-368 行）

```python
hook_event_name = (
    "BeforeAgent" if platform == "gemini" else "UserPromptSubmit"
)
```

**为什么**：Gemini CLI 0.40.x 将其每轮事件重命名为 `BeforeAgent`，其 schema 验证器会拒绝旧的 `UserPromptSubmit` 名称。其他所有平台（Claude、Cursor、Qoder、CodeBuddy、Droid、Codex、Copilot）接受原始的 Claude 风格命名。

---

## 四、关键调用链

```
main()
 ├── json.load(sys.stdin)                                 [读取 hook_input]
 ├── find_trellis_root(cwd)                               [Trellis 根目录]
 │   └── 向上遍历，查找 .trellis/ 目录
 ├── load_breadcrumbs(root)                               [解析 workflow.md]
 │   └── _TAG_RE.finditer(content)                        [正则匹配标签块]
 ├── _detect_platform(data)                               [平台检测]
 │   ├── input_data.cursor_version?
 │   ├── 环境变量 (CLAUDE_PROJECT_DIR, ...)?
 │   └── sys.argv[0] 路径启发式?
 ├── _read_trellis_config(root)                           [配置加载]
 │   └── common.trellis_config.read_trellis_config()
 ├── get_active_task(root, data)                          [活动任务]
 │   └── _resolve_active_task(root, data, platform=...)
 │       └── common.active_task.resolve_active_task()
 │           ├── context_key → .runtime/sessions/<key>.json
 │           ├── 会话回退（恰好1个session文件）
 │           └── task_dir/task.json 解析
 ├── resolve_breadcrumb_key(status, platform, config)     [键选择]
 │   └── Codex inline → "{status}-inline" else status
 └── build_breadcrumb(task_id, status, templates, ...)    [组装]
     ├── templates.get(lookup_key) → body
     └── f"<workflow-state>\n{header}\n{body}\n</workflow-state>"
```

---

## 五、数据流图

```
┌──────────────────────────────────────────────────────────────────────┐
│                        外部系统                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                          │
│  │ 环境变量  │  │ stdin    │  │ 文件系统  │                          │
│  │ (平台ID, │  │ (hook    │  │ (.trellis │                          │
│  │  disable) │  │  input)  │  │  /tasks/) │                          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                          │
│       │             │             │                                  │
│       ▼             ▼             ▼                                  │
│  ┌────────────────────────────────────────────────────┐             │
│  │              inject-workflow-state.py               │             │
│  │                                                     │             │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │             │
│  │  │ 跳过检查     │  │ 平台检测     │  │ 根目录发现   │ │             │
│  │  │ TRELLIS_    │  │ _detect_    │  │ find_trellis │ │             │
│  │  │ HOOKS /     │  │ platform()  │  │ _root()      │ │             │
│  │  │ DISABLE      │  └──────┬──────┘  └──────┬──────┘ │             │
│  │  └─────────────┘         │                │         │             │
│  │                          │                │         │             │
│  │         ┌────────────────┼────────────────┘         │             │
│  │         │          核心模块                         │             │
│  │         │  ┌─────────────────────────────────┐     │             │
│  │         │  │ get_active_task()               │     │             │
│  │         │  │   → active_task.py              │     │             │
│  │         │  │   → (task_id, status, source)   │     │             │
│  │         │  └───────────────┬─────────────────┘     │             │
│  │         │                  │                       │             │
│  │         │  ┌───────────────▼─────────────────┐     │             │
│  │         │  │ load_breadcrumbs()              │     │             │
│  │         │  │   → workflow.md                 │     │             │
│  │         │  │   → {status: body_text}         │     │             │
│  │         │  └───────────────┬─────────────────┘     │             │
│  │         │                  │                       │             │
│  │         │  ┌───────────────▼─────────────────┐     │             │
│  │         │  │ resolve_breadcrumb_key()        │     │             │
│  │         │  │   → Codex: status-inline        │     │             │
│  │         │  │   → 其他: status                │     │             │
│  │         │  └───────────────┬─────────────────┘     │             │
│  │         │                  │                       │             │
│  │         │  ┌───────────────▼─────────────────┐     │             │
│  │         │  │ build_breadcrumb()              │     │             │
│  │         │  │   → 标题: 任务/状态 + 来源       │     │             │
│  │         │  │   → 正文: 模板 or 通用回退      │     │             │
│  │         │  └───────────────┬─────────────────┘     │             │
│  │         │                  │                       │             │
│  │         │  ┌───────────────▼─────────────────┐     │             │
│  │         │  │ Codex 特殊组装 (仅 codex)        │     │             │
│  │         │  │   → SUB_AGENT_NOTICE            │     │             │
│  │         │  │   → NO_TASK_BOOTSTRAP_NOTICE    │     │             │
│  │         │  │   → codex-mode banner           │     │             │
│  │         │  └───────────────┬─────────────────┘     │             │
│  │         └──────────────────┼───────────────────────┘             │
│  │                            │                                     │
│  │         ┌──────────────────▼───────────────────┐                 │
│  │         │ JSON 输出                             │                 │
│  │         │  hookEventName: UserPromptSubmit /    │                 │
│  │         │                 BeforeAgent (gemini)  │                 │
│  │         │  additionalContext: <workflow-state>  │                 │
│  │         └──────────────────┬───────────────────┘                 │
│  └────────────────────────────┼─────────────────────────────────────┘
│                               │                                      │
│                               ▼                                      │
│                      ┌────────────────┐                              │
│                      │ stdout (JSON)  │                              │
│                      │ → AI 上下文窗口 │                              │
│                      │ (每轮注入)      │                              │
│                      └────────────────┘                              │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 六、关键技术决策

### 6.1 为什么 workflow.md 是唯一真相来源

`load_breadcrumbs()` 中没有任何硬编码的回退字典。当 workflow.md 缺失或标签不存在时，`build_breadcrumb()` 回退为通用的 `"请参阅 workflow.md 了解当前步骤。"` 行。

**设计理由**：
- 避免双重维护——硬编码字典和 workflow.md 会逐渐偏离
- 损坏状态可见——用户看到通用行后知道需要修复 workflow.md
- 标签修改即时生效——编辑 workflow.md 后重启会话即可（无需修改脚本）

### 6.2 为什么需要 Codex 的 `-inline` 后缀机制

Codex 有两种派发模式：
- **inline**（默认）：主会话直接编辑代码，不派发子智能体
- **sub-agent**：主会话派发 `trellis-implement` / `trellis-check` 子智能体

同一种任务状态（如 `in_progress`）在不同模式下有完全不同的工作流：
- `in_progress`：派发子智能体 → 检查 → 更新 spec → 提交
- `in_progress-inline`：主会话加载 `trellis-before-dev` → 直接编辑 → 加载 `trellis-check` → 提交

`resolve_breadcrumb_key()` 通过 `{status}-inline` 键名切换，使同一种任务状态可以有两个不同的面包屑模板。

### 6.3 为什么 Codex 需要额外的引导通知

Codex 没有 SessionStart hook（无法在会话启动时注入完整上下文）。替代方案是：
- 在每轮的 `UserPromptSubmit` 输出中附加 `<trellis-bootstrap>` 通知
- 该通知仅在无活动任务时显示（`task is None`）
- AI 读取一次 `trellis-start` skill 后即可获得完整上下文

这避免了在每轮中都注入 9 KB 的 SessionStart 上下文（节省大量 token）。

### 6.4 为什么 get_active_task 返回 `stale_*` 状态

当会话文件记录了 `current_task` 但任务目录已被删除或移动时（`active.stale = True`），函数返回 `stale_{source_type}` 而非 `None`。

**设计理由**：stale 指针需要特殊的处理指令（运行 `task.py finish` 清除），与"完全没有任务"（需要 `task.py create` 创建）是不同的 UI 路径。

### 6.5 为什么 Gemini 需要 "BeforeAgent" 事件名

Gemini CLI 0.40.x 对其 hook 协议进行了重大更改：
- 旧版本：接受 `UserPromptSubmit`（与 Claude Code 兼容）
- 0.40.x+：重命名为 `BeforeAgent`，schema 验证器拒绝旧名称

`_detect_platform()` 检测到 Gemini 后，`main()` 自动选择 `"BeforeAgent"`，确保兼容新旧版本。

### 6.6 为什么需要 `TRELLIS_DISABLE_HOOKS` 这个备选变量名

```python
if os.environ.get("TRELLIS_HOOKS") == "0" or os.environ.get("TRELLIS_DISABLE_HOOKS") == "1":
    return 0
```

两个禁用变量：
- `TRELLIS_HOOKS=0` — 传统命名（0 表示关闭）
- `TRELLIS_DISABLE_HOOKS=1` — 更语义化的命名（1 表示禁用）

支持两种命名风格是为了兼容不同用户习惯和 CI 配置。注意一个用 `0` 表示禁用，另一个用 `1` 表示禁用——这是设计上的不一致，但保留了向后兼容。

### 6.7 静默退出 0 的场景

| 场景 | 原因 |
|------|------|
| `TRELLIS_HOOKS=0` 或 `TRELLIS_DISABLE_HOOKS=1` | 用户/CI 显式禁用 |
| 未找到 `.trellis/` 目录 | 非 Trellis 项目，不应注入 |
| `task.json` 格式错误或缺少 status | 损坏的任务数据，静默跳过 |

所有静默退出都是 `exit(0)`（成功），因为 hook 失败不应阻止 AI 助手正常运行。

---

## 七、两个版本对比

`.claude/hooks/inject-workflow-state.py`（382 行）和 `.codex/hooks/inject-workflow-state.py`（388 行）的差异：

| 差异点 | Claude 版 | Codex 版 |
|--------|----------|----------|
| **行数** | 382 | 388 |
| **注释语言** | 中文 | 英文 |
| **子智能体通知** | 中文 `CODEX_SUB_AGENT_NOTICE` | 英文 `CODEX_SUB_AGENT_NOTICE` |
| **引导通知** | 中文 `CODEX_NO_TASK_BOOTSTRAP_NOTICE` | 英文 `CODEX_NO_TASK_BOOTSTRAP_NOTICE` |
| **面包屑回退行** | `"请参阅 workflow.md 了解当前步骤。"` | `"Refer to workflow.md for current step."` |
| **构建标题** | `f"状态: {status}"` / `f"任务: {task_id} ({status})"` | `f"Status: {status}"` / `f"Task: {task_id} ({status})"` |
| **来源标签** | `"来源"` | `"Source"` |
| **核心逻辑** | 相同 | 相同（代码结构一致） |

两个版本本质上是同一代码的中英文翻译——核心算法（平台检测、任务解析、面包屑构建、Codex 组装）完全相同。

---

## 八、错误处理策略

| 场景 | 处理策略 |
|------|---------|
| stdin 不是有效 JSON | 回退到空 dict `{}` |
| cwd 不在 stdin 中 | 使用 `os.getcwd()` |
| Trellis 根目录未找到 | 静默 `exit(0)`（非 Trellis 项目） |
| workflow.md 不存在/不可读 | `load_breadcrumbs()` 返回空 dict |
| workflow.md 无匹配标签 | `build_breadcrumb()` 回退通用行 |
| config.yaml 加载失败 | `_read_trellis_config()` 返回空 dict |
| active_task.py 导入失败 | `_resolve_active_task()` 异常向上传播 |
| task.json 不存在 | `get_active_task()` 返回 None |
| task.json 解析失败 | `get_active_task()` 返回 None |
| status 为空字符串 | `get_active_task()` 返回 None |
| 平台检测失败 | 返回 None，后续逻辑正常处理 |

**核心原则**：任何错误都不应阻止 hook 输出——即使只输出一个通用面包屑也比静默失败好。

---

## 九、上下文预算

每轮注入的上下文约：

| 块 | 大约大小 | 说明 |
|----|---------|------|
| `<sub-agent-notice>`（仅 Codex） | ~550 B | 子智能体豁免指令 |
| `<trellis-bootstrap>`（仅 Codex + 无任务） | ~650 B | 引导通知 |
| `<codex-mode>`（仅 Codex） | ~40 B | 派发模式横幅 |
| `<workflow-state>` 标题 | ~80 B | 任务 ID + 状态 + 来源 |
| `<workflow-state>` 正文 | ~200-600 B | 工作流步骤指南 |
| **总计（标准平台）** | **~300-700 B** | 极小开销 |
| **总计（Codex + 无任务）** | **~1.5 KB** | 含引导通知 |

对比 SessionStart 的 9-12 KB，本脚本的上下文开销几乎可以忽略不计。

---

## 十、相关文件索引

| 文件 | 角色 |
|------|------|
| `.claude/hooks/inject-workflow-state.py` | 本文分析对象（主版本） |
| `.codex/hooks/inject-workflow-state.py` | Codex 平台变体（英文版） |
| `.claude/hooks/session-start.py` | SessionStart 钩子（会话启动时注入完整上下文） |
| `.trellis/scripts/common/active_task.py` | 活动任务解析 + 会话运行时管理 |
| `.trellis/scripts/common/trellis_config.py` | 轻量级 config.yaml 读取器 |
| `.trellis/workflow.md` | 完整工作流文档 + `[workflow-state:*]` 面包屑标签块（唯一真相来源） |
| `.trellis/config.yaml` | 项目配置（codex.dispatch_mode 等） |
| `.trellis/.runtime/sessions/*.json` | 会话运行时文件（含 current_task 指针） |
| `.trellis/tasks/*/task.json` | 任务定义文件（id, status, package） |
| `.claude/hooks/session-start-analysis.md` | SessionStart 钩子分析文档（本文的姊妹篇） |
| `.claude/hooks/session-start-flowchart.md` | SessionStart 钩子流程图 |

---

## 十一、inject-workflow-state.py 与 session-start.py 协作模式

```
会话生命周期:

  会话启动                          每轮用户输入
  ┌──────────────────────┐       ┌──────────────────────┐
  │  session-start.py    │       │ inject-workflow-     │
  │                      │       │ state.py             │
  │  注入 (~9-12 KB):    │       │                      │
  │  • 会话上下文        │       │  注入 (~300-700 B):  │
  │  • Git 状态          │       │  • 任务 ID + 状态    │
  │  • 任务列表          │       │  • 工作流步骤        │
  │  • 工作流指南        │       │  • Codex 模式横幅    │
  │  • Spec 索引         │       │                      │
  │  • 任务状态 + 下一步  │       │  ← 由 workflow.md   │
  │                      │       │    [workflow-state]  │
  │  ← 静态快照           │       │    标签块驱动        │
  └──────────────────────┘       └──────────────────────┘
           │                              │
           ▼                              ▼
      一次性注入                      每轮动态更新
```

**session-start.py** 提供**静态快照**——会话启动时的项目全貌。AI 从此了解项目结构、规范和工作流。

**inject-workflow-state.py** 提供**每轮动态更新**——当前任务状态可能在不同轮次之间变化（从 `planning` → `in_progress` → `completed`）。它通过 `[workflow-state:STATUS]` 标签确保 AI 始终按照当前状态对应的正确工作流步骤行动。

两个 hook 通过 `workflow.md` 的标签块进行协调——session-start.py 剥离面包屑标签块以避免重复，inject-workflow-state.py 消费这些标签块以提供动态指引。
