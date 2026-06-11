# 更改本地 agent（智能体）

当用户想要更改 `trellis-research`、`trellis-implement` 或 `trellis-check` 行为时，编辑用户项目中的平台 agent 文件。

## 首先读取这些文件

1. 目标平台 agent 目录
2. `.trellis/workflow.md` Phase 2 / research 路由
3. 当前 task 的 `prd.md`
4. 当前 task 的 `implement.jsonl` / `check.jsonl`
5. 相关的 hook 或 agent 前导部分

## 常见路径

| 平台 | 路径 |
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

以用户项目中的实际路径为准。

## 常见需求

| 需求 | 编辑哪个 agent |
| --- | --- |
| Research 必须写入文件，而不仅仅在聊天中回复 | `trellis-research` |
| 某些本地 spec 必须在 implement（实现）之前读取 | `trellis-implement` + `implement.jsonl` 配置规则 |
| 某些 command（命令）必须在 check（检查）期间运行 | `trellis-check` |
| Agent 不得修改某些目录 | 相应 agent 的写入边界指令 |
| Agent 输出格式必须修正 | 相应 agent 的最终/报告指令 |

## 修改原则

1. **保持角色边界**：research 负责调查并持久化；implement 负责编写实现；check 负责审查和修复。
2. **不要将项目 spec 硬编码到 agent 中**：长期 spec 应放在 `.trellis/spec/` 中；agent 负责读取它们。
3. **明确读取顺序**：活动 task -> PRD -> info -> JSONL -> spec/research。
4. **明确写入边界**：哪些目录可以写入，哪些不可以。
5. **跨平台同步**：当用户配置了多个平台时，决定是仅更改当前平台还是所有平台的 agent。

## Agent 拉取模式平台

如果 agent 文件包含"启动后读取 task/上下文"的前导部分，编辑时不要移除这些步骤。否则 agent 将仅基于聊天 context 工作，绕过 Trellis 的核心机制。

## Hook 推送模式平台

如果 context 由 hook 注入，agent 文件仍应保留职责边界。不要因为 hook 注入了 context 就从 agent 中移除 PRD/spec 要求。
