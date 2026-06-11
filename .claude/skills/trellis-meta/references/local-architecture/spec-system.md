# 本地规范系统

`.trellis/spec/` 是用户项目专属的工程规范库。Trellis 不是让 AI 记住惯例（convention），而是在合适的时机注入相关规范或要求 AI 去读取它们。

## 目录模型

常见的单仓库结构：

```text
.trellis/spec/
├── backend/
│   ├── index.md
│   └── ...
├── frontend/
│   ├── index.md
│   └── ...
└── guides/
    ├── index.md
    └── ...
```

常见的 monorepo 结构：

```text
.trellis/spec/
├── cli/
│   ├── backend/
│   │   ├── index.md
│   │   └── ...
│   └── unit-test/
│       ├── index.md
│       └── ...
├── docs-site/
│   └── docs/
│       ├── index.md
│       └── ...
└── guides/
    ├── index.md
    └── ...
```

`index.md` 是每个层级的入口点。它应列出开发前检查清单和质量检查（quality check）。具体指南（guideline）存放在同一目录下的其他 Markdown 文件中。

## 软件包配置

`.trellis/config.yaml` 可以声明软件包：

```yaml
packages:
  cli:
    path: packages/cli
  docs-site:
    path: docs-site
    type: submodule
default_package: cli
```

AI 可以运行：

```bash
py -3 ./.trellis/scripts/get_context.py --mode packages
```

此命令列出当前项目的软件包和规范层级。配置上下文 JSONL 时将此输出作为参考。

## 规范如何进入任务

在任务进入实现阶段之前，阶段 1.3 应将相关规范写入 `implement.jsonl` / `check.jsonl`：

```jsonl
{"file": ".trellis/spec/cli/backend/index.md", "reason": "CLI backend conventions"}
{"file": ".trellis/spec/cli/unit-test/conventions.md", "reason": "Test expectations"}
```

子智能体或平台序言读取这些 JSONL 文件并加载引用的规范。在不支持子智能体的平台上，AI 应按照工作流直接读取相关规范。

## 规范应包含的内容

规范应包含项目可执行的工程惯例，而非通用最佳实践：

- 文件应放置的位置。
- 错误处理应如何表达。
- API、钩子和命令的输入/输出契约。
- 被禁止使用的模式（pattern）。
- 需要测试的场景。
- 项目特有的陷阱及如何避免。

当 AI 在实现或调试过程中学到新规则时，应更新 `.trellis/spec/`，而不是仅在聊天中总结。

## 本地定制点

| 需求 | 编辑位置 |
| --- | --- |
| 添加新的规范层级 | `.trellis/spec/<package>/<layer>/index.md` 及相应的指南文件。 |
| 更改 monorepo 规范映射 | `.trellis/config.yaml` 中的 `packages` / `default_package` / `spec_scope`。 |
| 更改 AI 在实现前应读取的规范 | 任务的 `implement.jsonl`。 |
| 更改 AI 在检查期间应读取的规范 | 任务的 `check.jsonl`。 |
| 更改何时应更新规范 | `.trellis/workflow.md` 中的阶段 3.3 和 `trellis-update-spec` 技能。 |

## 边界

`.trellis/spec/` 是用户的项目规范，而非 Trellis 内置模板的永久副本。AI 应鼓励用户根据实际项目代码更新它，而不是将 Trellis 默认模板视为不可变文档。
