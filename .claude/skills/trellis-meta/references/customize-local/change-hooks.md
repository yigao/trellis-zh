# 更改本地 hook（钩子）

Hook 是连接平台与 Trellis 的自动化层。当用户想要更改"何时注入上下文"、"shell 命令如何继承 session"或"agent 启动前读取哪些文件"时，hook 通常是编辑点。

## 首先读取这些文件

1. 目标平台设置/配置，如 `.claude/settings.json`、`.codex/hooks.json`、`.cursor/hooks.json`
2. 目标平台 hook 目录
3. `.trellis/scripts/common/active_task.py`
4. `.trellis/scripts/common/session_context.py`
5. `.trellis/workflow.md`

## 常见 Hook 类型

| Hook | 用途 |
| --- | --- |
| session-start | 在 session 启动、清除或压缩时注入 Trellis 概览。 |
| workflow-state | 在每次用户输入时注入状态提示。 |
| sub-agent context | 在 agent 启动前注入 PRD/spec/research。 |
| shell session bridge | 让 shell 中的 `task.py` 命令能看到相同的 session 身份。 |

## 修改步骤

1. 在设置/配置中找到 hook 注册。
2. 确认注册的脚本路径存在。
3. 读取 hook 脚本，识别输入、输出和所调用的 `.trellis/scripts/`。
4. 修改 hook 行为。
5. 如果 hook 依赖 workflow 内容，同步 `.trellis/workflow.md`。

## 示例：更改新 session 注入内容

首先找到 session-start hook：

```text
.claude/settings.json
.claude/hooks/session-start.py
```

如果 hook 最终调用 `.trellis/scripts/get_context.py` 或 `session_context.py`，编辑本地脚本通常比在 hook 中硬编码内容更稳健。

## 示例：Agent 未读取 JSONL

首先确认：

```bash
py -3 ./.trellis/scripts/task.py current --source
py -3 ./.trellis/scripts/task.py validate <task>
```

如果 task 和 JSONL 正确，确定平台使用 hook 推送还是 agent 拉取模式。对于 hook 推送，编辑 `inject-subagent-context`；对于 agent 拉取，编辑 agent 文件。

## 注意事项

- 设置负责注册，hook 脚本负责行为；两者需一起检查。
- 不同平台支持不同的 hook 事件。不要直接复制另一个平台的设置。
- Hook 应读取项目本地的 `.trellis/`；不应依赖 Trellis 上游源路径。
- Hook 失败应产生可见的错误，以便 AI 不会静默丢失 context。
