# 添加项目本地惯例

通常用户不需要更改 Trellis 机制；他们需要本地 AI 理解其团队的 convention（惯例）。在这种情况下，优先使用 `.trellis/spec/` 或项目本地 skill，而非编辑 `trellis-meta`。

## 内容存放位置

| 内容类型 | 位置 |
| --- | --- |
| 代码必须遵循的规则 | `.trellis/spec/<layer>/` |
| 跨层级思考方法 | `.trellis/spec/guides/` |
| 项目特定流程的 AI 能力 | 平台本地 skill |
| 一次性任务材料 | `.trellis/tasks/<task>/` |
| session（会话）摘要 | `.trellis/workspace/<developer>/journal-N.md` |

## 创建项目本地 skill

如果用户希望 AI 了解"此项目如何自定义 Trellis"，请创建本地 skill：

```text
.claude/skills/trellis-local/
└── SKILL.md
```

示例：

```md
---
name: trellis-local
description: "Project-local Trellis customizations for this repository. Use when changing this project's Trellis workflow, hooks, local agents, or team-specific conventions."
---

# Trellis Local

## Local Scope

This skill documents this repository's Trellis customizations only.

## Custom Workflow Rules

- ...

## Local Hook Changes

- ...

## Local Agent Changes

- ...
```

对于多平台项目，在其他平台 skill 目录中放置等效版本，或对于支持共享层的平台使用 `.agents/skills/`。

## 写入 `.trellis/spec/`

如果内容是编码惯例，将其写入 spec。示例：

```text
.trellis/spec/backend/error-handling.md
.trellis/spec/frontend/components.md
.trellis/spec/guides/cross-platform-thinking-guide.md
```

写入后，更新相应的 `index.md`，以便 AI 能从入口点找到新规则。

## 使当前任务使用新惯例

写入 spec 后，将其添加到当前任务 context（上下文）：

```bash
py -3 ./.trellis/scripts/task.py add-context <task> implement ".trellis/spec/backend/error-handling.md" "Error handling conventions"
py -3 ./.trellis/scripts/task.py add-context <task> check ".trellis/spec/backend/error-handling.md" "Review error handling"
```

## 不要将项目私有规则存储在 `trellis-meta` 中

`trellis-meta` 是一个用于理解 Trellis architecture（架构）和本地自定义入口点的公共 skill。将项目私有内容放在：

- `.trellis/spec/`
- 项目本地 skill
- 当前 task
- workspace（工作区）journal（日志）

这样可以防止 Trellis 内置 `trellis-meta` 的未来更新覆盖团队自己的惯例。
