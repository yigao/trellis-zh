# 更改本地上下文加载

context（上下文）加载决定了 AI 何时读取 workflow、task、spec、research、workspace 和 git 状态。当用户说"AI 不知道当前任务"、"agent 没有读取 spec"或"上下文太多/太少"时，请阅读本页。

## 首先读取这些文件

1. `.trellis/workflow.md`
2. `.trellis/scripts/get_context.py`
3. `.trellis/scripts/common/session_context.py`
4. `.trellis/scripts/common/task_context.py`
5. `.trellis/scripts/common/active_task.py`
6. 当前平台的 hook 或 agent 文件
7. 当前 task 的 `implement.jsonl` / `check.jsonl`

## 上下文来源

| 来源 | 用途 |
| --- | --- |
| `.trellis/workflow.md` | 工作流和下一步提示。 |
| `.trellis/tasks/<task>/prd.md` | 当前任务需求。 |
| `.trellis/tasks/<task>/implement.jsonl` | implement 前要读取的 spec/research。 |
| `.trellis/tasks/<task>/check.jsonl` | check 期间要读取的 spec/research。 |
| `.trellis/spec/` | 项目 spec。 |
| `.trellis/workspace/` | session 记录。 |
| git status | 当前工作树变更。 |

## 常见需求与编辑点

| 需求 | 编辑点 |
| --- | --- |
| 在新 session 中注入更多/更少信息 | `session_context.py` 或平台 `session-start` hook。 |
| 更改每次用户输入时的提示 | `.trellis/workflow.md` 中的 `[workflow-state:STATUS]` 块。`inject-workflow-state` hook 仅做解析，逐字读取该块。 |
| Agent 未读取 spec | Task JSONL、agent 前导部分、`inject-subagent-context` hook。 |
| 活动 task 丢失 | `active_task.py` 和平台 session 身份传播。 |
| 更改 JSONL 验证规则 | `task_context.py`。 |

## JSONL 规则

`implement.jsonl` / `check.jsonl` 是关键的 context 加载接口：

```jsonl
{"file": ".trellis/spec/backend/index.md", "reason": "Backend conventions"}
{"file": ".trellis/tasks/04-28-x/research/api.md", "reason": "API research"}
```

仅包含 spec/research 文件。不要将将要被修改的代码文件放入这些清单；agent 会在 implement 过程中自行读取代码文件。

## 更改 session 上下文

如果用户希望每个新 session 都能看到更多项目状态，编辑：

- `.trellis/scripts/common/session_context.py`
- 相应的平台 `session-start` hook

上下文不能无限制增长。优先注入索引和路径，以便 AI 按需读取详细文件。

## 更改 sub-agent 上下文

首先确定平台使用哪种模式：

- hook 推送：编辑 `inject-subagent-context` hook。
- agent 拉取：编辑相应 `trellis-implement` / `trellis-check` agent 文件中的读取步骤。

无论哪种模式，确保 agent 最终读取：

1. 活动 task
2. `prd.md`
3. `info.md`（如果存在）
4. 对应的 JSONL
5. JSONL 引用的 spec/research

## 排查顺序

```bash
py -3 ./.trellis/scripts/task.py current --source
py -3 ./.trellis/scripts/task.py list-context <task>
py -3 ./.trellis/scripts/task.py validate <task>
py -3 ./.trellis/scripts/get_context.py --mode packages
```

在编辑 hook/agent 之前，先确认 task 和 JSONL 是否正确。
