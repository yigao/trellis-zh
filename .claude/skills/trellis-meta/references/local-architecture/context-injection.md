# 本地上下文注入系统

Trellis 上下文注入（context injection）的目标是让 AI 在正确的时间读取正确的文件，而非依赖模型记忆。在用户项目中，注入由 `.trellis/` 脚本与平台钩子（hook）、智能体（agent）和技能（skill）共同实现。

## 注入的上下文类型

| 类型 | 来源 | 用途 |
| --- | --- | --- |
| 会话上下文 | `.trellis/scripts/get_context.py` | 当前开发者、git 状态、活动任务、活跃任务列表、日志、软件包。 |
| 工作流上下文 | `.trellis/workflow.md` | 当前 Trellis 流程和下一步操作。 |
| 规范上下文 | `.trellis/spec/` + 任务 JSONL | 实现（implement）/检查（check）期间必须遵循的规范。 |
| 任务上下文 | `.trellis/tasks/<task>/prd.md`、`info.md`、`research/` | 当前任务的需求、设计和研究。 |
| 平台上下文 | 平台钩子/设置/智能体 | 让不同 AI 工具通过各自机制读取上述文件。 |

## session-start

支持 session-start 的平台在会话（session）启动、清除、压缩或收到类似事件时注入 Trellis 概览。注入的内容通常包括：

- 工作流摘要。
- 当前任务状态。
- 活跃任务。
- 规范索引路径。
- 开发者身份和 git 状态。

如果用户觉得在新会话中 AI 不知道当前任务，首先检查平台的 session-start 钩子或等效机制是否已安装并正常运行。

## workflow-state

workflow-state 是在每个用户回合前后注入的轻量级提示。根据当前任务状态，它从 `.trellis/workflow.md` 中选择一个块，例如 `no_task`、`planning`、`in_progress` 或 `completed`。

如果用户想要更改"在给定状态下 AI 接下来应该做什么"，首先编辑 `.trellis/workflow.md` 中对应的状态块。

## 子智能体上下文

实现和检查智能体需要任务上下文。Trellis 有两种加载模式：

1. **hook push**：平台钩子在智能体启动前注入 `prd.md` 和 `implement.jsonl` / `check.jsonl` 引用的文件。
2. **agent pull**：智能体定义指示智能体在启动后读取活动任务、PRD 和 JSONL 上下文。

在两种模式下，任务目录中的 JSONL 文件是关键接口。

## JSONL 读取规则

`implement.jsonl` 和 `check.jsonl` 每行包含一个 JSON 对象：

```jsonl
{"file": ".trellis/spec/backend/index.md", "reason": "Backend rules"}
```

读取器应跳过没有 `file` 字段的种子行。配置 JSONL 时，AI 应仅包含规范/研究文件，不要预先注册将要被修改的代码文件。

## 活动任务与上下文键

活动任务状态位于 `.trellis/.runtime/sessions/` 中，并按会话隔离。钩子尝试从平台事件、环境变量、转录路径或 `TRELLIS_CONTEXT_ID` 解析上下文键。

如果 shell 命令无法看到相同的上下文键，`task.py current --source` 可能报告没有活动任务。此时应检查平台是否将会话标识传递到 shell 中，而不是手写一个全局的 current-task 文件。

## 本地定制点

| 需求 | 编辑位置 |
| --- | --- |
| 更改 session-start 注入的内容 | 平台的 `session-start` 钩子或插件文件。 |
| 更改每回合 workflow-state 规则 | `.trellis/workflow.md` 中的 `[workflow-state:STATUS]` 块。平台的 workflow-state 钩子逐字解析这些块，不嵌入回退文本。 |
| 更改子智能体读取上下文的方式 | 平台智能体定义、`inject-subagent-context` 钩子或智能体序言。 |
| 更改 JSONL 验证/显示 | `.trellis/scripts/common/task_context.py`。 |
| 更改活动任务解析 | `.trellis/scripts/common/active_task.py`。 |

修改上下文注入时，验证两件事：新会话能否看到正确的任务，子智能体能否看到正确的 PRD/规范/研究。
