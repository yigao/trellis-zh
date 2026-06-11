# 智能体

Trellis 智能体（agent）文件定义专门的角色。用户项目中常见的 Trellis 智能体有：

- `trellis-research`
- `trellis-implement`
- `trellis-check`

文件位置和格式因平台而异，但职责边界应保持一致。

## 智能体职责

| 智能体 | 职责 |
| --- | --- |
| `trellis-research` | 研究问题并将结论写入当前任务的 `research/`。 |
| `trellis-implement` | 对照 `prd.md`、`info.md`、`implement.jsonl` 及相关规范/研究进行实现。 |
| `trellis-check` | 审查变更，修复发现的问题，并运行必要的检查。 |

智能体文件不应成为通用聊天提示。它们应定义输入来源、写入边界、是否可以修改代码以及如何报告结果。

## 常见路径

| 平台 | 智能体路径 |
| --- | --- |
| Claude Code | `.claude/agents/trellis-*.md` |
| Cursor | `.cursor/agents/trellis-*.md` |
| OpenCode | `.opencode/agents/trellis-*.md` |
| Codex | `.codex/agents/trellis-*.toml` |
| Kiro | `.kiro/agents/trellis-*.json` |
| Gemini CLI | `.gemini/agents/trellis-*.md` |
| Qoder | `.qoder/agents/trellis-*.md` |
| CodeBuddy | `.codebuddy/agents/trellis-*.md` |
| Factory Droid | `.factory/droids/trellis-*.md` |
| Pi Agent | `.pi/agents/trellis-*.md` |

GitHub Copilot 的 agent/prompt 支持由 `.github/agents/`、`.github/prompts/` 和 `.github/skills/` 等目录组合提供；检查用户项目中实际生成的文件。

Kilo、Antigravity 和 Windsurf 等主会话工作流平台可能没有 Trellis 子智能体文件。它们通常依赖工作流/技能来引导主会话。

## 两种上下文加载模式

### hook push

平台钩子在智能体启动前注入任务上下文。智能体文件本身可以更专注于职责和边界。

常见于支持智能体钩子的平台。

### agent pull

智能体文件指示智能体在启动后读取：

- `py -3 ./.trellis/scripts/task.py current --source`
- 当前任务 `prd.md`
- `info.md`
- `implement.jsonl` 或 `check.jsonl`
- JSONL 引用的规范/研究文件

此模式适用于钩子无法可靠重写子智能体提示的平台。

## 本地变更场景

| 用户需求 | 编辑位置 |
| --- | --- |
| 实现智能体必须遵守额外限制 | 平台的 `trellis-implement` 智能体文件。 |
| 检查智能体必须运行项目专属命令 | `trellis-check` 智能体文件，必要时也包括 `.trellis/spec/`。 |
| 研究智能体必须输出固定格式 | `trellis-research` 智能体文件。 |
| 智能体无法读取任务上下文 | 智能体序言或 `inject-subagent-context` 钩子。 |
| 添加项目专属智能体 | 平台智能体目录 + 相关工作流/命令/技能入口点。 |

## 修改原则

1. **保持职责单一**。不要将研究、实现和检查的职责混合到一个智能体中。
2. **指定读取顺序**。智能体必须知道从活动任务开始，然后找到 PRD 和 JSONL。
3. **指定写入边界**。研究通常只写入 `research/`；实现可以写入代码；检查可以修复问题。
4. **在多平台项目中保持语义同步**。如果用户同时配置了 Claude、Codex 和 Cursor，判断对一个平台智能体的更改是否需要同步应用到其他平台。

## 不要默认编辑上游模板

本地 AI 应默认修改用户项目内的平台智能体文件。仅在用户明确想要将变更贡献回 Trellis 上游时才讨论上游模板源代码。
