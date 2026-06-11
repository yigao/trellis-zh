# Init 之后生成的本地文件

`trellis init` 将 Trellis 运行时写入用户项目。之后，`trellis update` 会尝试更新 Trellis 管理的模板文件，但它使用 `.trellis/.template-hashes.json` 来判断哪些文件已被用户修改过。

本页仅描述用户项目内可见且可编辑的文件。

## `.trellis/`

```text
.trellis/
├── workflow.md
├── config.yaml
├── .developer
├── .version
├── .template-hashes.json
├── .runtime/
├── scripts/
├── spec/
├── tasks/
└── workspace/
```

| 路径 | 通常可编辑？ | 说明 |
| --- | --- | --- |
| `.trellis/workflow.md` | 是 | 本地工作流文档和 AI 路由规则。 |
| `.trellis/config.yaml` | 是 | 项目配置、钩子、软件包、日志行数限制及相关设置。 |
| `.trellis/spec/` | 是 | 项目规范，预期由用户和 AI 定期更新。 |
| `.trellis/tasks/` | 是 | 任务材料和研究产物，由任务工作流维护。 |
| `.trellis/workspace/` | 是 | 会话记录，通常由 `add_session.py` 写入。 |
| `.trellis/scripts/` | 谨慎 | 本地运行时。可以定制，但需要先理解调用链。 |
| `.trellis/.runtime/` | 否 | 运行时状态，通常由钩子/脚本自动写入。 |
| `.trellis/.developer` | 谨慎 | 当前开发者身份。 |
| `.trellis/.version` | 否 | Trellis 版本记录，供 update/migration 逻辑使用。 |
| `.trellis/.template-hashes.json` | 否 | 模板哈希记录。不要在此写入业务规则。 |

## 平台目录

不同平台生成不同的目录。常见类别：

| 类别 | 示例路径 | 用途 |
| --- | --- | --- |
| 钩子 | `.claude/hooks/`、`.codex/hooks/`、`.cursor/hooks/` | 注入会话上下文、workflow-state 和子智能体上下文。 |
| 设置 | `.claude/settings.json`、`.codex/hooks.json`、`.qoder/settings.json` | 告知平台何时运行钩子或插件。 |
| 智能体 | `.claude/agents/`、`.codex/agents/`、`.kiro/agents/` | 定义 `trellis-research`、`trellis-implement`、`trellis-check` 等智能体。 |
| 技能 | `.claude/skills/`、`.agents/skills/`、`.qoder/skills/` | 可自动触发或供 AI 读取的技能。 |
| 命令/提示/工作流 | `.cursor/commands/`、`.github/prompts/`、`.windsurf/workflows/` | 用户显式调用的命令或工作流入口点。 |

修改平台目录时，也要确认 `.trellis/workflow.md` 是否仍描述相同的流程。

## 模板哈希的含义

`.trellis/.template-hashes.json` 记录了 Trellis 上次写入模板文件时的内容哈希。`trellis update` 用它区分三种情况：

| 情况 | 更新行为 |
| --- | --- |
| 文件未被用户修改 | 可以自动更新。 |
| 文件已被用户修改 | 提示用户选择覆盖、保留或生成 `.new` 文件。 |
| 文件不再是当前模板 | 可能被删除、重命名或根据迁移规则保留。 |

当 AI 定制本地 Trellis 文件时，无需手动维护哈希。Trellis update 将结果识别为"已被用户修改"是正常行为。

## 本地定制边界

默认可编辑：

- `.trellis/workflow.md`
- `.trellis/config.yaml`
- `.trellis/spec/**`
- `.trellis/scripts/**`
- 平台钩子、设置、智能体、技能、命令、提示和工作流

默认不可编辑：

- 全局 npm 安装目录
- `node_modules/@mindfoldhq/trellis`
- Trellis GitHub 仓库源代码
- `.trellis/.runtime/**` 下的具体状态文件
- `.trellis/.template-hashes.json` 内的哈希内容

仅在用户明确想要向上游贡献时才切换到 Trellis CLI 源代码视角。
