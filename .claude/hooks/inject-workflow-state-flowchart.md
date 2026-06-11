# inject-workflow-state.py 流程图

> 可在 GitHub、Mermaid Live Editor 或任何支持 Mermaid 的 Markdown 渲染器中查看。

---

## 1. 总体执行流程

```mermaid
flowchart TD
    A["stdin: hook_input JSON"] --> B{"TRELLIS_HOOKS=0<br/>或 TRELLIS_DISABLE_HOOKS=1?"}
    B -->|"是"| C["sys.exit(0)<br/>跳过注入"]
    B -->|"否"| D["UTF-8 编码初始化<br/>（Windows: stdin/stdout/stderr）"]

    D --> E["解析 stdin JSON<br/>失败 → 空 dict"]
    E --> F["确定 CWD<br/>stdin.cwd → os.getcwd()"]
    F --> G["find_trellis_root(cwd)<br/>向上遍历查找 .trellis/"]

    G --> H{".trellis/ 找到?"}
    H -->|"否"| I["sys.exit(0)<br/>非 Trellis 项目"]
    H -->|"是"| J["load_breadcrumbs(root)<br/>解析 workflow.md 标签块"]

    J --> K["_detect_platform(data)<br/>9 种检测策略"]
    K --> L["_read_trellis_config(root)<br/>加载 config.yaml"]
    L --> M["get_active_task(root, data)<br/>调用 active_task.py"]

    M --> N{"task 返回值?"}
    N -->|"None<br/>无活动任务"| O["resolve_breadcrumb_key<br/>('no_task', platform, config)"]
    O --> P["build_breadcrumb<br/>(None, 'no_task', templates, ...)"]

    N -->|"(task_id, status, source)"| Q["resolve_breadcrumb_key<br/>(status, platform, config)"]
    Q --> R["build_breadcrumb<br/>(task_id, status, templates, source, ...)"]

    P --> S{"platform == 'codex'?"}
    R --> S

    S -->|"是"| T["Codex 特殊组装"]
    T --> T1["前置: CODEX_SUB_AGENT_NOTICE"]
    T1 --> T2{"task is None?"}
    T2 -->|"是"| T3["追加: CODEX_NO_TASK_BOOTSTRAP_NOTICE"]
    T2 -->|"否"| T4["追加: _codex_mode_banner(config)"]
    T3 --> T4
    T4 --> T5["追加: breadcrumb"]
    T5 --> U["确定 hookEventName"]

    S -->|"否"| U

    U --> V{"platform == 'gemini'?"}
    V -->|"是"| W["hookEventName = 'BeforeAgent'"]
    V -->|"否"| X["hookEventName = 'UserPromptSubmit'"]

    W --> Y["构建输出 JSON"]
    X --> Y
    Y --> Z["print(json.dumps(output))<br/>stdout → AI 上下文窗口"]
```

---

## 2. 平台检测详细流程

```mermaid
flowchart TD
    A["_detect_platform(input_data)"] --> B{"input_data<br/>.cursor_version 存在?"}
    B -->|"是"| C["返回 'cursor'"]
    B -->|"否"| D{"遍历环境变量映射"}

    D --> E1["CLAUDE_PROJECT_DIR → 'claude'"]
    D --> E2["CURSOR_PROJECT_DIR → 'cursor'"]
    D --> E3["CODEBUDDY_PROJECT_DIR → 'codebuddy'"]
    D --> E4["FACTORY_PROJECT_DIR → 'droid'"]
    D --> E5["GEMINI_PROJECT_DIR → 'gemini'"]
    D --> E6["QODER_PROJECT_DIR → 'qoder'"]
    D --> E7["KIRO_PROJECT_DIR → 'kiro'"]
    D --> E8["COPILOT_PROJECT_DIR → 'copilot'"]

    E1 --> F{"任一匹配?"}
    E2 --> F
    E3 --> F
    E4 --> F
    E5 --> F
    E6 --> F
    E7 --> F
    E8 --> F

    F -->|"是"| G["返回平台名称"]
    F -->|"否"| H{"sys.argv[0] 路径分析"}

    H --> I1[".claude/ → 'claude'"]
    H --> I2[".cursor/ → 'cursor'"]
    H --> I3[".codex/ → 'codex'"]
    H --> I4[".gemini/ → 'gemini'"]
    H --> I5[".qoder/ → 'qoder'"]
    H --> I6[".codebuddy/ → 'codebuddy'"]
    H --> I7[".factory/ → 'droid'"]
    H --> I8[".kiro/ → 'kiro'"]

    I1 --> J{"任一匹配?"}
    I2 --> J
    I3 --> J
    I4 --> J
    I5 --> J
    I6 --> J
    I7 --> J
    I8 --> J

    J -->|"是"| K["返回平台名称"]
    J -->|"否"| L["返回 None<br/>（未知平台）"]
```

---

## 3. Trellis 根目录发现流程

```mermaid
flowchart TD
    A["find_trellis_root(start)"] --> B["cur = start.resolve()"]
    B --> C{"(cur / '.trellis').is_dir()?"}
    C -->|"是"| D["返回 cur<br/>（Trellis 根目录）"]
    C -->|"否"| E{"cur == cur.parent?<br/>（已到达文件系统根）"}
    E -->|"是"| F["返回 None<br/>（非 Trellis 项目）"]
    E -->|"否"| G["cur = cur.parent<br/>（向上一级）"]
    G --> C
```

---

## 4. 活动任务解析详细流程

```mermaid
flowchart TD
    A["get_active_task(root, input_data)"] --> B["_resolve_active_task(root, data, platform=platform)"]
    B --> C["导入 common.active_task.<br/>resolve_active_task"]
    C --> D["调用 resolve_active_task()"]

    D --> E{"context_key 存在?"}
    E -->|"是"| F["读取 .runtime/sessions/&lt;key&gt;.json"]
    F --> G{"文件存在且有 current_task?"}
    G -->|"是"| H["返回 ActiveTask<br/>source='session'"]
    G -->|"否"| I{"恰好 1 个 session 文件?"}
    E -->|"否"| I

    I -->|"是"| J["读取该唯一会话文件"]
    J --> K{"有 current_task?"}
    K -->|"是"| L["返回 ActiveTask<br/>source='session-fallback'"]
    K -->|"否"| M["返回 ActiveTask(None, 'none')"]
    I -->|"0 或 ≥2 个文件"| M

    H --> N{"active.task_path 为 None?"}
    L --> N
    M --> N

    N -->|"是"| O["返回 None<br/>（无活动任务）"]
    N -->|"否"| P["task_dir = Path(task_path)<br/>非绝对路径 → root / task_dir"]

    P --> Q{"active.stale?"}
    Q -->|"是（任务目录已删除）"| R["返回 (dir_name,<br/>'stale_{source_type}',<br/>source)"]
    Q -->|"否"| S{"task_dir/task.json 存在?"}

    S -->|"否"| O
    S -->|"是"| T["json.loads(task.json)"]
    T --> U{"解析成功且 status<br/>为非空字符串?"}
    U -->|"是"| V["返回 (task_id, status, source)"]
    U -->|"否"| O
```

---

## 5. 面包屑模板加载流程

```mermaid
flowchart TD
    A["load_breadcrumbs(root)"] --> B{"workflow.md 存在?"}
    B -->|"否"| C["返回空 dict {}"]
    B -->|"是"| D["workflow.read_text(utf-8)"]

    D --> E{"读取成功?"}
    E -->|"否"| C
    E -->|"是"| F["_TAG_RE.finditer(content)<br/>正则匹配所有标签块"]

    F --> G["遍历匹配结果"]
    G --> H["提取 status = group(1)<br/>提取 body = group(2).strip()"]
    H --> I{"body 非空?"}
    I -->|"是"| J["result[status] = body"]
    I -->|"否"| K["跳过（空标签块）"]
    J --> G
    K --> G

    G --> L["返回 result dict<br/>{status: body_text}"]
```

### 5.1 正则表达式说明

```
_TAG_RE = re.compile(
    r"\[workflow-state:([A-Za-z0-9_-]+)\]\s*\n"   ← 开始标签，捕获 STATUS
    r"(.*?)"                                        ← 正文（非贪婪）
    r"\n\s*\[/workflow-state:\1\]",                 ← 结束标签，反向引用验证配对
    re.DOTALL,                                       ← . 匹配换行符
)
```

### 5.2 workflow.md 标签块结构

```
┌─────────────────────────────────────────────┐
│ workflow.md                                 │
├─────────────────────────────────────────────┤
│                                             │
│  [workflow-state:no_task]                   │
│  - 无活跃 task。                             │
│  **A 直接回答** — 纯粹的问答...              │
│  **B 先建任务** — ...                       │
│  **C 内联修改** — ...                       │
│  [/workflow-state:no_task]                  │
│                                             │
│  [workflow-state:planning]                  │
│  加载 `trellis-brainstorm` 技能...          │
│  阶段 1.3（必需，一次）...                   │
│  [/workflow-state:planning]                 │
│                                             │
│  [workflow-state:planning-inline]           │
│  加载 `trellis-brainstorm` 技能...          │
│  在内联派发模式下，阶段 1.3 被跳过...        │
│  [/workflow-state:planning-inline]          │
│                                             │
│  [workflow-state:in_progress]               │
│  **流程**：trellis-implement → ...          │
│  [/workflow-state:in_progress]              │
│                                             │
│  [workflow-state:in_progress-inline]        │
│  **流程**（内联模式）：主 session 加载...    │
│  [/workflow-state:in_progress-inline]       │
│                                             │
│  [workflow-state:completed]                 │
│  代码已通过阶段 3.4 提交...                  │
│  [/workflow-state:completed]                │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 6. Codex 面包屑键解析流程

```mermaid
flowchart TD
    A["resolve_breadcrumb_key(status, platform, config)"] --> B{"platform == 'codex'?"}
    B -->|"否"| C["返回 status（原样）<br/>非 Codex 平台无需特殊处理"]
    B -->|"是"| D["mode = 'inline'（默认）"]

    D --> E{"config 是 dict?"}
    E -->|"否"| F["返回 '{status}-inline'"]
    E -->|"是"| G{"config.codex 存在?"}
    G -->|"否"| F
    G -->|"是"| H{"codex.dispatch_mode?"}

    H -->|"'inline'"| F
    H -->|"'sub-agent'"| I["返回 status（原样）<br/>子智能体模式使用标准标签"]
    H -->|"缺失/无效"| F

    F --> J["最终键: '{status}-inline'<br/>→ 匹配 workflow.md 中<br/>  [workflow-state:{status}-inline]"]
    I --> K["最终键: '{status}'<br/>→ 匹配 workflow.md 中<br/>  [workflow-state:{status}]"]
```

---

## 7. 面包屑构建流程

```mermaid
flowchart TD
    A["build_breadcrumb(task_id, status, templates, source, breadcrumb_key)"] --> B["lookup_key = breadcrumb_key or status"]

    B --> C["body = templates.get(lookup_key)"]
    C --> D{"body 为 None<br/>且 lookup_key ≠ status?"}
    D -->|"是"| E["body = templates.get(status)<br/>（回退到原始状态键）"]
    D -->|"否"| F{"body 为 None?"}
    E --> F
    F -->|"是"| G["body = '请参阅 workflow.md<br/>了解当前步骤。'<br/>（通用回退行）"]
    F -->|"否"| H{"task_id 为 None?"}

    G --> H
    H -->|"是"| I["header = '状态: {status}'"]
    H -->|"否"| J["header = '任务: {task_id} ({status})'"]

    I --> K{"source 存在?"}
    J --> K
    K -->|"是"| L["header += '\n来源: {source}'"]
    K -->|"否"| M["组装 XML 块"]

    L --> M
    M --> N["返回:<br/>&lt;workflow-state&gt;<br/>  {header}<br/>  {body}<br/>&lt;/workflow-state&gt;"]
```

### 7.1 输出示例

**有活动任务（标准平台）**：
```xml
<workflow-state>
任务: trellis-python (in_progress)
来源: session-fallback:claude_d77f67d7-b3a3-4e90-baf3-cf3c89491de9
**流程**：trellis-implement → trellis-check → trellis-update-spec → 提交（阶段 3.4）→ `/trellis:finish-work`。
...
</workflow-state>
```

**无活动任务（标准平台）**：
```xml
<workflow-state>
状态: no_task
- 无活跃 task。
**A 直接回答** — 纯粹的问答 / 解释 / 查找 / 聊天...
**B 先建任务** — ...
**C 内联修改** — ...
</workflow-state>
```

**Codex 完整输出（无任务 + inline 模式）**：
```xml
<sub-agent-notice>
子智能体通知 — 如果通过 spawn_agent 派生，请先阅读
...
</sub-agent-notice>

<trellis-bootstrap>
你正在 Trellis 管理的 Codex 会话中运行，当前没有活动任务。
...
</trellis-bootstrap>

<codex-mode>inline</codex-mode>

<workflow-state>
状态: no_task
...
</workflow-state>
```

---

## 8. Gemini 事件名选择流程

```mermaid
flowchart TD
    A["确定 hookEventName"] --> B{"platform == 'gemini'?"}
    B -->|"是"| C["hookEventName = 'BeforeAgent'<br/>（Gemini CLI 0.40.x+ 兼容）"]
    B -->|"否"| D["hookEventName = 'UserPromptSubmit'<br/>（Claude Code 标准命名，<br/>Cursor/Qoder/CodeBuddy/<br/>Droid/Codex/Copilot 均接受）"]
```

---

## 9. 完整数据流（输入端 → 输出端）

```mermaid
flowchart LR
    subgraph 输入
        A1["环境变量<br/>(平台ID, TRELLIS_HOOKS,<br/>SESSION_ID, ...)"]
        A2["stdin JSON<br/>(hook_input: cwd,<br/>session_id, ...)"]
        A3["文件系统<br/>(.trellis/workflow.md,<br/>.trellis/config.yaml,<br/>.trellis/tasks/*/task.json,<br/>.runtime/sessions/*.json)"]
    end

    subgraph 处理
        B1["跳过检查<br/>TRELLIS_HOOKS / DISABLE"]
        B2["平台检测<br/>_detect_platform()"]
        B3["根目录发现<br/>find_trellis_root()"]
        B4["配置加载<br/>_read_trellis_config()"]
        B5["活动任务解析<br/>get_active_task()"]
        B6["面包屑加载<br/>load_breadcrumbs()"]
        B7["键解析<br/>resolve_breadcrumb_key()"]
        B8["面包屑构建<br/>build_breadcrumb()"]
        B9["Codex 组装<br/>(仅 Codex 平台)"]
    end

    subgraph 输出
        C1["&lt;sub-agent-notice&gt;<br/>（仅 Codex）"]
        C2["&lt;trellis-bootstrap&gt;<br/>（仅 Codex + 无任务）"]
        C3["&lt;codex-mode&gt;<br/>（仅 Codex）"]
        C4["&lt;workflow-state&gt;<br/>任务 ID + 状态 + 工作流"]
    end

    A1 --> B1
    A1 --> B2
    A2 --> B1
    A2 --> B2
    A2 --> B5
    A3 --> B3
    A3 --> B4
    A3 --> B5
    A3 --> B6

    B1 --> B3
    B2 --> B5
    B2 --> B7
    B2 --> B9
    B3 --> B4
    B3 --> B6
    B4 --> B7
    B5 --> B8
    B6 --> B8
    B7 --> B8
    B8 --> B9

    B9 --> C1
    B9 --> C2
    B9 --> C3
    B9 --> C4

    C1 --> D["stdout JSON<br/>→ AI 上下文窗口<br/>（每轮 ~300-1500 B）"]
    C2 --> D
    C3 --> D
    C4 --> D
```

---

## 10. 时序图：UserPromptSubmit 钩子生命周期

```mermaid
sequenceDiagram
    actor User
    participant CLI as AI 助手 CLI
    participant Hook as inject-workflow-state.py
    participant FS as 文件系统
    participant AT as active_task.py

    User->>CLI: 输入提示词
    CLI->>Hook: 调用钩子 (stdin = hook_input JSON)

    Note over Hook: 1. 环境初始化
    Hook->>Hook: UTF-8 编码（Windows）

    Note over Hook: 2. 跳过检查
    alt TRELLIS_HOOKS=0 或 DISABLE=1
        Hook-->>CLI: exit(0)
    end

    Note over Hook: 3. 项目定位
    Hook->>FS: find_trellis_root(cwd)
    alt 未找到 .trellis/
        Hook-->>CLI: exit(0)
    end

    Note over Hook: 4. 加载面包屑模板
    Hook->>FS: 读取 workflow.md
    FS-->>Hook: 标签块 {status: body}

    Note over Hook: 5. 平台 + 配置
    Hook->>Hook: _detect_platform(data)
    Hook->>FS: 读取 config.yaml
    FS-->>Hook: config dict

    Note over Hook: 6. 活动任务解析
    Hook->>AT: resolve_active_task(root, data, platform)
    AT->>FS: 读取 .runtime/sessions/*.json
    FS-->>AT: 会话上下文
    AT->>FS: 读取 task.json
    FS-->>AT: task_id + status
    AT-->>Hook: task 或 None

    Note over Hook: 7. 构建面包屑
    Hook->>Hook: resolve_breadcrumb_key()
    Hook->>Hook: build_breadcrumb()

    Note over Hook: 8. Codex 组装（如需要）
    opt platform == "codex"
        Hook->>Hook: 附加 SUB_AGENT_NOTICE
        alt task is None
            Hook->>Hook: 附加 BOOTSTRAP_NOTICE
        end
        Hook->>Hook: 附加 codex-mode banner
    end

    Note over Hook: 9. JSON 输出
    Hook->>Hook: hookEventName 选择
    Hook-->>CLI: stdout JSON (additionalContext)
    CLI-->>User: AI 已感知当前任务状态
```

---

## 11. 类图：核心数据结构

```mermaid
classDiagram
    class HookInput {
        +str? cwd
        +str? session_id
        +str? conversation_id
        +str? transcript_path
        +str? cursor_version
    }

    class ActiveTaskResult {
        +str? task_path
        +str source_type
        +str? context_key
        +bool stale
        +str source()
    }

    class TaskInfo {
        +str task_id
        +str status
        +str source
    }

    class BreadcrumbTemplates {
        +dict~str,str~ status_to_body
    }

    class TrellisConfig {
        +dict codex
        +dict packages
    }

    class WorkflowStateBlock {
        +str header
        +str body
    }

    class HookOutput {
        +str hookEventName
        +str additionalContext
    }

    HookInput --> ActiveTaskResult : 解析为
    ActiveTaskResult --> TaskInfo : get_active_task() 提取
    BreadcrumbTemplates --> WorkflowStateBlock : build_breadcrumb() 组装
    TrellisConfig --> WorkflowStateBlock : resolve_breadcrumb_key() 选择键
    TaskInfo --> WorkflowStateBlock : 提供标题信息
    WorkflowStateBlock --> HookOutput : 序列化为 additionalContext
```

---

## 12. 状态到面包屑映射全景图

```mermaid
flowchart TD
    subgraph "任务状态（来自 task.json）"
        S1["no_task<br/>（伪状态：无活动任务）"]
        S2["planning<br/>（阶段 1：头脑风暴）"]
        S3["in_progress<br/>（阶段 2+3：实现+收尾）"]
        S4["completed<br/>（阶段 3.5：已归档，当前废弃）"]
        S5["stale_session<br/>（过期指针）"]
        S6["stale_session-fallback<br/>（过期回退指针）"]
    end

    subgraph "Codex dispatch_mode 影响"
        D1["dispatch_mode = inline（默认）"]
        D2["dispatch_mode = sub-agent"]
    end

    subgraph "workflow.md 中的标签块"
        T1["[workflow-state:no_task]"]
        T2["[workflow-state:planning]"]
        T3["[workflow-state:planning-inline]"]
        T4["[workflow-state:in_progress]"]
        T5["[workflow-state:in_progress-inline]"]
        T6["[workflow-state:completed]"]
    end

    subgraph "最终输出的面包屑"
        B1["无活跃 task<br/>→ A/B/C 规则"]
        B2["头脑风暴 + JSONL 整理<br/>→ 派发子智能体"]
        B3["头脑风暴 → 主 session 直接编辑<br/>（跳过 JSONL 整理）"]
        B4["trellis-implement → check<br/>→ update-spec → 提交"]
        B5["主 session 加载 before-dev<br/>→ 编辑 → check → 提交"]
        B6["运行 /trellis:finish-work"]
    end

    S1 --> T1
    S2 --> D1
    S2 --> D2
    D1 --> T3
    D2 --> T2
    S3 --> D1
    S3 --> D2
    D1 --> T5
    D2 --> T4
    S4 --> T6
    S5 -.->|"无匹配标签"| B7["通用回退行<br/>'请参阅 workflow.md'"]
    S6 -.->|"无匹配标签"| B7

    T1 --> B1
    T2 --> B2
    T3 --> B3
    T4 --> B4
    T5 --> B5
    T6 --> B6
```

---

## 附录：关键常量和阈值

| 常量 | 值 | 位置 |
|------|-----|------|
| 跳过环境变量 | `TRELLIS_HOOKS=0` 或 `TRELLIS_DISABLE_HOOKS=1` | `main()` 第 323 行 |
| 标签正则 | `\[workflow-state:([A-Za-z0-9_-]+)\]\s*\n(.*?)\n\s*\[/workflow-state:\1\]` | `_TAG_RE` 第 200 行 |
| Codex 默认 dispatch_mode | `inline` | `resolve_breadcrumb_key()` 第 287 行 |
| Gemini hook 事件名 | `BeforeAgent` | `main()` 第 367 行 |
| 其他平台 hook 事件名 | `UserPromptSubmit` | `main()` 第 367 行 |
| 面包屑回退文本 | `请参阅 workflow.md 了解当前步骤。` | `build_breadcrumb()` 第 311 行 |
| 支持平台数 | 9 个（Claude/Cursor/Codex/Qoder/CodeBuddy/Droid/Gemini/Kiro/Copilot） | `_detect_platform()` 第 122 行 |
| Kiro 支持 | 无每轮 hook 入口点（写入了 hooks 目录但未接线） | 文件头部注释 |
