# 技能、命令、提示与工作流

技能和命令是用户与 Trellis 交互的文本入口点。不同平台使用不同的名称，但其核心目的相同：告诉 AI 在用户表达特定意图时如何进入 Trellis 流程。

## 概念差异

| 类型 | 触发方式 | 最适合 |
| --- | --- | --- |
| 技能 | AI 自动匹配或用户显式提及 | 长期能力、工作流规则、修改指南。 |
| 命令 | 用户显式调用 | 明确的操作入口点，如 continue 和 finish-work。 |
| 提示 | 用户显式调用或平台选择 | 与命令类似，但采用平台提示格式。 |
| 工作流 | 用户显式选择或平台自动匹配 | 在无子智能体/钩子时引导主会话。 |

Trellis 工作流技能通常共享一组语义：brainstorm、before-dev、check、update-spec、break-loop。`trellis-meta` 等多文件内置技能使用分层引用。

## 常见路径

| 平台 | 常见入口 |
| --- | --- |
| Claude Code | `.claude/skills/`、`.claude/commands/` |
| Cursor | `.cursor/skills/`、`.cursor/commands/` |
| OpenCode | `.opencode/skills/`、`.opencode/commands/` |
| Codex | `.agents/skills/`、`.codex/skills/` |
| Kilo | `.kilocode/skills/`、`.kilocode/workflows/` |
| Kiro | `.kiro/skills/` |
| Gemini CLI | `.agents/skills/`、`.gemini/commands/` |
| Antigravity | `.agent/skills/`、`.agent/workflows/` |
| Windsurf | `.windsurf/skills/`、`.windsurf/workflows/` |
| Qoder | `.qoder/skills/`、`.qoder/commands/` |
| CodeBuddy | `.codebuddy/skills/`、`.codebuddy/commands/` |
| GitHub Copilot | `.github/skills/`、`.github/prompts/` |
| Factory Droid | `.factory/skills/`、`.factory/commands/` |
| Pi Agent | `.pi/skills/` |

在用户项目中，以 init 实际生成的文件为准。

## 技能结构

常见的技能是一个目录：

```text
trellis-meta/
├── SKILL.md
└── references/
```

`SKILL.md` 应告诉 AI：

- 何时使用此技能。
- 对于当前任务首先阅读哪个参考文件。
- 不应做什么。

引用文件承载较长的说明，使入口文件不必包含所有内容。

## 命令/提示/工作流结构

命令、提示和工作流通常是单文件。其内容应包含：

- 何时使用。
- 需要读取哪些 `.trellis/` 文件。
- 需要运行哪些脚本。
- 完成后如何报告。

它们不应存储任务状态；任务状态属于 `.trellis/tasks/` 和 `.trellis/.runtime/`。

## 本地变更场景

| 用户需求 | 编辑位置 |
| --- | --- |
| 更改 AI 自动触发规则 | 对应技能的前置元数据描述。 |
| 更改用户命令行为 | 对应的命令/提示/工作流文件。 |
| 添加项目本地技能 | 平台技能目录，或共享的 `.agents/skills/`。 |
| 让多个平台共享一个能力 | 在每个平台技能目录中编写等效技能，或在支持此功能的平台上使用 `.agents/skills/` 共享层。 |
| 更改 finish/continue 入口点 | 平台命令/提示/工作流。 |

## 修改原则

1. **入口文件保持简短；引用承载长内容**。这对 `trellis-meta` 等多文件技能尤为重要。
2. **使触发描述具体明确**。过于宽泛的描述可能导致误触发；过于狭窄的描述可能不会触发。
3. **保持跨平台语义一致**。文件格式可以不同，但行为描述应一致。
4. **将项目专属能力放在本地技能中**。不要将团队私有流程放入公共的 `trellis-meta`。

如果用户只想让本地 AI 多了解一条项目规则，通常应创建项目本地技能或更新 `.trellis/spec/`，而非修改 Trellis 内置的工作流技能。
