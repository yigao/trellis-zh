# 开发工作流

---

## 核心原则

1. **先规划再编码** — 在动手之前先弄清楚要做什么
2. **规范靠注入而非记忆** — 指南通过 `hook（钩子）`/`skill（技能）` 注入，而非从记忆中回忆
3. **持久化一切** — 研究、决策和经验教训全部写入文件；对话会被压缩，文件不会
4. **增量开发** — 一次只做一个 `task（任务）`
5. **捕获经验教训** — 每个 task 完成后，回顾并将新知识写回 `spec（规范）`

---

## Trellis 系统

### 开发者身份

首次使用时，初始化你的身份：

```bash
py -3 ./.trellis/scripts/init_developer.py <your-name>
```

创建 `.trellis/.developer`（gitignored）+ `.trellis/workspace/<your-name>/`。

### 规范系统

`.trellis/spec/` 存放按 `package（软件包）` 和 `layer（层级）` 组织的编码指南。

- `.trellis/spec/<package>/<layer>/index.md` — 入口点，包含 **开发前检查清单** + **质量检查**。实际指南位于其指向的 `.md` 文件中。
- `.trellis/spec/guides/index.md` — 跨 package 的思维指南。

```bash
py -3 ./.trellis/scripts/get_context.py --mode packages   # 列出 package / layer
```

**何时更新 spec**：发现新的 `pattern（模式）`/`convention（惯例）` · 需要固化 bug 预防措施 · 新的技术决策。

### 任务系统

每个 task 在 `.trellis/tasks/{MM-DD-name}/` 下拥有独立目录，包含 `prd.md`、`implement.jsonl`、`check.jsonl`、`task.json`，以及可选的 `research/`、`info.md`。

```bash
# 任务生命周期
py -3 ./.trellis/scripts/task.py create "<title>" [--slug <name>] [--parent <dir>]
py -3 ./.trellis/scripts/task.py start <name>          # 设置活跃 task（若可用则为会话级别）
py -3 ./.trellis/scripts/task.py current --source      # 显示活跃 task 及其来源
py -3 ./.trellis/scripts/task.py finish                # 清除活跃 task（触发 after_finish hooks）
py -3 ./.trellis/scripts/task.py archive <name>        # 移至 archive/{year-month}/
py -3 ./.trellis/scripts/task.py list [--mine] [--status <s>]
py -3 ./.trellis/scripts/task.py list-archive

# Code-spec 上下文（通过 JSONL 注入到 implement/check agent（智能体））。
# 对于支持子智能体的平台，`implement.jsonl` / `check.jsonl` 在 `task create` 时
# 会预置种子数据；AI 在阶段 1.3 中填充真正的 spec 和研究条目。
py -3 ./.trellis/scripts/task.py add-context <name> <action> <file> <reason>
py -3 ./.trellis/scripts/task.py list-context <name> [action]
py -3 ./.trellis/scripts/task.py validate <name>

# 任务元数据
py -3 ./.trellis/scripts/task.py set-branch <name> <branch>
py -3 ./.trellis/scripts/task.py set-base-branch <name> <branch>    # PR 目标
py -3 ./.trellis/scripts/task.py set-scope <name> <scope>

# 层级关系（父/子）
py -3 ./.trellis/scripts/task.py add-subtask <parent> <child>
py -3 ./.trellis/scripts/task.py remove-subtask <parent> <child>

# PR 创建
py -3 ./.trellis/scripts/task.py create-pr [name] [--dry-run]
```

> 运行 `py -3 ./.trellis/scripts/task.py --help` 查看权威且最新的命令列表。

**当前任务机制**：`task.py create` 创建 task 目录，并且（当 `session（会话）` 身份可用时）自动设置每个会话的活跃 task `pointer（指针）`，以便规划面包屑立即触发。`task.py start` 写入相同的 pointer（如果已设置则幂等），并将 `task.json.status` 从 `planning` 翻转为 `in_progress`。状态存储在 `.trellis/.runtime/sessions/` 下。如果无法从 hook 输入、`TRELLIS_CONTEXT_ID` 或平台原生的 session 环境变量中获取 `context（上下文）` key，则没有活跃 task，`task.py start` 将失败并给出 session 身份提示。`task.py finish` 删除当前 session 文件（状态不变）。`task.py archive <task>` 写入 `status=completed`，将目录移至 `archive/`，并删除仍指向已归档 task 的任何运行时 session 文件。

### 工作区系统

在 `.trellis/workspace/<developer>/` 下记录每个 AI session，以实现跨 session 追踪。

- `journal-N.md` — session 日志。**每个文件最多 2000 行**；超出时自动创建新的 `journal-(N+1).md`。
- `index.md` — 个人索引（总 session 数、最后活跃时间）。

```bash
py -3 ./.trellis/scripts/add_session.py --title "Title" --commit "hash" --summary "Summary"
```

### 上下文脚本

```bash
py -3 ./.trellis/scripts/get_context.py                            # 完整 session 运行时
py -3 ./.trellis/scripts/get_context.py --mode packages            # 可用 package + spec layer
py -3 ./.trellis/scripts/get_context.py --mode phase --step <X.Y>  # 某工作流步骤的详细指南
```

---

<!--
  WORKFLOW-STATE 面包屑契约（编辑下方标签块之前请先阅读此处）

  嵌入在下方 ## 阶段索引 部分的 4 个 [workflow-state:STATUS] 块
  是每个支持 AI 平台的 UserPromptSubmit hook 所读取的每轮
  `<workflow-state>` 面包屑的**唯一事实来源**。
  inject-workflow-state.py（Python 平台）和
  inject-workflow-state.js（OpenCode 插件）仅解析这些块 —
  自 v0.5.0-rc.0 起，脚本中不再内嵌后备字典。

  STATUS 字符集：[A-Za-z0-9_-]+。当 hook 找不到标签时，
  会降级为通用的 "Refer to workflow.md for current step." 行 —
  有意让其可见，以便用户注意到并修复损坏的 workflow.md。

  不变量（test/regression.test.ts）：
    每个标记为 `[required · once]` 的工作流步骤，
    必须在其所属阶段的 [workflow-state:*] 块中有对应的强制执行行。
    面包屑是唯一的每轮沟通渠道；如果某个强制性步骤在那里没有被提及，
    AI 会静默跳过它（阶段 1.3 JSONL 整理的跳过和阶段 3.4 提交的跳过
    都曾因这个缺口而出现）。

  标签 ↔ 阶段 作用域：
    [workflow-state:no_task]      → 无活跃 task；阶段 1 之前
    [workflow-state:planning]     → 整个阶段 1（status='planning'）
    [workflow-state:in_progress]  → 阶段 2 + 阶段 3.1-3.4
                                    （从 task.py start 到 task.py archive，
                                    status 保持 'in_progress'）
    [workflow-state:completed]    → 当前**已废弃**：cmd_archive 在同一调用中
                                    翻转 status 并移动目录，
                                    因此解析器会丢失 pointer
                                    （保留此块以备将来显式的 in_progress→completed 转换）

  编辑检查清单：
    - 修改 [workflow-state:STATUS] 块时，同时检查对应阶段的
      `[required · once]` 步骤是否同步
    - 编辑后运行 `trellis update` 将新的正文推送到下游用户项目
      （块级别的托管替换）
    - 完整运行时契约：
      .trellis/spec/cli/backend/workflow-state-contract.md
-->

## 阶段索引

```
阶段 1：规划 → 弄清楚要做什么（头脑风暴 + 研究 → prd.md）
阶段 2：执行 → 编写代码并通过质量检查
阶段 3：完成 → 提炼经验教训 + 收尾
```

<!-- 每轮面包屑：当无活跃 task 时显示（阶段 1 之前） -->

[workflow-state:no_task]
无活跃 task。
**A 直接回答** — 纯粹的问答 / 解释 / 查找 / 聊天；不写文件 + 单行回答 + 仓库读取 ≤ 2 个文件 → AI 自行判断，无需覆盖。
**B 创建 task** — 任何实现 / 代码修改 / 构建 / 重构工作。入口顺序：(1) `py -3 ./.trellis/scripts/task.py create "<title>"` 创建 task（status=planning，面包屑切换至 [workflow-state:planning] 以进行头脑风暴 + JSONL 阶段指导）→ (2) 加载 `trellis-brainstorm` 技能与用户讨论需求并迭代 prd.md → (3) 一旦 PRD 完成且 JSONL 整理完毕，运行 `task.py start <task-dir>` 进入 [workflow-state:in_progress] 开始实现骨架。**"看起来很小"不构成将 B 降级为 A 或 C 的理由**。
**C 内联修改**（仅限本轮，B 的逃生出口）— 用户**当前**消息必须包含以下之一："skip trellis" / "no task" / "just do it" / "don't create a task" / "跳过 trellis" / "别走流程" / "小修一下" / "直接改" / "先别建任务" → 简要确认（"ok, skipping trellis flow this turn"），然后内联处理。**没有看到这些短语，你绝不能自行内联**；不要臆造用户从未说过的覆盖指令。
[/workflow-state:no_task]

### 阶段 1：规划
- 1.0 创建 task `[required · once]`（仅 `task.py create`；status 进入 planning）
- 1.1 需求探索 `[required · repeatable]`
- 1.2 研究 `[optional · repeatable]`
- 1.3 配置上下文 `[required · once]` — Claude Code、Cursor、OpenCode、Codex、Kiro、Gemini、Qoder、CodeBuddy、Copilot、Droid、Pi
- 1.4 激活 task `[required · once]`（运行 `task.py start`；status → in_progress）
- 1.5 完成标准

<!-- 每轮面包屑：贯穿阶段 1 显示（status='planning'） -->

[workflow-state:planning]
加载 `trellis-brainstorm` 技能，与用户迭代 prd.md。
阶段 1.3（必需，一次）：在 `task.py start` 之前，你**必须**整理 `implement.jsonl` 和 `check.jsonl` — 列出子智能体需要的 spec / 研究文件，以便它们获得正确的上下文注入。仅当 JSONL 已有 AI 整理的条目时才可以跳过（仅有预置的 `_example` 行不算）。
然后运行 `task.py start <task-dir>` 将 status 翻转为 in_progress。
[/workflow-state:planning]

<!-- 每轮面包屑：当 codex.dispatch_mode=inline 时在阶段 1 显示。
     仅 Codex 可选替代 [workflow-state:planning]。主智能体在阶段 2
     直接编辑代码，因此跳过阶段 1.3 JSONL 整理 —
     内联工作流加载 `trellis-before-dev` 而非将 JSONL 注入子智能体。 -->

[workflow-state:planning-inline]
加载 `trellis-brainstorm` 技能，与用户迭代 prd.md。
在内联派发模式下，阶段 1.3 JSONL 整理**被跳过** — 主 session 在阶段 2 直接加载 `trellis-before-dev` 并自行读取 spec 上下文，因此无需向子智能体注入 JSONL。
然后运行 `task.py start <task-dir>` 将 status 翻转为 in_progress。
[/workflow-state:planning-inline]

### 阶段 2：执行
- 2.1 实现 `[required · repeatable]`
- 2.2 质量检查 `[required · repeatable]`
- 2.3 回滚 `[on demand]`

<!-- 每轮面包屑：status='in_progress' 时显示。
     作用域：全部阶段 2 + 阶段 3.1-3.4（从 task.py start 到 task.py archive，
     status 保持 'in_progress'；只有 archive 会翻转它）。因此正文必须覆盖
     从实现到提交的每个必需步骤，包括阶段 3.3 spec 更新和阶段 3.4 提交。 -->

[workflow-state:in_progress]
**流程**：trellis-implement → trellis-check → trellis-update-spec → 提交（阶段 3.4）→ `/trellis:finish-work`。
**主 session 默认（无覆盖）**：派发 `trellis-implement` / `trellis-check` 子智能体 — 主智能体默认**不**编辑代码。阶段 3.4 提交（必需，一次）：在 trellis-update-spec 之后，或当实现可验证完成时，主智能体**主导提交** — 在面向用户的文字中说明提交计划，然后运行 `git commit` — **在**建议 `/trellis:finish-work` **之前**完成。`/finish-work` 拒绝在脏工作树（`.trellis/workspace/` 和 `.trellis/tasks/` 之外的路径）上运行。
**子智能体自豁免**：如果你已经在以 `trellis-implement` 身份运行，直接从加载的 task 上下文实现，**不要**再派发另一个 `trellis-implement`；如果你已经在以 `trellis-check` 身份运行，直接审查/修复，**不要**再派发另一个 `trellis-check`。默认派发规则仅适用于主 session。
**子智能体派发协议（所有平台、所有子智能体）**：当你派发 `trellis-implement` / `trellis-check` / `trellis-research` 时，你的派发提示**必须**以一行开头：`Active task: <task path from \`task.py current\`>`。没有例外。在 class-2 平台（codex / copilot / gemini / qoder）上，子智能体依赖此行，因为没有 hook 来注入 task 上下文。在 class-1 平台（claude / cursor / opencode / kiro / codebuddy / droid）上，此行通常是冗余的 — hook 直接注入上下文 — 但当 hook 失败时（Windows + Claude Code PreToolUse 静默跳过、`--continue` 恢复、fork 分发、hooks 禁用等），它作为关键的备用方案。对于 `trellis-research`，此行告诉子智能体应写入哪个 `{task_dir}/research/`。
**内联覆盖**（仅限本轮，子智能体派发的逃生出口）：用户当前消息**必须**明确包含以下之一："do it inline" / "no sub-agent" / "你直接改" / "别派 sub-agent" / "main session 写就行" / "不用 sub-agent"。**没有看到这些短语，你绝不能自行内联**；不要臆造用户从未说过的覆盖指令。
[/workflow-state:in_progress]

<!-- 每轮面包屑：当 codex.dispatch_mode=inline 且 status='in_progress' 时显示。
     仅 Codex 可选替代 [workflow-state:in_progress]。主 session 直接编辑代码，
     而非派发子智能体。 -->

[workflow-state:in_progress-inline]
**流程**（内联模式）：主 session 加载 `trellis-before-dev` → 主 session 编辑代码 → 主 session 加载 `trellis-check` → 运行 lint / type-check / 测试 → 修复 → `trellis-update-spec` → 提交（阶段 3.4）→ `/trellis:finish-work`。
**主 session 默认（内联 dispatch_mode）**：主智能体直接编辑代码。**不要**派发 `trellis-implement` / `trellis-check` 子智能体。在编写代码之前加载 `trellis-before-dev` 技能；在报告完成之前加载 `trellis-check` 技能。
阶段 3.4 提交（必需，一次）：在 `trellis-update-spec` 之后，或当实现可验证完成时，主智能体**主导提交** — 在面向用户的文字中说明提交计划，然后运行 `git commit` — **在**建议 `/trellis:finish-work` **之前**完成。`/finish-work` 拒绝在脏工作树（`.trellis/workspace/` 和 `.trellis/tasks/` 之外的路径）上运行。
[/workflow-state:in_progress-inline]

### 阶段 3：完成
- 3.1 质量验证 `[required · repeatable]`
- 3.2 调试回顾 `[on demand]`
- 3.3 Spec 更新 `[required · once]`
- 3.4 提交更改 `[required · once]`
- 3.5 收尾提醒

<!-- 每轮面包屑：status='completed' 时显示。
     当前在正常流程中**已废弃**：cmd_archive 在将 task 目录移至 archive/
     的同一调用中写入 status='completed'，因此活跃 task 解析器会丢失 pointer，
     hook 永远不会对已归档的 task 触发。保留此块以备将来的状态转换重新设计
     （例如显式的 in_progress→completed 命令）。通过与活跃块相同的 spec 渠道进行编辑。 -->

[workflow-state:completed]
代码已通过阶段 3.4 提交；运行 `/trellis:finish-work` 收尾（归档 task + 记录 session）。
如果你到达此状态时仍有未提交的代码，请先返回阶段 3.4 — `/finish-work` 拒绝在脏工作树上运行。
`task.py archive` 删除任何仍指向已归档 task 的运行时 session 文件。
[/workflow-state:completed]

### 规则

1. 确定你处于哪个阶段，然后从该阶段的下一个步骤继续
2. 在每个阶段内按顺序执行步骤；`[required]` 步骤不能跳过
3. 阶段可以回退（例如，执行阶段发现 PRD 缺陷 → 返回规划阶段修复，然后重新进入执行阶段）
4. 标记为 `[once]` 的步骤如果输出已存在则跳过；不要重新运行

### 技能路由

当用户请求匹配以下意图之一时，首先加载对应的 skill（或派发对应的子智能体）—— 不要跳过 skill。

[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi]

| 用户意图 | 路由 |
|---|---|
| 想要新功能 / 需求不明确 | `trellis-brainstorm` |
| 即将编写代码 / 开始实现 | 按阶段 2.1 派发 `trellis-implement` 子智能体 |
| 编写完成 / 想要验证 | 按阶段 2.2 派发 `trellis-check` 子智能体 |
| 卡住了 / 同一个 bug 修了多次 | `trellis-break-loop` |
| Spec 需要更新 | `trellis-update-spec` |

**为什么 `trellis-before-dev` 不在此表中**：写代码的不是你 — 是 `trellis-implement` 子智能体。子智能体平台通过 `implement.jsonl` 注入/序言获取 spec 上下文，而非通过主线程加载 `trellis-before-dev`。

[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi]

[codex-inline, Kilo, Antigravity, Windsurf]

| 用户意图 | Skill |
|---|---|
| 想要新功能 / 需求不明确 | `trellis-brainstorm` |
| 即将编写代码 / 开始实现 | `trellis-before-dev`（然后在主 session 中直接实现） |
| 编写完成 / 想要验证 | `trellis-check` |
| 卡住了 / 同一个 bug 修了多次 | `trellis-break-loop` |
| Spec 需要更新 | `trellis-update-spec` |

[/codex-inline, Kilo, Antigravity, Windsurf]

### 不要跳过技能

[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi]

| 你可能在想 | 为什么这是错的 |
|---|---|
| "这很简单，我直接在主线程里写代码就行" | 派发 `trellis-implement` 是代价最小的路径；跳过它会诱使你在主线程中写代码并丢失 spec 上下文 — 子智能体会被注入 `implement.jsonl`，你不会 |
| "我在规划模式中已经想清楚了" | 规划模式的输出存在于内存中 — 子智能体看不到；必须持久化到 prd.md |
| "我已经知道 spec 了" | Spec 可能在你上次读取后已更新；子智能体会获取最新副本，你可能不会 |
| "先写代码，稍后再检查" | `trellis-check` 会发现你自己注意不到的问题；越早检查代价越小 |

[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi]

[codex-inline, Kilo, Antigravity, Windsurf]

| 你可能在想 | 为什么这是错的 |
|---|---|
| "这很简单，直接写代码就行" | 简单的任务常常会变复杂；`trellis-before-dev` 不到一分钟就能加载你需要的 spec 上下文 |
| "我在规划模式中已经想清楚了" | 规划模式的输出存在于内存中 — 编码前必须持久化到 prd.md |
| "我已经知道 spec 了" | Spec 可能在你上次读取后已更新；重新读取 |
| "先写代码，稍后再检查" | `trellis-check` 会发现你自己注意不到的问题；越早检查代价越小 |

[/codex-inline, Kilo, Antigravity, Windsurf]

### 加载步骤详情

在每个步骤，运行以下命令获取详细指导：

```bash
py -3 ./.trellis/scripts/get_context.py --mode phase --step <step>
# 例如 py -3 ./.trellis/scripts/get_context.py --mode phase --step 1.1
```

---

## 阶段 1：规划

目标：弄清楚要构建什么，产出清晰的需求文档以及实现所需的上下文。

#### 1.0 创建 task `[required · once]`

创建 task 目录（status 进入 `planning`，当 session 身份可用时，session 活跃 task pointer 自动指向新 task）：

```bash
py -3 ./.trellis/scripts/task.py create "<task title>" --slug <name>
```

`--slug` 仅为人可读的名称。**不要**包含 `MM-DD-` 日期前缀；`task.py create` 会自动添加此前缀。

此命令成功后，每轮面包屑自动切换至 `[workflow-state:planning]`，告知 AI 进入头脑风暴 + JSONL 整理阶段。

⚠️ **这里只运行 `create` — 不要同时运行 `start`**。`start` 会将 status 翻转为 `in_progress`，这会在头脑风暴 + JSONL 完成之前将面包屑切换至实现阶段 — AI 会静默跳过它们。将 `start` 留到步骤 1.4，在 JSONL 整理完成后执行。

当 `py -3 ./.trellis/scripts/task.py current --source` 已指向一个 task 时跳过。

#### 1.1 需求探索 `[required · repeatable]`

加载 `trellis-brainstorm` 技能，按该技能的指导与用户交互式探索需求。

头脑风暴技能将引导你：
- 每次只问一个问题
- 优先研究而非询问用户
- 优先提供选项而非开放式问题
- 每次用户回答后立即更新 `prd.md`

当需求发生变化时返回此步骤并修订 `prd.md`。

#### 1.2 研究 `[optional · repeatable]`

研究可以在需求探索期间的任何时候进行。它不限于本地代码 — 你可以使用任何可用的工具（MCP 服务器、技能、网络搜索等）查阅外部信息，包括第三方库文档、行业实践、API 参考等。

[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi]

派发研究子智能体：

- **智能体类型**：`trellis-research`
- **任务描述**：研究 <具体问题>
- **关键要求**：研究输出**必须**持久化到 `{TASK_DIR}/research/`

[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi]

[codex-inline, Kilo, Antigravity, Windsurf]

在主 session 中直接进行研究，并将发现写入 `{TASK_DIR}/research/`。（对于 `codex-inline`，这避免了 `fork_turns="none"` 隔离导致 `trellis-research` 子智能体无法解析活跃 task 路径的问题。）

[/codex-inline, Kilo, Antigravity, Windsurf]

**研究产物的约定**：
- 每个研究主题一个文件（例如 `research/auth-library-comparison.md`）
- 在文件中记录第三方库使用示例、API 参考、版本约束
- 记下你发现的、供后续参考的相关 spec 文件路径

头脑风暴和研究可以自由交织 — 暂停来研究一个技术问题，然后返回与用户讨论。

**核心原则**：研究输出必须写入文件，而不能只留在聊天中。对话会被压缩；文件不会。

#### 1.3 配置上下文 `[required · once]`

[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi]

整理 `implement.jsonl` 和 `check.jsonl`，以便阶段 2 的子智能体获得正确的 spec 上下文。这些文件在 `task create` 时已预置了一条自描述的 `_example` 行；你在此处的任务是填入真实的条目。

**位置**：`{TASK_DIR}/implement.jsonl` 和 `{TASK_DIR}/check.jsonl`（已存在）。

**格式**：每行一个 JSON 对象 — `{"file": "<path>", "reason": "<why>"}`。路径相对于仓库根目录。

**应放入的内容**：
- **Spec 文件** — `.trellis/spec/<package>/<layer>/index.md` 以及与此 task 相关的任何具体指南文件（`error-handling.md`、`conventions.md` 等）
- **研究文件** — 子智能体需要参考的 `{TASK_DIR}/research/*.md`

**不应放入的内容**：
- 代码文件（`src/**`、`packages/**/*.ts` 等）— 这些由子智能体在实现时读取，不在此处预注册
- 你即将修改的文件 — 同样原因

**两个文件的分工**：
- `implement.jsonl` → implement 子智能体正确编写代码所需的 spec + 研究
- `check.jsonl` → check 子智能体的 spec（质量指南、检查惯例，以及需要时相同的研究资料）

**如何发现相关的 spec**：

```bash
py -3 ./.trellis/scripts/get_context.py --mode packages
```

列出每个 package 及其 spec layer 及路径。选择与此 task 领域匹配的条目。

**如何追加条目**：

可以直接在编辑器中编辑 JSONL 文件，或使用：

```bash
py -3 ./.trellis/scripts/task.py add-context "$TASK_DIR" implement "<path>" "<reason>"
py -3 ./.trellis/scripts/task.py add-context "$TASK_DIR" check "<path>" "<reason>"
```

在有真实条目后删除预置的 `_example` 行（可选 — 消费者会自动跳过它）。

跳过条件：`implement.jsonl` 已有 AI 整理的条目（仅有预置行不算）。

[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi]

[codex-inline, Kilo, Antigravity, Windsurf]

跳过此步骤。上下文由阶段 2 中的 `trellis-before-dev` 技能直接加载。

[/codex-inline, Kilo, Antigravity, Windsurf]

#### 1.4 激活 task `[required · once]`

一旦 prd.md 完成且 1.3 JSONL 整理完毕，将 task status 翻转为 `in_progress`：

```bash
py -3 ./.trellis/scripts/task.py start <task-dir>
```

此命令成功后，面包屑自动切换至 `[workflow-state:in_progress]`，后续按阶段 2 / 3 进行。

如果 `task.py start` 因 session 身份消息而报错（没有来自 hook 输入、`TRELLIS_CONTEXT_ID` 或平台原生 session 环境变量的 context key），请按照错误提示设置 session 身份，然后重试。

#### 1.5 完成标准

| 条件 | 必需 |
|------|:---:|
| `prd.md` 存在 | ✅ |
| 用户确认需求 | ✅ |
| `task.py start` 已运行（status = in_progress） | ✅ |
| `research/` 有产物（复杂任务） | 推荐 |
| `info.md` 技术设计（复杂任务） | 可选 |

[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi]

| `implement.jsonl` 有 AI 整理的条目（不仅仅是预置行） | ✅ |

[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi]

---

## 阶段 2：执行

目标：将 PRD 转化为通过质量检查的代码。

#### 2.1 实现 `[required · repeatable]`

[Claude Code, Cursor, OpenCode, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi]

派发 implement 子智能体：

- **智能体类型**：`trellis-implement`
- **任务描述**：按照 prd.md 实现需求，参考 `{TASK_DIR}/research/` 下的资料；完成后运行项目 lint 和 type-check
- **派发提示防护**：告知被派发的智能体它已经是 `trellis-implement` 子智能体，必须直接实现，不得再派发另一个 `trellis-implement` / `trellis-check`。

平台 hook/插件自动处理：
- 读取 `implement.jsonl` 并将引用的 spec 文件注入到智能体提示中
- 注入 prd.md 内容

[/Claude Code, Cursor, OpenCode, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi]

[codex-sub-agent]

派发 implement 子智能体：

- **智能体类型**：`trellis-implement`
- **任务描述**：按照 prd.md 实现需求，参考 `{TASK_DIR}/research/` 下的资料；完成后运行项目 lint 和 type-check
- **派发提示防护**：提示**必须**以 `Active task: <task path>` 开头，然后明确说明被派发的智能体已经是 `trellis-implement`，必须直接实现，不得派发另一个 `trellis-implement` / `trellis-check`。

Codex 子智能体定义自动处理上下文加载要求：
- 通过 `task.py current --source` 解析活跃 task，然后读取 `prd.md` 和 `info.md`（如果存在）
- 读取 `implement.jsonl` 并要求智能体在编码前加载每个引用的 spec 文件

[/codex-sub-agent]

[Kiro]

派发 implement 子智能体：

- **智能体类型**：`trellis-implement`
- **任务描述**：按照 prd.md 实现需求，参考 `{TASK_DIR}/research/` 下的资料；完成后运行项目 lint 和 type-check
- **派发提示防护**：告知被派发的智能体它已经是 `trellis-implement` 子智能体，必须直接实现，不得再派发另一个 `trellis-implement` / `trellis-check`。

平台序言自动处理上下文加载要求：
- 读取 `implement.jsonl` 并将引用的 spec 文件注入到智能体提示中
- 注入 prd.md 内容

[/Kiro]

[codex-inline, Kilo, Antigravity, Windsurf]

1. 加载 `trellis-before-dev` 技能读取项目指南
2. 读取 `{TASK_DIR}/prd.md` 了解需求
3. 参考 `{TASK_DIR}/research/` 下的资料
4. 按需求实现代码
5. 运行项目 lint 和 type-check

[/codex-inline, Kilo, Antigravity, Windsurf]

#### 2.2 质量检查 `[required · repeatable]`

[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi]

派发 check 子智能体：

- **智能体类型**：`trellis-check`
- **任务描述**：对照 spec 和 PRD 审查所有代码变更；直接修复发现的任何问题；确保 lint 和 type-check 通过
- **派发提示防护**：告知被派发的智能体它已经是 `trellis-check` 子智能体，必须直接审查/修复，不得派发另一个 `trellis-check` / `trellis-implement`。

check 智能体的职责：
- 对照 spec 审查代码变更
- 自动修复发现的问题
- 运行 lint 和 typecheck 进行验证

[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi]

[codex-inline, Kilo, Antigravity, Windsurf]

加载 `trellis-check` 技能并按指导验证代码：
- Spec 合规性
- lint / type-check / 测试
- 跨层一致性（当变更跨越多个 layer 时）

如果发现问题 → 修复 → 重新检查，直到通过。

[/codex-inline, Kilo, Antigravity, Windsurf]

#### 2.3 回滚 `[on demand]`

- `check` 发现 PRD 缺陷 → 返回阶段 1，修复 `prd.md`，然后重做 2.1
- 实现方向出错 → 还原代码，重做 2.1
- 需要更多研究 → 进行研究（同阶段 1.2），将发现写入 `research/`

---

## 阶段 3：完成

目标：确保代码质量，捕获经验教训，记录工作成果。

#### 3.1 质量验证 `[required · repeatable]`

加载 `trellis-check` 技能并进行最终验证：
- Spec 合规性
- lint / type-check / 测试
- 跨层一致性（当变更跨越多个 layer 时）

如果发现问题 → 修复 → 重新检查，直到通过。

#### 3.2 调试回顾 `[on demand]`

如果此 task 涉及反复调试（同一问题被修复了多次），加载 `trellis-break-loop` 技能：
- 对根因进行分类
- 解释为什么之前的修复失败了
- 提出预防措施

目标是将调试经验教训捕获下来，使同类问题不再重现。

#### 3.3 Spec 更新 `[required · once]`

加载 `trellis-update-spec` 技能，审视此 task 是否产出了值得记录的新知识：
- 新发现的 pattern 或 convention
- 遇到的陷阱
- 新的技术决策

据此更新 `.trellis/spec/` 下的文档。即使结论是"无需更新"，也要走完判断过程。

#### 3.4 提交更改 `[required · once]`

AI 主导此 task 代码变更的批量提交，以便 `/finish-work` 之后能干净地运行。目标：**先**产出工作提交，**然后**是记账类（归档 + 日志）提交 — 绝不交叉。

**逐步操作**：

1. **检查脏状态**：
   ```bash
   git status --porcelain
   ```
   快照所有脏路径。如果工作树是干净的，跳到 3.5。

2. **从最近历史中学习提交风格**（使草拟的消息与之一致）：
   ```bash
   git log --oneline -5
   ```
   注意前缀约定（`feat:` / `fix:` / `chore:` / `docs:` ...）、语言（中文/English）和长度风格。

3. **将脏文件分为两组**：
   - **本次 session 中 AI 编辑的** — 你在本次 session 中通过 Edit/Write/Bash 工具调用编写/编辑的文件。你知道改了什么、为什么改。
   - **未识别文件** — 你在本次 session 中**没有**接触过的脏文件（可能是用户的手动编辑、之前 session 遗留的 WIP 或无关工作）。**不要**悄悄包含它们。

4. **起草提交计划**。将 AI 编辑的文件分组为逻辑提交（每个连贯的变更单元一个提交，而非每个文件一个提交）。每项：`<提交消息>` + 文件列表。将未识别文件单独列在底部。

5. **一次性展示计划，请求一次性确认**。格式：
   ```
   建议的提交（按顺序）：
     1. <消息>
        - <文件>
        - <文件>
     2. <消息>
        - <文件>

   未识别脏文件（未纳入任何提交 — 请确认是否包含/排除）：
     - <文件>
     - <文件>

   回复 'ok' / '行' 执行。回复修改意见，或 '我自己来' / 'manual' 放弃。
   ```

6. **确认后**：按顺序对每批运行 `git add <files>` + `git commit -m "<msg>"`。不要 amend。不要 push。

7. **被拒绝时**（用户回复"不行" / "我自己来" / "manual" / 对计划的任何拒绝）：停止。不要尝试第二个计划。用户将手动提交；你确认后直接跳到 3.5。

**规则**：
- 任何地方都不得使用 `git commit --amend` — 三阶段三提交流程（工作提交 → 归档提交 → 日志提交）。
- 在此步骤中绝不推送到远程。
- 如果用户想要不同的消息措辞但接受文件分组，修改消息并重新确认一次 — 但如果他们拒绝分组，退出到手动模式。
- 批量计划是一次性提示；不要逐个提交提示。

#### 3.5 收尾提醒

完成以上步骤后，提醒用户可以运行 `/finish-work` 进行收尾（归档 task、记录 session）。

---

## 自定义 Trellis（针对分支版本）

本节面向想要修改 Trellis 工作流本身的开发者。所有自定义均通过编辑此文件完成；脚本仅作为解析器。

### 更改某个步骤的含义

编辑上文阶段 1 / 2 / 3 部分中对应步骤的详细说明。**关键约束**：如果你更改了步骤的 `[required · once]` 标记或添加了新的 `[required · once]` 步骤，你**必须**在该阶段的 `[workflow-state:STATUS]` 标签块中添加强制执行行 — 否则每轮面包屑会遗漏该强化信息，AI 会静默跳过该步骤。回归测试会对此进行断言。

所有 4 个标签块位于上文的 `## 阶段索引` 部分，紧接在每个阶段摘要之后：

| 作用域 | 对应标签 |
|---|---|
| 无活跃 task（阶段 1 之前） | `[workflow-state:no_task]`（在阶段索引 ASCII 图之后） |
| 整个阶段 1（task 已创建 → 准备实现） | `[workflow-state:planning]`（在阶段 1 摘要之后） |
| 阶段 2 + 阶段 3.1–3.4（实现 + 检查 + 收尾） | `[workflow-state:in_progress]`（在阶段 2 摘要之后） |
| 阶段 3.5 之后（已归档） | `[workflow-state:completed]`（在阶段 3 摘要之后；**当前已废弃**） |

### 更改每轮提示文本

直接编辑对应 `[workflow-state:STATUS]` 块的正文。编辑后，如果你是模板维护者则运行 `trellis update`，如果你在自定义自己的项目则重启 AI session — 无需修改脚本。

### 添加自定义 status

添加一个新块：

```
[workflow-state:my-status]
你的每轮提示文本
[/workflow-state:my-status]
```

约束：
- STATUS 字符集：`[A-Za-z0-9_-]+`（允许下划线和连字符，例如 `in-review`、`blocked-by-team`）
- 必须有一个 `lifecycle（生命周期）` hook 将 `task.json.status` 写入你的自定义值，否则标签永远不会被读取
- 生命周期 hook 位于 `task.json.hooks.after_*`，绑定到 `after_create / after_start / after_finish / after_archive` 之一

### 添加生命周期 hook

将 `hooks` 字段添加到你的 `task.json`：

```json
{
  "hooks": {
    "after_finish": [
      "your-script-or-command-here"
    ]
  }
}
```

支持的事件：`after_create / after_start / after_finish / after_archive`。注意 `after_finish` ≠ 状态变更（它只清除活跃 task pointer）；使用 `after_archive` 来触发"任务已完成"通知。

### 完整契约

关于工作流状态机的运行时契约、所有 status 写入器的位置、伪状态（`no_task` / `stale_<source_type>`）、hook 可达性矩阵以及其他深层细节，请参见：

- `.trellis/spec/cli/backend/workflow-state-contract.md` — 运行时契约 + 写入器表 + 测试不变量
- `.trellis/scripts/inject-workflow-state.py` — 实际解析器（仅读取 workflow.md，无嵌入文本）
