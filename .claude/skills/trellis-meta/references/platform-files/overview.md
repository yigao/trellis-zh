# 平台文件概览

Trellis 将相同的本地架构（architecture）连接到不同的 AI 工具。`.trellis/` 存储共享运行时；平台目录存储适配器文件，定义每个 AI 工具如何进入 Trellis。

当本地 AI 修改 Trellis 时，应首先区分两类文件：

- **共享文件**：`.trellis/workflow.md`、`.trellis/tasks/`、`.trellis/spec/`、`.trellis/scripts/`。
- **平台文件**：`.claude/`、`.codex/`、`.cursor/`、`.opencode/`、`.kiro/`、`.gemini/`、`.qoder/`、`.codebuddy/`、`.github/`、`.factory/`、`.pi/`、`.kilocode/`、`.agent/`、`.windsurf/` 及类似目录。

平台文件不存储业务状态。它们让对应的 AI 工具读取 Trellis 状态、调用 Trellis 脚本并加载 Trellis 技能/智能体/钩子。

## 平台文件类别

| 类别 | 常见路径 | 用途 |
| --- | --- | --- |
| 设置/配置 | `.claude/settings.json`、`.codex/hooks.json`、`.qoder/settings.json` | 注册钩子、插件、扩展或平台行为。 |
| 钩子/插件/扩展 | `.claude/hooks/`、`.opencode/plugins/`、`.pi/extensions/` | 在会话启动、用户输入、智能体启动、shell 执行等事件时注入上下文。 |
| 智能体 | `.claude/agents/`、`.codex/agents/`、`.kiro/agents/` | 定义 `trellis-research`、`trellis-implement` 和 `trellis-check`。 |
| 技能 | `.claude/skills/`、`.agents/skills/`、`.qoder/skills/` | 可自动触发或按需读取的能力描述。 |
| 命令/提示/工作流 | `.cursor/commands/`、`.github/prompts/`、`.windsurf/workflows/` | 用户显式调用的入口点。 |

## 三种平台集成模式

### 1. 钩子/扩展驱动

这些平台可以在特定事件上触发脚本或插件，并主动将 Trellis 上下文注入 AI。

常见能力：

- session-start 注入 `.trellis/` 概览。
- 每个用户回合的 workflow-state 提示。
- 子智能体启动时的 PRD/规范/研究注入。
- Shell 命令继承会话标识。

要更改"AI 何时知道什么"，首先检查钩子/插件/扩展和设置。

### 2. 智能体序言/拉取式

某些平台无法可靠地让钩子重写子智能体提示，因此智能体文件本身指示智能体在启动后读取活动任务、PRD 和 JSONL 上下文。

要更改子智能体加载上下文的方式，检查智能体文件本身。

### 3. 主会话工作流

某些平台没有 Trellis 子智能体或钩子能力。它们依赖工作流/技能/命令来引导主会话 AI 读取文件、运行脚本并推进任务。

要更改行为，检查平台工作流/技能/命令和 `.trellis/workflow.md`。

## 本地修改顺序

当用户要求为某个平台定制行为时，AI 应按以下顺序检查文件：

1. 读取 `.trellis/workflow.md` 确认共享流程。
2. 读取目标平台的设置/配置，查看注册了哪些钩子/智能体/技能/命令。
3. 读取目标平台的智能体/技能/命令/钩子。
4. 修改最接近用户需求的本地文件。
5. 如果变更影响共享流程，同步 `.trellis/workflow.md` 或 `.trellis/spec/`。

不要只修改平台文件而忘记共享工作流。不要只修改 `.trellis/workflow.md` 而忘记平台入口点可能仍包含旧的描述。
