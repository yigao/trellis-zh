# 更改本地 task lifecycle（任务生命周期）

Task lifecycle 包括创建、启动、上下文配置、完成、归档、父/子任务以及生命周期 hook。默认的自定义目标是 `.trellis/tasks/`、`.trellis/config.yaml` 和 `.trellis/scripts/`。

## 首先读取这些文件

1. `.trellis/workflow.md`
2. `.trellis/config.yaml`
3. `.trellis/scripts/task.py`
4. `.trellis/scripts/common/task_store.py`
5. `.trellis/scripts/common/task_utils.py`
6. 当前 task 的 `.trellis/tasks/<task>/task.json`

## 常见需求与编辑点

| 需求 | 编辑点 |
| --- | --- |
| 在 task 创建后自动同步外部系统 | `.trellis/config.yaml` 中的 `hooks.after_create`。 |
| 在 task 启动后自动更新状态 | `.trellis/config.yaml` 中的 `hooks.after_start`。 |
| 在 task 完成后运行脚本 | `.trellis/config.yaml` 中的 `hooks.after_finish`。 |
| 归档后清理外部资源 | `.trellis/config.yaml` 中的 `hooks.after_archive`。 |
| 更改默认 task 字段 | `.trellis/scripts/common/task_store.py`。 |
| 更改 task 解析/搜索 | `.trellis/scripts/common/task_utils.py`。 |
| 更改活动 task 行为 | `.trellis/scripts/common/active_task.py`。 |

## lifecycle hook

`.trellis/config.yaml` 支持：

```yaml
hooks:
  after_create:
    - "py -3 .trellis/scripts/hooks/my_sync.py create"
  after_start:
    - "py -3 .trellis/scripts/hooks/my_sync.py start"
  after_finish:
    - "py -3 .trellis/scripts/hooks/my_sync.py finish"
  after_archive:
    - "py -3 .trellis/scripts/hooks/my_sync.py archive"
```

Hook 命令会收到 `TASK_JSON_PATH` 环境变量，指向当前 task 的 `task.json`。Hook 失败通常应发出警告，但不应阻塞主 task 操作。

## 更改 task 字段

如果用户想要添加项目本地字段，最好将它们放在 `task.json` 的 `meta` 下，以避免破坏现有脚本对标准字段的假设。

示例：

```json
"meta": {
  "linearIssue": "ENG-123",
  "risk": "high"
}
```

如果确实需要更改标准字段，请检查每个读取 `task.json` 的本地脚本。

## 更改活动 task

活动 task 是存储在 `.trellis/.runtime/sessions/` 中的 session 级别状态。不要回退到全局 `.current-task` 模型。如果用户想要更改活动 task 行为，编辑：

- `.trellis/scripts/common/active_task.py`
- 平台 hook 或 shell session bridge
- `.trellis/workflow.md` 中的活动 task 描述

### `task.py create` 设置活动指针

`.trellis/scripts/common/task_store.py` 中的 `cmd_create` 在写入新 task 目录后立即尽力调用 `set_active_task`。其行为如下：

- 当调用 shell 携带 session 身份（`TRELLIS_CONTEXT_ID` 环境变量，或 `resolve_context_key` 能识别的任何平台特定 session 环境变量——参见 `active_task.py:_ENV_SESSION_KEYS`）时，`.trellis/.runtime/sessions/<context_key>.json` 中的每 session 指针会被重写以指向新 task。task 的 `status=planning`，并且 `[workflow-state:planning]` 会在下一个 `UserPromptSubmit` 时立即触发。
- 当 session 身份不可用时（在 AI session 之外的原始 CLI 调用，或平台不将身份传播到 shell），task 目录仍会被创建且 `status=planning` 仍会被写入，但活动指针保持不变。用户可以在回到 AI session 后使用 `task.py start <dir>` 来附加该 task。

这使得 `[workflow-state:planning]` 成为 `task.py create` 之后的 brainstorm（头脑风暴）和 JSONL 整理工作期间的实时面包屑导航。R7 之前的行为在 `task.py start` 之前将面包屑停留在 `no_task` 上，因此 planning 块实际上是死文本。

如果你 fork `task.py` 以添加新的创建路径（例如绕过 `cmd_create` 的外部导入），请检查你的路径是否也调用了 `set_active_task`。如果没有该调用，你创建的任务将不会显示为活动任务。完整的状态写入表位于 `.trellis/spec/cli/backend/workflow-state-contract.md`。

## 修改步骤

1. 使用 `py -3 ./.trellis/scripts/task.py current --source` 确认当前 task。
2. 读取当前 task 的 `task.json` 并确认状态和字段。
3. 对于配置需求，首先编辑 `.trellis/config.yaml`。
4. 对于脚本行为需求，然后编辑 `.trellis/scripts/`。
5. 如果 AI 流程变更，同步 `.trellis/workflow.md`。

## 不要做的事

- 不要直接编辑 `.trellis/.runtime/sessions/` 来"修复"业务状态。
- 不要将项目私有字段硬编码到脚本中；优先使用 `meta`。
- 不要默认建议用户 fork Trellis CLI。
