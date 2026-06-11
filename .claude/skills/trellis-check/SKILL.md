---
name: trellis-check
description: "Comprehensive quality verification: spec compliance, lint, type-check, tests, cross-layer data flow, code reuse, and consistency checks. Use when code is written and needs quality verification, before committing changes, or to catch context drift during long sessions."
---

# 代码质量 Check（检查）

对最近编写的代码进行全面的 quality（质量）验证。结合 spec 合规性、跨层安全性以及提交前检查。

---

## 步骤 1：识别变更内容

```bash
git diff --name-only HEAD
git status
```

## 步骤 2：阅读适用的 Spec

```bash
py -3 ./.trellis/scripts/get_context.py --mode packages
```

对于每个变更的 package/layer，阅读 spec 索引并按照其 **Quality Check** 章节操作：

```bash
cat .trellis/spec/<package>/<layer>/index.md
```

阅读索引引用的具体 guideline 文件——索引只是指针，不是目标。

## 步骤 3：运行项目检查

运行项目的 lint、type-check 和 test 命令。修复所有失败后再继续。

## 步骤 4：对照 Checklist 审查

### 代码质量

- [ ] Linter 通过？
- [ ] 类型检查器通过（如适用）？
- [ ] 测试通过？
- [ ] 没有遗留调试日志？
- [ ] 没有抑制的警告或类型安全绕过？

### 测试覆盖

- [ ] 新函数 → 已添加单元测试？
- [ ] Bug 修复 → 已添加回归测试？
- [ ] 行为变更 → 已更新已有测试？

### Spec 同步

- [ ] `.trellis/spec/` 是否需要更新？（新的 pattern、convention、经验教训）

> "如果我修了一个 bug 或发现了什么不明显的东西，我应该把它记录下来，以免将来的我再踩同一个坑吗？" → 如果是，更新相关的 spec 文档。

## 步骤 5：跨层维度（如适用）

如果你的变更仅限于单层，请跳过此步骤。

### A. 数据流（变更涉及 3 层以上）

- [ ] 读取流程追踪正确：Storage → Service → API → UI
- [ ] 写入流程追踪正确：UI → API → Service → Storage
- [ ] 类型/模式在各层之间传递正确？
- [ ] 错误正确传播至调用者？

### B. 代码复用（修改常量、创建工具函数）

- [ ] 在创建新代码之前搜索过已有的类似代码？
  ```bash
  grep -r "pattern" src/
  ```
- [ ] 如果 2 处以上定义了相同值 → 提取为共享常量？
- [ ] 批量修改后，所有出现都已更新？

### C. 导入/依赖（创建新文件）

- [ ] 导入路径正确（相对 vs 绝对）？
- [ ] 没有循环依赖？

### D. 同层一致性

- [ ] 使用同一概念的其他位置是否一致？

---

## 步骤 6：报告并修复

报告发现的违规项并直接修复。修复后重新运行项目检查。
