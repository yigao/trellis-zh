---
name: trellis-before-dev
description: "Discovers and injects project-specific coding guidelines from .trellis/spec/ before implementation begins. Reads spec indexes, pre-development checklists, and shared thinking guides for the target package. Use when starting a new coding task, before writing any code, switching to a different package, or needing to refresh project conventions and standards."
---

在开始 task（任务）之前，阅读相关的开发 guideline（指南）。

执行以下步骤：

1. **发现 package（软件包）及其 spec（规范）层**：
   ```bash
   py -3 ./.trellis/scripts/get_context.py --mode packages
   ```

2. **确定哪些 spec 适用于**你的 task，依据：
   - 你要修改哪个 package（如 `cli/`、`docs-site/`）
   - 工作类型是什么（backend、frontend、unit-test、docs 等）

3. **阅读每个相关模块的 spec 索引**：
   ```bash
   cat .trellis/spec/<package>/<layer>/index.md
   ```
   按照索引中的 **"Pre-Development Checklist"** 章节操作。

4. **阅读 Pre-Development Checklist 中列出的、与你 task 相关的具体 guideline 文件**。索引本身不是目标——它指向实际的 guideline 文件（如 `error-handling.md`、`conventions.md`、`mock-strategies.md`）。阅读这些文件以了解编码标准和 pattern（模式）。

5. **始终阅读共享 guide**：
   ```bash
   cat .trellis/spec/guides/index.md
   ```

6. 理解你需要遵循的编码标准和 pattern，然后继续你的开发计划。

此步骤在编写任何代码之前是**强制性的**。
