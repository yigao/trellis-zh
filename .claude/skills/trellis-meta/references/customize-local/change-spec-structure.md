# 更改本地 spec（规范）结构

当用户想要更改 AI 遵循的工程惯例、添加新的 spec 层级或调整 monorepo 中 package（软件包）的映射时，编辑 `.trellis/spec/` 和 `.trellis/config.yaml`。

## 首先读取这些文件

1. `.trellis/config.yaml`
2. `.trellis/spec/`
3. `.trellis/workflow.md` Phase 1.3 和 Phase 3.3
4. 当前 task 的 `implement.jsonl` / `check.jsonl`

## 常见需求

| 需求 | 编辑位置 |
| --- | --- |
| 添加 backend/frontend/docs/test spec 层级 | `.trellis/spec/<layer>/` 或 `.trellis/spec/<package>/<layer>/` |
| 添加共享思考指南 | `.trellis/spec/guides/` |
| 调整 monorepo 软件包 | `.trellis/config.yaml` 中的 `packages` |
| 更改默认软件包 | `.trellis/config.yaml` 中的 `default_package` |
| 控制 spec 扫描范围 | `.trellis/config.yaml` 中的 `spec_scope` |
| 使某个 task 读取新的 spec | Task `implement.jsonl` / `check.jsonl` |

## 添加 spec 层级

单仓库示例：

```text
.trellis/spec/security/
├── index.md
└── auth.md
```

Monorepo 示例：

```text
.trellis/spec/webapp/security/
├── index.md
└── auth.md
```

`index.md` 应包含：

- 此层级适用于哪些代码。
- 开发前检查清单（Pre-Development Checklist）。
- 质量检查（Quality Check）。
- 指向具体 guideline（指南）文件的链接。

## 更新上下文

添加 spec 并不意味着每个 task 都会自动读取它。当前 task 必须在 JSONL 中引用它：

```bash
py -3 ./.trellis/scripts/task.py add-context <task> implement ".trellis/spec/webapp/security/index.md" "Security conventions"
py -3 ./.trellis/scripts/task.py add-context <task> check ".trellis/spec/webapp/security/index.md" "Security review rules"
```

## 更改 monorepo 软件包

示例 `.trellis/config.yaml`：

```yaml
packages:
  webapp:
    path: apps/web
  api:
    path: apps/api
default_package: webapp
```

编辑后运行：

```bash
py -3 ./.trellis/scripts/get_context.py --mode packages
```

使用此输出确认 AI 能看到正确的软件包和 spec 层级。

## 注意事项

- Spec 是用户项目惯例，可根据项目需求更改。
- 不要将临时 task 信息放入 spec；将临时信息放在 task 中。
- 不要将长期惯例仅放在 agent 或 command 中；将其保留在 spec 中。
- 更改 spec 结构后，检查现有 task 的 JSONL 文件是否仍指向存在的文件。
