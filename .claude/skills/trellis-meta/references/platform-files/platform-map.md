# 平台文件映射

本页列出用户项目中按平台划分的常见 Trellis 文件位置。平台目录是否存在于实际项目中取决于用户运行了哪些 `trellis init --<platform>` 命令。

## 矩阵

| 平台 | CLI 标志 | 主目录 | 技能目录 | 智能体目录 | 钩子/扩展 |
| --- | --- | --- | --- | --- | --- |
| Claude Code | `--claude` | `.claude/` | `.claude/skills/` | `.claude/agents/` | `.claude/hooks/` + `.claude/settings.json` |
| Cursor | `--cursor` | `.cursor/` | `.cursor/skills/` | `.cursor/agents/` | `.cursor/hooks.json` + `.cursor/hooks/` |
| OpenCode | `--opencode` | `.opencode/` | `.opencode/skills/` | `.opencode/agents/` | `.opencode/plugins/` |
| Codex | `--codex` | `.codex/` | `.agents/skills/` | `.codex/agents/` | `.codex/hooks/` + `.codex/hooks.json` |
| Kilo | `--kilo` | `.kilocode/` | `.kilocode/skills/` | 通常无 | `.kilocode/workflows/` |
| Kiro | `--kiro` | `.kiro/` | `.kiro/skills/` | `.kiro/agents/` | `.kiro/hooks/` |
| Gemini CLI | `--gemini` | `.gemini/` | `.agents/skills/` | `.gemini/agents/` | `.gemini/settings.json` + `.gemini/hooks/` |
| Antigravity | `--antigravity` | `.agent/` | `.agent/skills/` | 通常无 | `.agent/workflows/` |
| Windsurf | `--windsurf` | `.windsurf/` | `.windsurf/skills/` | 通常无 | `.windsurf/workflows/` |
| Qoder | `--qoder` | `.qoder/` | `.qoder/skills/` | `.qoder/agents/` | `.qoder/hooks/` + `.qoder/settings.json` |
| CodeBuddy | `--codebuddy` | `.codebuddy/` | `.codebuddy/skills/` | `.codebuddy/agents/` | `.codebuddy/hooks/` + `.codebuddy/settings.json` |
| GitHub Copilot | `--copilot` | `.github/` | `.github/skills/` | `.github/agents/` | `.github/copilot/hooks/` + prompts |
| Factory Droid | `--droid` | `.factory/` | `.factory/skills/` | `.factory/droids/` | `.factory/hooks/` + settings |
| Pi Agent | `--pi` | `.pi/` | `.pi/skills/` | `.pi/agents/` | `.pi/extensions/trellis/` + `.pi/settings.json` |

## 能力分组

### Trellis 子智能体支持

以下平台通常有 `trellis-research`、`trellis-implement` 和 `trellis-check` 文件：

- Claude Code
- Cursor
- OpenCode
- Codex
- Kiro
- Gemini CLI
- Qoder
- CodeBuddy
- GitHub Copilot
- Factory Droid
- Pi Agent

更改实现/检查/研究行为时，首先查找对应的平台智能体文件。

### 主会话工作流平台

以下平台更多依赖工作流/技能来引导主会话：

- Kilo
- Antigravity
- Windsurf

更改行为时，首先检查工作流和技能。不要假设 Trellis 子智能体存在。

### 共享 `.agents/skills/`

Codex 写入共享的 `.agents/skills/` 层级。某些支持 agentskills.io 的工具也可以读取此目录。如果用户希望多个兼容工具共享一个技能，优先考虑 `.agents/skills/`，但不要假设每个平台都会读取它。

## 修改平台文件时的决策规则

1. 用户指定了某个平台：仅修改该平台目录，除非共享工作流/规范文件也必须变更。
2. 用户说"所有平台都应该这样做"：逐平台同步等效入口点；不要只修改一个目录。
3. 用户只说"我的 AI"：检查项目中实际存在的配置目录，推断当前的 AI 平台。
4. 用户想要项目规则：优先使用 `.trellis/spec/` 或项目本地技能。
5. 用户想要 Trellis 行为：编辑 `.trellis/workflow.md` 以及平台钩子/智能体/技能/命令。

## 路径不一致时

平台生态会变化，用户项目可能已被定制。如果本表与本地文件不一致，以用户项目中的实际设置/配置为准：

- 检查设置注册的钩子。
- 检查命令/提示/工作流指向的脚本。
- 以智能体文件中当前编写的读取规则判断行为。

不要仅仅因为某个文件未列在此路径表中就删除自定义文件。
