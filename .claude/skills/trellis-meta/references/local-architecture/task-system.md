# 本地任务系统

Trellis 任务系统（task system）完全存储在用户项目的 `.trellis/tasks/` 下。每个任务是一个目录，包含需求、上下文、研究、状态和关系信息。

## 任务目录结构

```text
.trellis/tasks/
├── 04-28-example-task/
│   ├── task.json
│   ├── prd.md
│   ├── info.md
│   ├── implement.jsonl
│   ├── check.jsonl
│   └── research/
└── archive/
    └── 2026-04/
```

| 文件 | 用途 |
| --- | --- |
| `task.json` | 任务元数据：状态、负责人、优先级、分支（branch）、父/子任务等字段。 |
| `prd.md` | 需求文档；实现期间最重要的业务上下文。 |
| `info.md` | 可选的技术设计。 |
| `implement.jsonl` | 实现智能体必须首先读取的规范/研究文件列表。 |
| `check.jsonl` | 检查智能体必须首先读取的规范/研究文件列表。 |
| `research/` | 研究产物。复杂的研究结论不应只存在于聊天中。 |

## `task.json`

`task.json` 记录任务状态和元数据。常用字段：

| 字段 | 含义 |
| --- | --- |
| `id` / `name` / `title` | 任务标识和标题。 |
| `status` | 状态，如 `planning`、`in_progress`、`review` 或 `completed`。 |
| `priority` | `P0`、`P1`、`P2`、`P3`。 |
| `creator` / `assignee` | 创建者和负责人。 |
| `package` | monorepo 中的目标软件包；可为空。 |
| `branch` / `base_branch` | 工作分支和 PR 目标分支。 |
| `children` / `parent` | 父/子任务关系。 |
| `commit` / `pr_url` | 完成后的提交（commit）和 PR 信息。 |
| `meta` | 扩展字段。 |

AI 不应将阶段编号视为任务状态。任务进度主要由 `status`、`prd.md`、JSONL 上下文是否已配置以及 `workflow.md` 中的阶段描述决定。

## 活动任务

用户看到的是"当前任务"，但 Trellis 按会话存储活动任务状态。

```text
.trellis/.runtime/sessions/<context-key>.json
```

`task.py start` 将任务路径写入当前会话的运行时会话文件。`task.py current --source` 显示当前任务及其来源。不同的 AI 窗口可以指向不同的任务而不会相互覆盖。

如果平台或 shell 环境没有稳定的会话标识，`task.py start` 可能无法设置活动任务。AI 应阅读错误信息，检查平台钩子/会话环境，而非回退到共享的全局指针。

## JSONL 上下文

`implement.jsonl` 和 `check.jsonl` 是子智能体首先读取的上下文清单。

格式：

```jsonl
{"file": ".trellis/spec/cli/backend/index.md", "reason": "Backend conventions"}
{"file": ".trellis/tasks/04-28-example/research/api.md", "reason": "API research"}
```

规则：

- 包含规范和研究文件。
- 不要包含即将被修改的代码文件。
- 不要将聊天中的临时结论作为唯一上下文。
- 种子行没有 `file` 字段；它们仅提示 AI 填入实际条目。

## 常用命令

```bash
py -3 ./.trellis/scripts/task.py create "<title>" --slug <slug>
py -3 ./.trellis/scripts/task.py start <task>
py -3 ./.trellis/scripts/task.py current --source
py -3 ./.trellis/scripts/task.py add-context <task> implement <file> <reason>
py -3 ./.trellis/scripts/task.py validate <task>
py -3 ./.trellis/scripts/task.py finish
py -3 ./.trellis/scripts/task.py archive <task>
```

修改任务系统时，AI 应优先使用脚本命令来维护结构。仅在脚本无法满足需求时才直接编辑 JSON/Markdown。

## 本地定制点

| 需求 | 编辑位置 |
| --- | --- |
| 更改默认任务模板 | `.trellis/scripts/common/task_store.py` 和任务创建说明。 |
| 更改状态语义 | `.trellis/workflow.md`、workflow-state 钩子逻辑和任务使用惯例。 |
| 添加任务生命周期操作 | `.trellis/config.yaml` 中的 `hooks.after_*`。 |
| 更改上下文规则 | `.trellis/workflow.md` 中的阶段 1.3 以及相关平台智能体/钩子说明。 |
| 更改归档策略 | `.trellis/scripts/common/task_store.py` / `task_utils.py`。 |

这些是用户项目中的本地文件。除非用户想要向上游贡献，否则不要默认编辑 Trellis CLI 源代码。
