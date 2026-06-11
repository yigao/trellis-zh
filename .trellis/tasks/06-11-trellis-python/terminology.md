# Trellis 术语对照表

本文件作为所有翻译工作的术语一致性基准。翻译时请严格遵循此表。

## 核心系统术语

| 英文 | 中文 | 说明 |
|------|------|------|
| workflow | 工作流 | Trellis 开发流程 |
| spec | 规范 | `.trellis/spec/` 下的编码规范文档 |
| hook | 钩子 | Claude Code 的钩子机制 |
| agent / subagent | 智能体 / 子智能体 | AI 智能体 |
| task | 任务 | Trellis 任务系统中的任务 |
| skill | 技能 | `.claude/skills/` 下的技能定义 |
| command | 命令 | `.claude/commands/` 下的斜杠命令 |
| workspace | 工作区 | `.trellis/workspace/` 下的工作记录 |
| journal | 日志 | 会话日志文件 |
| session | 会话 | AI 编程会话 |
| developer | 开发者 | Trellis 中的开发者身份 |
| context | 上下文 | AI 上下文 |
| injection | 注入 | 上下文注入机制 |
| phase | 阶段 | 工作流阶段（plan/execute/finish） |
| brainstorm | 头脑风暴 | 需求发现阶段 |
| lifecycle | 生命周期 | 任务从创建到归档的完整周期 |
| bootstrap | 引导 | 项目初始化 |
| pointer | 指针 | 指向当前活动任务的文件指针 |

## 文件/目录术语

| 英文 | 中文 | 说明 |
|------|------|------|
| PRD (Product Requirements Document) | 产品需求文档 | prd.md |
| implement.jsonl | 实现上下文文件 | 注入到实现智能体的规范文件列表 |
| check.jsonl | 检查上下文文件 | 注入到检查智能体的规范文件列表 |
| jsonl | JSONL | JSON Lines 格式 |
| YAML frontmatter | YAML 前置元数据 | Markdown 文件头部的 YAML 元数据块 |
| task.json | 任务元数据文件 | 每个任务目录下的状态文件 |
| CLAUDE.md | CLAUDE.md | 项目级 AI 指令文件 |
| SKILL.md | SKILL.md | 技能定义文件 |

## 技术概念术语

| 英文 | 中文 | 说明 |
|------|------|------|
| code-spec | 代码规范 | 编码规范上下文 |
| quality check | 质量检查 | 代码质量验证 |
| directory structure | 目录结构 | 项目目录组织规范 |
| state management | 状态管理 | 应用状态管理 |
| component | 组件 | UI 组件 |
| type safety | 类型安全 | TypeScript/类型系统安全 |
| error handling | 错误处理 | 异常和错误处理机制 |
| logging | 日志记录 | 日志输出规范 |
| database | 数据库 | 数据库相关 |
| guideline | 指南 | 编码指南和最佳实践 |
| convention | 惯例 | 编码惯例 |
| pattern | 模式 | 设计/编码模式 |
| template | 模板 | 文件模板 |
| iteration | 迭代 | 开发迭代 |
| idempotent | 幂等 | 多次执行结果不变 |
| degraded mode | 降级模式 | 缺少会话身份时的降级运行模式 |

## 开发流程术语

| 英文 | 中文 | 说明 |
|------|------|------|
| plan | 计划 | Phase 1：规划阶段 |
| execute | 执行 | Phase 2：实施阶段 |
| finish | 完成 | Phase 3：收尾阶段 |
| acceptance criteria | 验收标准 | 任务完成的检验标准 |
| definition of done | 完成定义 | 团队质量门槛 |
| out of scope | 明确不包含 | 排除在外的范围 |
| ADR (Architecture Decision Record) | 架构决策记录 | 重要技术决策记录 |
| implementation plan | 实施计划 | 代码实现步骤计划 |
| PR (Pull Request) | 拉取请求 | Git PR |
| branch | 分支 | Git 分支 |
| commit | 提交 | Git 提交 |
| archive | 归档 | 将完成的任务移到 archive/ 目录 |

## 翻译规则

1. **术语首次出现**时使用格式：`hook（钩子）`、`agent（智能体）`
2. **后续出现**时可直接使用英文术语：`hook`、`agent`
3. **代码块内容不翻译**：```python ... ``` 等代码块保持原样
4. **YAML frontmatter 不翻译**：`---` 包裹的元数据块保持原样
5. **函数名、变量名不翻译**：Python 代码中的标识符保持英文
6. **API 返回值、JSON key 不翻译**：机器接口部分保持英文
7. **print/log/错误消息**：翻译为中文（用户可见）
