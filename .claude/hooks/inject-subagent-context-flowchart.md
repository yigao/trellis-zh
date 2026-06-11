# inject-subagent-context.py 流程图

> 可在 GitHub、Mermaid Live Editor 或任何支持 Mermaid 的 Markdown 渲染器中查看。

---

## 1. 总体执行流程

```mermaid
flowchart TD
    A["stdin: hook_input JSON"] --> B{"TRELLIS_HOOKS=0<br/>或 TRELLIS_DISABLE_HOOKS=1?"}
    B -->|"是"| C["sys.exit(0)<br/>跳过注入"]
    B -->|"否"| D["UTF-8 编码初始化<br/>（Windows: stdout 重配置）"]

    D --> E["json.load(sys.stdin)<br/>解析失败 → sys.exit(0)"]
    E --> F["_parse_hook_input(input_data)<br/>解析子智能体类型和原始 prompt"]

    F --> G{"subagent_type<br/>in AGENTS_ALL?"}
    G -->|"否"| H["sys.exit(0)<br/>非 Trellis 子智能体"]

    G -->|"是"| I["find_repo_root(cwd)<br/>向上遍历查找 .git/"]
    I --> J{".git 找到?"}
    J -->|"否"| K["sys.exit(0)<br/>非 git 仓库"]

    J -->|"是"| L["get_current_task(repo_root, input_data)<br/>调用 active_task.resolve_active_task()"]
    L --> M{"subagent_type<br/>in AGENTS_REQUIRE_TASK?"}

    M -->|"是 (implement/check)"| N{"task_dir 存在?"}
    N -->|"否"| O["sys.exit(0)"]
    N -->|"是"| P{"任务目录<br/>在磁盘上存在?"}
    P -->|"否"| O

    M -->|"否 (research)"| Q["task_dir 可选<br/>继续执行"]

    P -->|"是"| R{"检测 [finish] 标记?"}
    R -->|"是"| S["使用 Finish 上下文<br/>get_finish_context()"]
    R -->|"否"| T["按智能体类型<br/>构建上下文"]

    Q --> U["get_research_context()<br/>动态扫描 Spec 目录树"]

    S --> V["build_finish_prompt()"]
    T --> W{"subagent_type?"}
    W -->|"implement"| X["get_implement_context()<br/>→ build_implement_prompt()"]
    W -->|"check"| Y["get_check_context()<br/>→ build_check_prompt()"]

    U --> ZA["build_research_prompt()"]
    X --> ZB{"context 非空?"}
    Y --> ZB
    V --> ZB
    ZA --> ZB

    ZB -->|"否"| ZC["sys.exit(0)"]
    ZB -->|"是"| ZD["组装多平台输出格式"]

    ZD --> ZE["print(json.dumps(output))<br/>sys.exit(0)"]
```

---

## 2. 钩子输入解析 `_parse_hook_input()`

```mermaid
flowchart TD
    A["input_data = {tool_input, tool_name, ...}"] --> B{"tool_name 是什么?"}

    B -->|"Task / Agent / Subagent<br/>(Claude, Cursor, Qoder, CodeBuddy, Droid)"| C["_extract_subagent_type(tool_input)"]
    C --> D["返回 (subagent_type,<br/>tool_input.prompt,<br/>tool_input)"]

    B -->|"agentSpawn hook<br/>(Kiro)"| E{"agent_name<br/>存在?"}
    E -->|"是"| F["返回 (agent_name,<br/>prompt, tool_input)"]
    E -->|"否"| G["返回 ('', '', tool_input)"]

    B -->|"智能体名称<br/>(Gemini CLI)"| H{"tool_name<br/>in AGENTS_ALL?"}
    H -->|"是"| I["返回 (tool_name,<br/>tool_input.prompt,<br/>tool_input)"]
    H -->|"否"| J{"toolName<br/>in AGENTS_ALL?<br/>(Copilot)"}
    J -->|"是"| K["返回 (toolName,<br/>toolArgs, tool_input)"]
    J -->|"否"| G
```

---

## 3. 子智能体名称提取 `_extract_subagent_name()`

```mermaid
flowchart TD
    A["value: Any"] --> B{"value 是字符串?"}
    B -->|"是"| C["返回 stripped value"]

    B -->|"否"| D{"value 是字典?"}
    D -->|"否"| E["返回 ''"]

    D -->|"是"| F["尝试 name / subagent_type_name<br/>/ subagentTypeName 键"]
    F --> G{"找到?"}
    G -->|"是"| H["返回名称"]

    G -->|"否"| I["尝试 value.custom.name<br/>(Cursor protobuf oneof)"]
    I --> J{"找到?"}
    J -->|"是"| H

    J -->|"否"| K["尝试 value.type<br/>(case='custom' → value.name)"]
    K --> L{"找到?"}
    L -->|"是"| H

    L -->|"否"| M["尝试顶层 case='custom'<br/>→ value.name"]
    M --> N{"找到?"}
    N -->|"是"| H

    N -->|"否"| O["回退: 在字典中搜索<br/>AGENTS_ALL 中的名称"]
    O --> P{"找到?"}
    P -->|"是"| H
    P -->|"否"| E
```

---

## 4. 平台检测 `_detect_platform()`

```mermaid
flowchart TD
    A["input_data: dict"] --> B{"cursor_version<br/>字段存在?"}
    B -->|"是"| C["返回 'cursor'"]

    B -->|"否"| D["检查 8 个环境变量"]
    D --> E{"CLAUDE_PROJECT_DIR?"} -->|"是"| F["返回 'claude'"]
    E -->|"否"| G{"CURSOR_PROJECT_DIR?"} -->|"是"| H["返回 'cursor'"]
    G -->|"否"| I{"CODEBUDDY_PROJECT_DIR?"} -->|"是"| J["返回 'codebuddy'"]
    I -->|"否"| K{"FACTORY_PROJECT_DIR?"} -->|"是"| L["返回 'droid'"]
    K -->|"否"| M{"GEMINI_PROJECT_DIR?"} -->|"是"| N["返回 'gemini'"]
    M -->|"否"| O{"QODER_PROJECT_DIR?"} -->|"是"| P["返回 'qoder'"]
    O -->|"否"| Q{"KIRO_PROJECT_DIR?"} -->|"是"| R["返回 'kiro'"]
    Q -->|"否"| S{"COPILOT_PROJECT_DIR?"} -->|"是"| T["返回 'copilot'"]

    S -->|"否"| U["分析 sys.argv[0] 路径"]
    U --> V{".claude" in parts?} -->|"是"| F
    V -->|"否"| W{".cursor" in parts?} -->|"是"| H
    W -->|"否"| X{".gemini" in parts?} -->|"是"| N
    X -->|"否"| Y{".qoder" in parts?} -->|"是"| P
    Y -->|"否"| Z{".codebuddy" in parts?} -->|"是"| J
    Z -->|"否"| AA{".factory" in parts?} -->|"是"| L
    AA -->|"否"| AB{".kiro" in parts?} -->|"是"| R
    AB -->|"否"| AC["返回 None"]
```

---

## 5. JSONL 上下文解析 `read_jsonl_entries()`

```mermaid
flowchart TD
    A["输入: base_path, jsonl_path"] --> B{"JSONL 文件<br/>存在?"}
    B -->|"否"| C["stderr: 警告<br/>返回 []"]

    B -->|"是"| D["逐行读取 JSONL"]
    D --> E{"取下一行"}
    E --> F{"空行?"}
    F -->|"是"| E

    F -->|"否"| G["json.loads(line)"]
    G --> H{"JSON 解码<br/>成功?"}
    H -->|"否"| E

    H -->|"是"| I{"item.file 或<br/>item.path 存在?"}
    I -->|"否"| J["种子/注释行<br/>静默跳过"]
    J --> E

    I -->|"是"| K["saw_real_entry = True"]
    K --> L{"entry_type ==<br/>'directory'?"}
    L -->|"是"| M["read_directory_contents()<br/>读取目录中所有 .md<br/>（最多 20 个文件）"]
    M --> N["results.extend(...)"]

    L -->|"否 (file)"| O["read_file_content()<br/>读取单个文件"]
    O --> P{"文件存在<br/>且读取成功?"}
    P -->|"是"| Q["results.append(...)"]
    P -->|"否"| E

    N --> E
    Q --> E

    E -->|"文件结束"| R{"saw_real_entry<br/>== False?"}
    R -->|"是"| S["stderr: 警告<br/>（仅有种子/空行）"]
    R -->|"否"| T["返回 results"]
    S --> T
```

---

## 6. 各智能体上下文构建

```mermaid
flowchart TD
    subgraph IMPLEMENT["Implement 智能体"]
        I1["get_implement_context()"] --> I2["① read_jsonl_entries('implement.jsonl')<br/>开发规范、编码约定"]
        I2 --> I3["② read_file_content('prd.md')<br/>需求文档"]
        I3 --> I4["③ read_file_content('info.md')<br/>技术设计文档"]
        I4 --> I5["build_implement_prompt()<br/>组装: 角色 + 上下文 + 任务 + 工作流"]
    end

    subgraph CHECK["Check 智能体"]
        C1["get_check_context()"] --> C2["① read_jsonl_entries('check.jsonl')<br/>检查规范、检查清单"]
        C2 --> C3["② read_file_content('prd.md')<br/>需求文档（验证用）"]
        C3 --> C4["build_check_prompt()<br/>组装: 角色 + 上下文 + 任务 + 自修复工作流"]
    end

    subgraph FINISH["Finish 阶段（Check 变体）"]
        F1["get_finish_context()"] --> F2["复用 get_check_context()<br/>check.jsonl + prd.md"]
        F2 --> F3["build_finish_prompt()<br/>组装: PR 前最终检查 + 规范同步"]
    end

    subgraph RESEARCH["Research 智能体"]
        R1["get_research_context()"] --> R2["① 动态扫描 .trellis/spec/<br/>构建目录树"]
        R2 --> R3["② 添加搜索提示<br/>(Glob, Grep, Exa, ...)"]
        R3 --> R4["build_research_prompt()<br/>组装: 查找和解释信息 + 严格边界"]
    end
```

---

## 7. 输出格式适配

```mermaid
flowchart LR
    A["updated = {<br/>  ...tool_input,<br/>  prompt: new_prompt<br/>}"] --> B["组装三层输出"]

    B --> C["hookSpecificOutput<br/>├─ hookEventName: 'PreToolUse'<br/>├─ permissionDecision: 'allow'<br/>└─ updatedInput: updated"]
    B --> D["permission: 'allow'<br/>updated_input: updated"]
    B --> E["updatedInput: updated"]

    C --> F["目标: Claude Code<br/>Qoder, CodeBuddy, Droid"]
    D --> G["目标: Cursor"]
    E --> H["目标: Gemini CLI"]

    F --> I["print(json.dumps(output))"]
    G --> I
    H --> I
```

---

## 8. 三类智能体完整时序图

```mermaid
sequenceDiagram
    actor User as 用户
    participant Main as 主会话 AI
    participant Hook as inject-subagent-context.py
    participant FS as 文件系统
    participant AT as active_task.py
    participant Sub as 子智能体

    User->>Main: 发送任务指令
    Main->>Hook: PreToolUse 触发<br/>(Task 工具调用前)

    rect rgb(240, 248, 255)
        Note over Hook: 解析阶段
        Hook->>Hook: 解析 stdin JSON
        Hook->>Hook: 检测子智能体类型
        Hook->>Hook: 检测平台
    end

    rect rgb(255, 248, 240)
        Note over Hook, AT: 任务解析阶段
        Hook->>AT: resolve_active_task(repo_root, input_data)
        AT->>FS: 读取会话运行时文件
        AT-->>Hook: ActiveTask(task_path, ...)
    end

    rect rgb(240, 255, 240)
        Note over Hook, FS: 上下文加载阶段
        Hook->>FS: 读取 {agent}.jsonl
        FS-->>Hook: JSONL 条目列表
        Hook->>FS: 读取引用的 spec 文件
        FS-->>Hook: 文件内容
        Hook->>FS: 读取 prd.md / info.md
        FS-->>Hook: 需求/设计文档
    end

    rect rgb(255, 240, 255)
        Note over Hook: 组装阶段
        Hook->>Hook: build_*_prompt(original, context)
        Hook->>Hook: 组装多平台 JSON 输出
    end

    Hook-->>Main: 更新后的 tool_input<br/>(含注入上下文)
    Main->>Sub: 派生子智能体<br/>(携带完整上下文)
    Sub->>Sub: 自主工作<br/>(无需恢复、无需分段)
```

---

## 9. 错误处理决策树

```mermaid
flowchart TD
    A["异常/边界情况"] --> B{"影响范围?"}

    B -->|"stdin JSON 解析失败"| C["sys.exit(0)<br/>静默退出，不阻止工具调用"]
    B -->|"非 Trellis 子智能体"| C
    B -->|"找不到 .git"| C
    B -->|"implement/check 无任务目录"| C
    B -->|"任务目录在磁盘上不存在"| C
    B -->|"上下文为空"| C

    B -->|"JSONL 文件不存在"| D["stderr 警告<br/>返回空列表，继续执行"]
    B -->|"JSONL 无已整理条目"| D

    B -->|"JSONL 单行 JSON 解码失败"| E["静默跳过该行<br/>继续处理后续行"]
    B -->|"引用的文件不存在"| E
    B -->|"目录读取异常"| E

    B -->|"TRELLIS_HOOKS=0"| F["立即 sys.exit(0)<br/>不执行任何逻辑"]
```

---

## 10. 函数调用关系图

```mermaid
flowchart TD
    main --> find_repo_root
    main --> _parse_hook_input
    main --> get_current_task
    main --> get_implement_context
    main --> get_check_context
    main --> get_finish_context
    main --> get_research_context
    main --> build_implement_prompt
    main --> build_check_prompt
    main --> build_finish_prompt
    main --> build_research_prompt

    _parse_hook_input --> _extract_subagent_type
    _extract_subagent_type --> _extract_subagent_name

    get_current_task --> _detect_platform
    get_current_task -->|"import"| active_task.resolve_active_task

    get_implement_context --> get_agent_context
    get_implement_context --> read_file_content
    get_agent_context --> read_jsonl_entries

    get_check_context --> read_jsonl_entries
    get_check_context --> read_file_content

    get_finish_context --> get_check_context

    get_research_context -->|"动态扫描"| Path.iterdir

    read_jsonl_entries --> read_directory_contents
    read_jsonl_entries --> read_file_content
    read_directory_contents --> read_file_content
```

---

## 图例

| 符号 | 含义 |
|------|------|
| `{}` | 条件判断（菱形） |
| `[]` | 处理步骤（矩形） |
| `()` | 开始/结束（圆角矩形） |
| `→` | 流程方向 |
| `-->>` | 返回/响应 |
| 彩色背景 | 逻辑分组 |
