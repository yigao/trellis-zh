# 钩子与设置

钩子（hook）/设置是连接平台与 Trellis 的入口层。它们决定平台在哪些事件上运行哪些脚本、插件或扩展。

## 设置的职责

设置/配置文件通常注册：

- session-start 钩子：在新的会话启动或上下文重置时注入 Trellis 概览。
- workflow-state 钩子：解析 `.trellis/workflow.md` 中的 `[workflow-state:STATUS]` 块，并在每次用户输入时输出与当前任务 `status` 匹配的正文。仅做解析；脚本不嵌入回退内容。
- sub-agent context 钩子：在实现/检查/研究智能体启动时注入任务上下文。
- shell/session bridge：让 shell 命令看到相同的 Trellis 会话标识。
- 平台插件或扩展入口点。

常见文件：

| 平台 | 设置/配置 |
| --- | --- |
| Claude Code | `.claude/settings.json` |
| Cursor | `.cursor/hooks.json` |
| Codex | `.codex/hooks.json`、`.codex/config.toml` |
| OpenCode | `.opencode/package.json`、`.opencode/plugins/*` |
| Kiro | `.kiro/hooks/` + 平台配置 |
| Gemini CLI | `.gemini/settings.json` |
| Qoder | `.qoder/settings.json` |
| CodeBuddy | `.codebuddy/settings.json` |
| GitHub Copilot | `.github/copilot/hooks.json` |
| Factory Droid | `.factory/settings.json` |
| Pi Agent | `.pi/settings.json`、`.pi/extensions/trellis/` |

这些文件在项目中是否存在取决于用户运行了哪些 `trellis init --<platform>` 标志。

## 钩子脚本类型

| 脚本 | 用途 |
| --- | --- |
| `session-start.py` | 生成 session-start 上下文。 |
| `inject-workflow-state.py` | 解析 `.trellis/workflow.md` 中的 `[workflow-state:STATUS]` 块，输出与当前任务状态匹配的正文。当没有匹配的块时回退到 `Refer to workflow.md for current step.`。 |
| `inject-subagent-context.py` | 将 PRD、JSONL 上下文及相关规范/研究注入子智能体。 |
| `inject-shell-session-context.py` | 让 shell 命令继承 Trellis 会话标识。 |

并非每个平台都有每种钩子。不要因为某个平台缺少钩子就从其他平台复制文件；首先确认该平台是否支持对应的事件。

## 本地变更场景

| 用户需求 | 编辑位置 |
| --- | --- |
| AI 在新会话中应看到更多/更少的上下文 | 平台的 `session-start` 钩子。 |
| 每回合提示策略应更改 | `.trellis/workflow.md` 中的 `[workflow-state:STATUS]` 块。钩子逐字解析 workflow.md——无需编辑脚本。 |
| 子智能体无法读取 PRD/规范 | `inject-subagent-context` 钩子或智能体序言。 |
| `task.py current` 在 shell 中没有活动任务 | shell/session bridge 钩子或平台环境变量配置。 |
| 禁用自动注入 | 设置/配置中对应的钩子注册项。 |

## 修改原则

1. **设置负责接线；钩子定义行为**。如果只修改了钩子，平台可能永远不会调用它。如果只修改了设置，行为可能不会改变。
2. **首先确认平台事件名称**。不同平台对 SessionStart、UserPromptSubmit、AgentSpawn、shell 执行等事件使用不同的名称。
3. **钩子读取本地 `.trellis/`，而非上游源代码**。用户项目中的 `.trellis/scripts/` 和 `.trellis/workflow.md` 是默认目标。
4. **错误必须可见**。钩子失败时应告知用户什么未被注入，而非让 AI 在缺少上下文的情况下静默继续。

## 故障排查路径

如果用户反馈"AI 没有读取 Trellis 状态"：

1. 检查平台设置是否注册了该钩子。
2. 检查钩子文件是否存在。
3. 手动运行钩子所依赖的 `.trellis/scripts/get_context.py` 或 `task.py current --source` 命令。
4. 检查 `.trellis/.runtime/sessions/` 中是否存在活动任务状态。
5. 检查平台 shell 是否传递了会话标识。
