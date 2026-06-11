# 本地 Trellis 架构概览

`trellis-meta` 适用于已运行 `trellis init` 的用户项目。用户机器上通常只有通过 npm 安装的 `trellis` 命令以及项目内生成的 Trellis 文件；可能没有 Trellis CLI 源代码。

因此，当 AI 使用此技能时，默认的定制目标是用户项目内的本地文件：

- `.trellis/`：工作流（workflow）、任务（task）、规范（spec）、记忆、脚本和运行时状态。
- 平台目录：`.claude/`、`.codex/`、`.cursor/`、`.opencode/`、`.kiro/`、`.gemini/`、`.qoder/`、`.codebuddy/`、`.github/`、`.factory/`、`.pi/`、`.kilocode/`、`.agent/`、`.windsurf/` 及类似目录。
- 共享技能（skill）层：`.agents/skills/`。

不要默认引导用户 fork Trellis CLI 仓库。只有在用户明确表示要更改 Trellis 上游源代码、发布 npm 软件包（package）或贡献 PR 时，才将上游源代码作为操作目标。

## 本地系统模型

Trellis 在用户项目内提供三个层级（layer）：

1. **工作流层**：`.trellis/workflow.md` 定义阶段（phase）、路由、下一步操作和提示块。
2. **持久层**：`.trellis/tasks/`、`.trellis/spec/` 和 `.trellis/workspace/` 存储任务、规范和工作区（workspace）会话记忆。
3. **平台集成层**：平台目录中的钩子（hook）、设置、智能体（agent）、技能、命令（command）、提示和工作流将 Trellis 工作流连接到不同的 AI 工具。

所有三个层级都位于用户项目内部，因此 AI 可以直接读取和修改它们。

## 核心路径

| 路径 | 用途 |
| --- | --- |
| `.trellis/workflow.md` | 工作流阶段、技能路由和工作流状态提示块。 |
| `.trellis/config.yaml` | 项目配置、任务生命周期钩子、monorepo 软件包配置和日志（journal）配置。 |
| `.trellis/spec/` | 用户项目专属的编码惯例（convention）和思考指南（guideline）。 |
| `.trellis/tasks/` | 每个任务的产品需求文档（PRD）、技术说明、研究文件及 JSONL 上下文。 |
| `.trellis/workspace/` | 每位开发者（developer）的日志和跨会话（session）记忆。 |
| `.trellis/scripts/` | 由命令、钩子和上下文注入（context injection）使用的本地 Python 运行时。 |
| `.trellis/.runtime/` | 会话级别的运行时状态，例如当前任务指针。 |
| `.trellis/.template-hashes.json` | Trellis 管理文件的模板哈希，供 update 用于判断本地文件是否被用户修改过。 |

## AI 定制原则

1. **先找到本地的事实来源**：不要凭记忆编辑。先读取 `.trellis/workflow.md`、`.trellis/config.yaml`、相关平台目录和相关任务文件。
2. **编辑用户项目，而非 npm 软件包缓存**：修改项目内的生成文件（generated files），而不是 `node_modules` 或全局 npm 安装目录。
3. **保持平台文件与 `.trellis/` 对齐**：如果工作流路由发生变更，也要检查平台技能或命令是否仍描述相同的流程。
4. **将项目专属规则放在 `.trellis/spec/` 或本地技能中**：不要将团队惯例放入 `trellis-meta`。
5. **保留用户的修改**：如果某个文件已在本地被修改过，应基于当前内容工作，而不是用默认模板覆盖它。

## 如何使用此目录

- 了解 init 之后存在哪些文件，阅读 `generated-files.md`。
- 修改阶段、路由或下一步操作，阅读 `workflow.md`。
- 修改任务模型、JSONL 上下文或活动任务行为，阅读 `task-system.md`。
- 修改编码惯例注入，阅读 `spec-system.md`。
- 了解日志和跨会话记忆，阅读 `workspace-memory.md`。
- 修改钩子或子智能体上下文加载，阅读 `context-injection.md`。
