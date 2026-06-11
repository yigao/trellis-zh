# 本地自定义概述

本目录供通过 npm 安装了 Trellis 且已运行 `trellis init` 的用户项目中的本地 AI 使用。AI 应修改项目中生成的 `.trellis/` 和 platform（平台）目录，而非 Trellis CLI 上游源代码。

## 首先确定用户实际想要更改什么

| 用户表述 | 先阅读 |
| --- | --- |
| "更改 Trellis 流程 / 阶段 / 下一个提示" | `change-workflow.md` |
| "更改 task（任务）创建、状态、归档或 hooks（钩子）" | `change-task-lifecycle.md` |
| "AI 没有阅读上下文 / 更改注入内容" | `change-context-loading.md` |
| "某个平台 hook 行为不符合预期" | `change-hooks.md` |
| "更改 implement/check/research agent（智能体）行为" | `change-agents.md` |
| "添加 skill/command/workflow/提示词" | `change-skills-or-commands.md` |
| "调整项目 spec（规范）结构" | `change-spec-structure.md` |
| "添加团队惯例和本地备注" | `add-project-local-conventions.md` |

## 一般操作顺序

1. **确认平台和目录**：检查哪些目录存在，如 `.claude/`、`.codex/`、`.cursor/`。
2. **确认当前活动任务**：运行 `py -3 ./.trellis/scripts/task.py current --source`。
3. **阅读本地权威来源**：优先查阅 `.trellis/workflow.md`、`.trellis/config.yaml` 及相关平台文件。
4. **精准修改**：仅编辑与用户请求相关的文件。
5. **同步语义**：如果共享 flow（工作流）变更，检查平台入口点是否也需要变更；如果平台入口变更，检查 `.trellis/workflow.md` 是否仍然一致。

## 本地文件优先级

| 层级 | 文件 |
| --- | --- |
| Workflow | `.trellis/workflow.md` |
| 项目配置 | `.trellis/config.yaml` |
| 任务材料 | `.trellis/tasks/<task>/` |
| 项目规范 | `.trellis/spec/` |
| 运行时脚本 | `.trellis/scripts/` |
| 平台集成 | `.claude/`、`.codex/`、`.cursor/`、`.opencode/` 及类似目录 |
| 共享 skill | `.agents/skills/` |

## 默认不应做的事

- 不要编辑全局 npm 安装目录。
- 不要编辑 `node_modules/@mindfoldhq/trellis`。
- 不要假设用户拥有 Trellis GitHub repository（仓库）。
- 不要用默认模板覆盖用户已修改的本地文件。
- 不要将团队项目规则放入公开的 `trellis-meta`；项目规则应放在 `.trellis/spec/` 或本地 skill 中。

## 何时查阅上游源代码

仅当用户明确表达以下目标之一时，才切换到上游源代码视角：

- "我想向 Trellis 提交 PR（拉取请求）"
- "我想更改 npm 软件包发布内容"
- "我想 fork Trellis"
- "我想修改 `trellis init/update` 的生成逻辑"

否则，默认修改用户项目内的本地 Trellis 文件。
