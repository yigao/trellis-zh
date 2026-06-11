# 更改本地 skill、command、prompt 和 workflow

当用户想要更改 AI 入口点、自动触发规则或显式命令行为时，编辑本地平台目录中的 skill、command、prompt 或 workflow。

## 首先读取这些文件

1. `.trellis/workflow.md`
2. 目标平台 skill/command/prompt/workflow 目录
3. 相关的 agent 或 hook 文件
4. `.trellis/spec/` 中是否已存在项目规则

## 选择哪种入口类型

| 目标 | 建议 |
| --- | --- |
| AI 应自动知晓某项能力 | 添加或修改 skill。 |
| 用户希望通过 command 手动触发 | 添加或修改 command/prompt/workflow。 |
| 团队项目惯例 | 优先使用 `.trellis/spec/` 或项目本地 skill。 |
| 更改 Trellis 工作流语义 | 同步 `.trellis/workflow.md`。 |

## 修改 skill

Skill 通常为：

```text
<skill-name>/
├── SKILL.md
└── references/
```

`SKILL.md` 应简短，负责触发/路由。将长篇内容放在 `references/` 中，以便 AI 按需读取。

frontmatter 中的 description 应指定何时使用该 skill。示例：

```yaml
description: "Use when customizing this project's deployment workflow and release checklist."
```

不要编写模糊的描述，如"helpful project skill"；它们可能会被错误触发。

## 修改 command/prompt/workflow

显式入口点应说明：

- 用户如何触发它。
- 需要读取哪些 `.trellis/` 文件。
- 需要运行哪些脚本。
- 完成后如何报告。

如果某个 command 仅仅重复 workflow 规则，最好让它引用/读取 `.trellis/workflow.md`，而不是维护一份流程的副本。

## 常见路径

| 平台 | 入口目录 |
| --- | --- |
| Claude Code | `.claude/skills/`、`.claude/commands/` |
| Cursor | `.cursor/skills/`、`.cursor/commands/` |
| OpenCode | `.opencode/skills/`、`.opencode/commands/` |
| Codex | `.agents/skills/`、`.codex/skills/` |
| GitHub Copilot | `.github/skills/`、`.github/prompts/` |
| Kilo / Antigravity / Windsurf | workflows + skills |

## 添加项目本地 skill

如果用户想要记录团队私有自定义内容，请创建项目本地 skill，例如：

```text
.claude/skills/project-trellis-local/
└── SKILL.md
```

对于多平台项目，在每个平台 skill 目录中添加等效版本，或对于支持共享层的平台使用 `.agents/skills/`。

## 注意事项

- 不要将每种平台的语法混入一个文件。
- 不要在声称支持所有平台的同时仅更改一个平台的入口点。
- 不要将长期工程惯例隐藏在 command 中；将其写入 `.trellis/spec/`。
