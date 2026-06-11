---
name: trellis-break-loop
description: "Deep bug analysis to break the fix-forget-repeat cycle. Analyzes root cause category, why fixes failed, prevention mechanisms, and captures knowledge into specs. Use after fixing a bug to prevent the same class of bugs."
---

# Break the Loop（打破循环）- 深度 Bug 分析

当调试完成后，使用此 skill（技能）进行深度分析，打破"修 bug → 忘记 → 重复"的循环。

---

## 分析框架

从以下 5 个维度分析你刚修复的 bug：

### 1. 根因分类

这个 bug 属于哪个类别？

| 类别 | 特征 | 示例 |
|----------|-----------------|---------|
| **A. 缺少 Spec** | 缺少关于如何操作的文档 | 新功能没有 checklist |
| **B. 跨层合约** | 层之间的接口不够明确 | API 返回格式与预期不同 |
| **C. 变更传播失败** | 改了一处，漏了其他 | 改了函数签名，漏了调用点 |
| **D. 测试覆盖不足** | 单元测试通过，集成测试失败 | 单独运行正常，组合后出问题 |
| **E. 隐式假设** | 代码依赖未文档化的假设 | 时间戳单位是秒还是毫秒 |

### 2. 失败修复原因（如适用）

如果在成功之前你尝试了多次修复，分析每次失败：

- **表面修复**：修了症状，没修根因
- **覆盖不全**：找到了根因，但没覆盖所有情况
- **工具限制**：grep 没找到、类型检查不够严格
- **思维模型**：一直在同一层查找，没想到跨层

### 3. 预防机制

什么机制可以防止此类问题再次发生？

| 类型 | 描述 | 示例 |
|------|-------------|---------|
| **文档化（Documentation）** | 记录下来让大家知道 | 更新 thinking guide |
| **架构（Architecture）** | 从结构上杜绝该错误 | 类型安全包装器 |
| **编译时（Compile-time）** | 严格类型检查、无后门 | 签名变更导致编译错误 |
| **运行时（Runtime）** | 监控、告警、扫描 | 检测孤立实体 |
| **测试覆盖（Test Coverage）** | E2E 测试、集成测试 | 验证完整流程 |
| **代码审查（Code Review）** | Checklist、PR 模板 | "你检查过 X 吗？" |

### 4. 系统化扩展

这个 bug 揭示了哪些更广泛的问题？

- **类似问题**：其他地方还可能存在同样的问题吗？
- **设计缺陷**：是否存在根本性的架构问题？
- **流程缺陷**：是否有开发流程改进空间？
- **知识缺口**：团队是否缺少某些理解？

### 5. 知识捕获

将洞察固化到系统中：

- [ ] 更新 `.trellis/spec/guides/` thinking guide
- [ ] 更新相关的 `.trellis/spec/` 文档
- [ ] 创建 issue 记录（如适用）
- [ ] 创建根因修复的 feature ticket
- [ ] 必要时更新 check（检查） guideline

---

## 输出格式

请按以下格式输出分析：

```markdown
## Bug Analysis: [Short Description]

### 1. Root Cause Category
- **Category**: [A/B/C/D/E] - [Category Name]
- **Specific Cause**: [Detailed description]

### 2. Why Fixes Failed (if applicable)
1. [First attempt]: [Why it failed]
2. [Second attempt]: [Why it failed]
...

### 3. Prevention Mechanisms
| Priority | Mechanism | Specific Action | Status |
|----------|-----------|-----------------|--------|
| P0 | ... | ... | TODO/DONE |

### 4. Systematic Expansion
- **Similar Issues**: [List places with similar problems]
- **Design Improvement**: [Architecture-level suggestions]
- **Process Improvement**: [Development process suggestions]

### 5. Knowledge Capture
- [ ] [Documents to update / tickets to create]
```

---

## 核心理念

> **调试的价值不在于修好这个 bug，而在于让这一类 bug 永不再发生。**

三个层次的洞察：
1. **战术层（Tactical）**：如何修复这一个 bug
2. **战略层（Strategic）**：如何防止这一类别 bug
3. **哲学层（Philosophical）**：如何扩展思维 pattern

30 分钟的分析可以节省未来 30 小时的调试。

---

## 分析完成后：立即行动

**重要**：完成上述分析后，你**必须**立即：

1. **更新 spec/guide** - 不要只列出 TODO，要切实更新相关文件：
   - 如果是跨平台问题 → 更新 `cross-platform-thinking-guide.md`
   - 如果是跨层问题 → 更新 `cross-layer-thinking-guide.md`
   - 如果是代码复用问题 → 更新 `code-reuse-thinking-guide.md`
   - 如果是领域特定问题 → 更新 `backend/*.md` 或 `frontend/*.md`

2. **同步模板** - 更新 `.trellis/spec/` 后，同步到 `src/templates/markdown/spec/`

3. **提交 spec 更新** - 这是主要产出，而不仅仅是分析文本

> **如果分析只停留在聊天记录中，则毫无价值。价值在于更新后的 spec。**
