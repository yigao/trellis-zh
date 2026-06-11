# 更改本地 workflow（工作流）

当用户想要更改 Trellis phase（阶段）、下一步提示、是否创建 task、是否使用 sub-agent 或何时 check/wrap up 时，首先编辑 `.trellis/workflow.md`。

## 首先读取这些文件

1. `.trellis/workflow.md`
2. 当前平台的入口文件，如 skills/commands/prompts/workflows
3. 当前 task 的 `task.json` 和 `prd.md`

## 常见需求与编辑点

| 需求 | 编辑点 |
| --- | --- |
| 更改 phase 名称或 phase 顺序 | `Phase Index` 和相应的 Phase 部分。 |
| 更改没有 task 时是否创建 task | `[workflow-state:no_task]` 状态块。 |
| 更改 planning 期间的下一步 | Phase 1 和 `[workflow-state:planning]`。 |
| 更改 in_progress 期间是否需要 agent | Phase 2 和 `[workflow-state:in_progress]`。 |
| 更改完成后的 wrap-up | Phase 3 和 `[workflow-state:completed]`。 |
| 更改用户意图触发哪个 skill | `Skill Routing` 表格。 |

## 修改步骤

1. 找到 `.trellis/workflow.md` 中的相关部分。
2. 更改规则时，保持明确的触发条件和后续操作。
3. 如果添加或重命名 skill/agent，同步平台目录中的相应文件。
4. Workflow-state 变更只需编辑 `.trellis/workflow.md` 中的 `[workflow-state:STATUS]` 块。hook 仅做解析——它会逐字读取你放在块中的内容。保持开始和结束标签的 STATUS 字符串一致（`[workflow-state:foo]…[/workflow-state:foo]`）；不匹配的 STATUS 对会被静默丢弃。
5. 让 AI 重新读取 `.trellis/workflow.md`；不要继续使用旧对话中的规则。

## 示例：放宽 task 创建要求

要更改何时可以跳过 task 创建，通常编辑 `[workflow-state:no_task]`：

```md
[workflow-state:no_task]
Task is not required when the answer is a one-reply explanation, no files are changed, and no research is needed.
[/workflow-state:no_task]
```

如果正式的 Phase 1 流程也需要更改，同步 Phase 1 部分。

## 示例：某个平台不使用 sub-agent

如果用户希望仅一个平台避免使用 sub-agent，首先确认该平台在 workflow 中是否有独立的分组。然后为该平台分组更改 Phase 2 路由，而不是跨平台删除所有 `trellis-implement` / `trellis-check` 指令。

## `/trellis:continue` 路由表

`/trellis:continue` 通过决定接下来加载哪个 phase 步骤来恢复 task。该决策结合了 `task.json.status` 与 task 目录中是否存在工件。映射关系固定在 command 本身中；添加了自定义状态的 fork 必须同时扩展 workflow.md 标签块和此路由表。

| `status` | 工件状态 | 恢复到 |
| --- | --- | --- |
| `planning` | `prd.md` 缺失 | Phase 1.1（加载 `trellis-brainstorm`） |
| `planning` | `prd.md` 存在，`implement.jsonl` 仅有种子 `_example` 行 | Phase 1.3（整理 JSONL 上下文） |
| `planning` | `prd.md` 存在，`implement.jsonl` 已整理 | Phase 1.4（运行 `task.py start`） |
| `in_progress` | 对话历史中没有实现 | Phase 2.1（`trellis-implement`） |
| `in_progress` | 实现完成，未运行 `trellis-check` | Phase 2.2（`trellis-check`） |
| `in_progress` | check 通过 | Phase 3.1（验证质量 + spec 更新） |
| `completed` | task 仍在活动树中 | Phase 3.5（运行 `/trellis:finish-work` 进行归档） |

当你添加自定义状态（例如 `in-review`）时，在 `.trellis/workflow.md` 中添加一个 `[workflow-state:in-review]` 块用于每轮面包屑导航，并扩展此路由表——通常通过编辑 `/trellis:continue` command 文件（`.{platform}/commands/trellis/continue.md` 或等效文件）以添加一行决定从何处恢复。没有路由条目，`/trellis:continue` 将落入默认分支，用户将不会到达你预期的步骤。

## 注意事项

`.trellis/workflow.md` 是本地项目工作流，而非不可变的 template（模板）。用户可以根据团队习惯进行调整。编辑后，平台入口文件可能仍包含旧描述，因此也要检查它们。
