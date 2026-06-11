# session-start.py 流程图

> 可在 GitHub、Mermaid Live Editor 或任何支持 Mermaid 的 Markdown 渲染器中查看。

---

## 1. 总体架构流程

```mermaid
flowchart TD
    A["stdin: hook_input JSON"] --> B{"should_skip_injection()?"}
    B -->|"TRELLIS_HOOKS=0<br/>或 NON_INTERACTIVE=1"| C["sys.exit(0)<br/>跳过注入"]
    B -->|"否"| D["UTF-8 编码初始化<br/>（Windows）"]
    D --> E["项目目录定位<br/>_normalize_windows_shell_path()"]
    E --> F["平台检测<br/>_detect_platform()"]
    F --> G["上下文键解析<br/>_resolve_context_key()"]
    G --> H["持久化到 Bash 环境<br/>_persist_context_key_for_bash()"]
    H --> I["加载 Trellis 配置<br/>_load_trellis_config()"]
    I --> J["Spec 作用域解析<br/>_resolve_spec_scope()"]
    J --> K["旧版迁移检查<br/>_check_legacy_spec()"]

    K --> L["构建输出缓冲区<br/>StringIO"]

    L --> M["写入 &lt;session-context&gt;"]
    M --> N["写入 &lt;first-reply-notice&gt;"]
    N --> O{"旧版迁移警告?"}
    O -->|"是"| P["写入 &lt;migration-warning&gt;"]
    O -->|"否"| Q["写入 &lt;current-state&gt;"]
    P --> Q

    Q --> R["run_script(get_context.py)<br/>子进程 5 秒超时"]
    R --> S["写入 &lt;workflow&gt;<br/>_build_workflow_overview()"]
    S --> T["写入 &lt;guidelines&gt;<br/>spec 索引 + guides 内联"]
    T --> U["写入 &lt;task-status&gt;<br/>_get_task_status() → 状态机"]
    U --> V["写入 &lt;ready&gt;"]

    V --> W["JSON 序列化<br/>两种输出格式"]
    W --> X["stdout 输出<br/>→ AI 上下文窗口"]
```

---

## 2. 平台检测流程

```mermaid
flowchart TD
    A["_detect_platform(input_data)"] --> B{"input_data<br/>.cursor_version?"}
    B -->|"是"| C["返回 'cursor'"]
    B -->|"否"| D{"检查平台环境变量"}

    D --> E["CLAUDE_PROJECT_DIR → 'claude'"]
    D --> F["CURSOR_PROJECT_DIR → 'cursor'"]
    D --> G["CODEBUDDY_PROJECT_DIR → 'codebuddy'"]
    D --> H["FACTORY_PROJECT_DIR → 'droid'"]
    D --> I["GEMINI_PROJECT_DIR → 'gemini'"]
    D --> J["QODER_PROJECT_DIR → 'qoder'"]
    D --> K["KIRO_PROJECT_DIR → 'kiro'"]
    D --> L["COPILOT_PROJECT_DIR → 'copilot'"]

    E --> M{"匹配?"}
    F --> M
    G --> M
    H --> M
    I --> M
    J --> M
    K --> M
    L --> M

    M -->|"是"| N["返回平台名称"]
    M -->|"否"| O{"sys.argv[0]<br/>路径分析"}
    O --> P[".claude/ → 'claude'"]
    O --> Q[".cursor/ → 'cursor'"]
    O --> R[".codex/ → 'codex'"]
    O --> S["..."]
    P --> T{"匹配?"}
    Q --> T
    R --> T
    S --> T
    T -->|"是"| U["返回平台名称"]
    T -->|"否"| V["返回 None"]
```

---

## 3. 上下文键解析流程

```mermaid
flowchart TD
    A["resolve_context_key()"] --> B{"TRELLIS_CONTEXT_ID<br/>环境变量?"}
    B -->|"是"| C["直接返回<br/>（子进程显式覆盖）"]
    B -->|"否"| D{"hook_input 中有<br/>session_id?"}
    D -->|"是"| E["返回 platform_session_&lt;id&gt;"]
    D -->|"否"| F{"hook_input 中有<br/>conversation_id?"}
    F -->|"是"| G["返回 platform_conversation_&lt;id&gt;"]
    F -->|"否"| H{"hook_input 中有<br/>transcript_path?"}
    H -->|"是"| I["返回 platform_transcript_&lt;hash&gt;"]
    H -->|"否"| J{"环境变量中有<br/>平台 SESSION_ID?"}
    J -->|"是"| K["返回 platform_&lt;session_id&gt;"]
    J -->|"否"| L{"环境变量中有<br/>TRANSCRIPT_PATH?"}
    L -->|"是"| M["返回 platform_transcript_&lt;hash&gt;"]
    L -->|"否"| N{"平台是 cursor<br/>且有 shell ticket?"}
    N -->|"是"| O["返回 ticket context_key"]
    N -->|"否"| P["返回 None<br/>（无会话身份）"]
```

---

## 4. 活动任务解析流程（含 session-fallback）

```mermaid
flowchart TD
    A["resolve_active_task()"] --> B{"context_key 存在?"}
    B -->|"是"| C["读取 .runtime/sessions/&lt;key&gt;.json"]
    C --> D{"文件存在且有<br/>current_task?"}
    D -->|"是"| E["返回 ActiveTask<br/>source='session'"]
    D -->|"否"| F{"恰好 1 个<br/>session 文件?"}
    B -->|"否"| F

    F -->|"是"| G["读取该唯一文件"]
    G --> H{"有 current_task?"}
    H -->|"是"| I["返回 ActiveTask<br/>source='session-fallback'<br/>（Class-2 平台子智能体）"]
    H -->|"否"| J["返回 ActiveTask(None, 'none')"]
    F -->|"0 或 ≥2 个文件"| J

    E --> K["检查任务目录是否存在"]
    K -->|"存在"| L["stale=False"]
    K -->|"不存在"| M["stale=True"]
```

---

## 5. 任务状态机（核心决策）

```mermaid
flowchart TD
    A["_get_task_status()"] --> B["_resolve_active_task()"]
    B --> C{"active.task_path?"}
    C -->|"None"| D["<b>NO ACTIVE TASK</b><br/>→ 加载 trellis-brainstorm<br/>→ 用户描述意图<br/>→ task.py create<br/>⚠ 用户覆盖: 跳过/小修/直接改"]

    C -->|"有值"| E{"任务目录存在<br/>且非 stale?"}
    E -->|"否"| F["<b>STALE POINTER</b><br/>→ task.py finish<br/>→ 询问用户下一步"]

    E -->|"是"| G["读取 task.json"]
    G --> H{"status == 'completed'?"}
    H -->|"是"| I["<b>COMPLETED</b><br/>→ trellis-update-spec<br/>→ task.py archive"]

    H -->|"否"| J{"prd.md 存在?"}
    J -->|"否"| K["<b>PLANNING (Phase 1.1)</b><br/>→ trellis-brainstorm<br/>→ 生成 prd.md<br/>⚠ 如需研究 → trellis-research"]

    J -->|"是"| L{"implement.jsonl<br/>有已整理条目?"}
    L -->|"否（仅种子数据）"| M["<b>PLANNING (Phase 1.3)</b><br/>→ 整理 implement.jsonl<br/>→ 整理 check.jsonl<br/>→ 仅 spec + research 路径"]

    L -->|"是"| N["<b>READY</b><br/>→ Phase 2.1: trellis-implement<br/>→ Phase 2.2: trellis-check<br/>→ 子智能体自我豁免<br/>→ 用户覆盖: 你直接改/别派 sub-agent"]
```

---

## 6. Spec 作用域解析

```mermaid
flowchart TD
    A["_resolve_spec_scope()"] --> B{"is_monorepo?"}
    B -->|"否"| C["返回 None<br/>（全量扫描）"]
    B -->|"是"| D{"scope_config?"}

    D -->|"None"| C
    D -->|"'active_task'"| E{"task_pkg 有效?"}
    E -->|"是"| F["返回 {task_pkg}"]
    E -->|"否"| G{"default_pkg 有效?"}
    G -->|"是"| H["返回 {default_pkg}"]
    G -->|"否"| C

    D -->|"list[str]"| I["过滤有效 package"]
    I --> J{"有有效条目?"}
    J -->|"是"| K{"task_pkg 在集合内?"}
    K -->|"否"| L["打印警告<br/>（任务 package 不在 scope 内）"]
    K -->|"是"| M["返回有效 package 集合"]
    L --> M
    J -->|"否"| N["回退链:<br/>task_pkg → default_pkg → 全量扫描"]
```

---

## 7. Workflow 指南构建

```mermaid
flowchart TD
    A["_build_workflow_overview()"] --> B["read_file(workflow.md)"]
    B --> C{"内容存在?"}
    C -->|"否"| D["返回 '未找到 workflow.md'"]
    C -->|"是"| E["提取所有 ## 标题<br/>→ 目录索引"]

    E --> F["_extract_range()<br/>'Phase Index' → 'Customizing Trellis'"]
    F --> G{"提取成功?"}
    G -->|"是"| H["_strip_breadcrumb_tag_blocks()<br/>移除 [workflow-state:...] 块"]
    G -->|"否"| I["跳过 phases 内容"]

    H --> J["组装输出:<br/>1. 章节索引<br/>2. Phase Index<br/>3. Phase 1<br/>4. Phase 2<br/>5. Phase 3"]
    I --> J
    J --> K["返回压缩后的<br/>workflow 指南 (~7KB)"]
```

---

## 8. 完整数据流（输入端 → 输出端）

```mermaid
flowchart LR
    subgraph 输入
        A1["环境变量<br/>(CLAUDE_PROJECT_DIR,<br/>SESSION_ID, ...)"]
        A2["stdin JSON<br/>(hook_input)"]
        A3["文件系统<br/>(.trellis/)"]
        A4["子进程<br/>(get_context.py)"]
    end

    subgraph 处理
        B1["平台检测"]
        B2["上下文键解析"]
        B3["活动任务解析"]
        B4["配置加载"]
        B5["状态机"]
        B6["Workflow 提取"]
        B7["Spec 发现"]
    end

    subgraph 输出
        C1["&lt;session-context&gt;"]
        C2["&lt;current-state&gt;<br/>(git + 任务 + 日志)"]
        C3["&lt;workflow&gt;<br/>(Phase Index + 1/2/3)"]
        C4["&lt;guidelines&gt;<br/>(guides + spec 列表)"]
        C5["&lt;task-status&gt;<br/>(状态 + Next-Action)"]
        C6["&lt;ready&gt;"]
    end

    A1 --> B1
    A1 --> B2
    A2 --> B1
    A2 --> B2
    A2 --> B3
    A3 --> B3
    A3 --> B4
    A3 --> B6
    A3 --> B7
    A4 --> C2

    B1 --> B2
    B2 --> B3
    B3 --> B5
    B4 --> B5
    B4 --> B7

    B5 --> C5
    B6 --> C3
    B7 --> C4

    C1 --> D["stdout JSON<br/>→ AI 上下文窗口<br/>(~9-12 KB)"]
    C2 --> D
    C3 --> D
    C4 --> D
    C5 --> D
    C6 --> D
```

---

## 9. 时序图：SessionStart 钩子生命周期

```mermaid
sequenceDiagram
    actor User
    participant CLI as AI 助手 CLI
    participant Hook as session-start.py
    participant FS as 文件系统
    participant Sub as get_context.py

    User->>CLI: 启动新会话
    CLI->>Hook: 调用钩子 (stdin = hook_input JSON)
    
    Note over Hook: 1. 环境初始化
    Hook->>Hook: UTF-8 编码 / 警告抑制 / 路径规范化
    
    Note over Hook: 2. 跳过检查
    alt 非交互或禁用
        Hook-->>CLI: exit(0)
    end
    
    Note over Hook: 3. 项目定位
    Hook->>Hook: 平台检测 → 项目目录
    
    Note over Hook: 4. 会话身份
    Hook->>FS: 读取 .runtime/sessions/*.json
    FS-->>Hook: 会话上下文
    
    Note over Hook: 5. 配置加载
    Hook->>FS: 读取 .trellis/config.yaml
    FS-->>Hook: packages / spec_scope
    
    Note over Hook: 6. 上下文生成
    Hook->>Sub: 子进程调用 get_context.py
    Sub-->>Hook: git 状态 + 任务 + 日志
    
    Note over Hook: 7. 组装输出
    Hook->>FS: 读取 workflow.md / spec indexes
    FS-->>Hook: 工作流指南 / spec 列表
    
    Hook->>Hook: 状态机决策 → Next-Action
    
    Note over Hook: 8. JSON 输出
    Hook-->>CLI: stdout JSON (additionalContext)
    CLI-->>User: AI 上下文已注入
    
    Note over User,CLI: 用户发送首条消息时,<br/>AI 已拥有完整上下文
```

---

## 10. 类图：核心数据结构

```mermaid
classDiagram
    class ActiveTask {
        +str? task_path
        +str source_type
        +str? context_key
        +bool stale
        +str source()
    }

    class HookInput {
        +str? session_id
        +str? conversation_id
        +str? transcript_path
        +str? cwd
        +str? cursor_version
    }

    class TrellisConfig {
        +bool is_monorepo
        +dict packages
        +list~str~|str|None spec_scope
        +str? task_package
        +str? default_package
    }

    class SessionContext {
        +str current_task
        +str platform
        +str last_seen_at
        +str? current_run
    }

    class TaskStatus {
        +str status
        +str task_title
        +str source
        +str next_action
    }

    class ContextOutput {
        +str session_context
        +str current_state
        +str workflow_guide
        +str guidelines
        +str task_status
    }

    HookInput --> ActiveTask : 解析为
    TrellisConfig --> ContextOutput : 过滤 spec
    SessionContext --> ActiveTask : 包含任务指针
    ActiveTask --> TaskStatus : 状态机决策
    TaskStatus --> ContextOutput : 注入 task-status 块
```

---

## 附录：关键常量和阈值

| 常量 | 值 | 位置 |
|------|-----|------|
| 子进程超时 | 5 秒 | `run_script()` |
| 会话键最大长度 | 160 字符 | `active_task.py:_sanitize_key()` |
| Cursor shell ticket TTL | 30 秒 | `active_task.py:CURSOR_SHELL_TICKET_TTL_SECONDS` |
| Workflow 注入预算 | ~9 KB | `_build_workflow_overview()` |
| 总上下文预算 | ~9-12 KB | 最终输出 |
| WebFetch 内联上限 | 10 次 | `_get_task_status()` 研究提醒 |
| 日志文件最大行数 | 2000 | `config.py:DEFAULT_MAX_JOURNAL_LINES` |
| Session auto-commit 默认 | True | `config.py:DEFAULT_SESSION_AUTO_COMMIT` |
