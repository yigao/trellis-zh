---
name: trellis-update-spec
description: "Captures executable contracts and coding conventions into .trellis/spec/ documents. Use when learning something valuable from debugging, implementing, or discussion that should be preserved for future sessions."
---

# Update Code-Spec（更新代码规范） - 捕获可执行合约

当你学到有价值的东西（来自调试、实现或讨论），使用本 skill 更新相关的 code-spec（代码规范）文档。

**时机**：完成 task、修复 bug 或发现新 pattern 之后

---

## Code-Spec 优先规则（关键）

在此项目中，实现工作中所指的 "spec" 即是 **code-spec**：
- 可执行合约（而非仅原则性文字）
- 具体的签名、payload 字段、环境变量键以及边界行为
- 可测试的验证/错误行为

如果变更涉及基础设施或跨层合约，code-spec 深度是强制性的。

### 强制性触发条件

当变更包含以下任一项时，必须应用 code-spec 深度：
- 新增/修改的命令或 API 签名
- 跨层请求/响应合约变更
- 数据库 schema/迁移变更
- 基础设施集成（存储、队列、缓存、密钥、环境变量接线）

### 强制输出（7 个章节）

对于被触发的 task，必须包含以下所有章节：
1. Scope / Trigger
2. Signatures (command/API/DB)
3. Contracts (request/response/env)
4. Validation & Error Matrix
5. Good/Base/Bad Cases
6. Tests Required (with assertion points)
7. Wrong vs Correct (at least one pair)

---

## 何时更新 Code-Spec

| 触发条件 | 示例 | 目标 Spec |
|---------|---------|-------------|
| **实现了一个功能** | 添加了新的集成或模块 | 相关 spec 文件 |
| **做出了设计决策** | 选择了扩展性 pattern 而非简单方案 | 相关 spec + "Design Decisions" 章节 |
| **修复了一个 bug** | 发现了错误处理中的细微问题 | 相关 spec（如 error-handling 文档） |
| **发现了一个 pattern** | 找到了更好的代码结构方式 | 相关 spec 文件 |
| **踩到了一个坑** | 了解到 X 必须在 Y 之前完成 | 相关 spec + "Common Mistakes" 章节 |
| **确立了一个 convention** | 团队就命名 pattern 达成一致 | quality guideline |
| **新的思维触发点** | "做 Y 之前别忘了检查 X" | `guides/*.md`（作为 checklist 条目） |

**关键洞察**：Code-spec 更新不仅仅是为了修复问题。每个功能的实现都包含设计决策和合约，未来的 AI/开发者（developer）需要这些来安全执行。

---

## Spec 结构概览

```
.trellis/spec/
├── <layer>/           # 每层编码标准（如 backend/、frontend/、api/）
│   ├── index.md       # 概览和链接
│   └── *.md           # 特定主题 guideline
└── guides/            # 思维 checklist（非编码 spec！）
    ├── index.md       # Guide 索引
    └── *.md           # 特定主题 guide
```

### 关键：Code-Spec 与 Guide —— 认清区别

| 类型 | 位置 | 用途 | 内容风格 |
|------|----------|---------|---------------|
| **Code-Spec** | `<layer>/*.md` | 告诉 AI"如何安全实现" | 签名、合约、矩阵、案例、测试要点 |
| **Guide** | `guides/*.md` | 帮助 AI"思考什么" | Checklist、问题、指向 spec 的指针 |

**决策规则**：问自己：

- "这是关于**如何编写**代码" → 放入 spec layer 目录
- "这是关于编写之前**需要考虑什么**" → 放入 `guides/`

**示例**：

| 学到的内容 | 错误位置 | 正确位置 |
|----------|----------------|------------------|
| "此任务使用 API X 而非 API Y" | ❌ `guides/`（对于 thinking guide 来说过于具体） | ✅ 相关 spec 文件（具体 convention） |
| "做 Y 时记得检查 X" | ❌ Spec 文件（对于 spec 来说过于抽象） | ✅ `guides/`（思维 checklist） |

**Guide 应该是简短的 checklist，指向 spec**，而非重复详细规则。

---

## 更新流程

### 步骤 1：识别你学到了什么

回答以下问题：

1. **你学到了什么？**（具体）
2. **为什么重要？**（能预防什么问题？）
3. **应该放在哪里？**（哪个 spec 文件？）

### 步骤 2：归类更新类型

| 类型 | 描述 | 操作 |
|------|-------------|--------|
| **设计决策（Design Decision）** | 为什么选择方案 X 而非 Y | 添加到 "Design Decisions" 章节 |
| **项目惯例（Project Convention）** | 在此项目中我们如何做 X | 添加到相关章节并附带示例 |
| **新模式（New Pattern）** | 发现的可复用方法 | 添加到 "Patterns" 章节 |
| **禁止模式（Forbidden Pattern）** | 会引发问题的做法 | 添加到 "Anti-patterns" 或 "Don't" 章节 |
| **常见错误（Common Mistake）** | 容易犯的错误 | 添加到 "Common Mistakes" 章节 |
| **约定（Convention）** | 达成一致的标准 | 添加到相关章节 |
| **坑点（Gotcha）** | 不显而易见的行为 | 添加警告提示 |

### 步骤 3：阅读目标 Code-Spec

在编辑之前，先阅读当前的 code-spec 以：
- 了解现有结构
- 避免重复内容
- 为你的更新找到正确的章节

```bash
cat .trellis/spec/<category>/<file>.md
```

### 步骤 4：执行更新

遵循以下原则：

1. **具体**：包含具体示例，而非仅为抽象规则
2. **解释原因**：说明这能预防什么问题
3. **展示合约**：添加签名、payload 字段和错误行为
4. **展示代码**：为关键 pattern 添加代码片段
5. **保持简短**：每节一个概念

### 步骤 5：更新索引（如需要）

如果你添加了新章节或 code-spec 状态发生变化，更新该类别的 `index.md`。

---

## 更新模板

### 基础设施/跨层工作强制模板

```markdown
## Scenario: <name>

### 1. Scope / Trigger
- Trigger: <why this requires code-spec depth>

### 2. Signatures
- Backend command/API/DB signature(s)

### 3. Contracts
- Request fields (name, type, constraints)
- Response fields (name, type, constraints)
- Environment keys (required/optional)

### 4. Validation & Error Matrix
- <condition> -> <error>

### 5. Good/Base/Bad Cases
- Good: ...
- Base: ...
- Bad: ...

### 6. Tests Required
- Unit/Integration/E2E with assertion points

### 7. Wrong vs Correct
#### Wrong
...
#### Correct
...
```

### 添加设计决策

```markdown
### Design Decision: [Decision Name]

**Context**: What problem were we solving?

**Options Considered**:
1. Option A - brief description
2. Option B - brief description

**Decision**: We chose Option X because...

**Example**:
\`\`\`typescript
// How it's implemented
code example
\`\`\`

**Extensibility**: How to extend this in the future...
```

### 添加项目 Convention

```markdown
### Convention: [Convention Name]

**What**: Brief description of the convention.

**Why**: Why we do it this way in this project.

**Example**:
\`\`\`typescript
// How to follow this convention
code example
\`\`\`

**Related**: Links to related conventions or specs.
```

### 添加新 Pattern

```markdown
### Pattern Name

**Problem**: What problem does this solve?

**Solution**: Brief description of the approach.

**Example**:
\`\`\`
// Good
code example

// Bad
code example
\`\`\`

**Why**: Explanation of why this works better.
```

### 添加禁止 Pattern

```markdown
### Don't: Pattern Name

**Problem**:
\`\`\`
// Don't do this
bad code example
\`\`\`

**Why it's bad**: Explanation of the issue.

**Instead**:
\`\`\`
// Do this instead
good code example
\`\`\`
```

### 添加常见错误

```markdown
### Common Mistake: Description

**Symptom**: What goes wrong

**Cause**: Why this happens

**Fix**: How to correct it

**Prevention**: How to avoid it in the future
```

### 添加 Gotcha

```markdown
> **Warning**: Brief description of the non-obvious behavior.
>
> Details about when this happens and how to handle it.
```

---

## 交互模式

如果您不确定要更新什么，请回答以下提示：

1. **你刚刚完成了什么？**
   - [ ] 修复了一个 bug
   - [ ] 实现了一个功能
   - [ ] 重构了代码
   - [ ] 就方案进行了讨论

2. **你学到了或决定了什么？**
   - 设计决策（为什么选 X 而非 Y）
   - 项目 convention（我们如何做 X）
   - 不显而易见的行为（gotcha）
   - 更好的方法（pattern）

3. **未来的 AI/开发者需要知道这个吗？**
   - 理解代码如何工作 → 是，更新 spec
   - 维护或扩展功能 → 是，更新 spec
   - 避免重复犯错 → 是，更新 spec
   - 纯粹一次性实现细节 → 或许可以跳过

4. **它与哪个领域相关？**
   - [ ] 后端代码
   - [ ] 前端代码
   - [ ] 跨层数据流
   - [ ] 代码组织/复用
   - [ ] 质量/测试

---

## Quality Checklist

完成 code-spec 更新前：

- [ ] 内容是否具体且可操作？
- [ ] 是否包含了代码示例？
- [ ] 是否解释了 WHY，而不仅仅是 WHAT？
- [ ] 是否包含了可执行的签名/合约？
- [ ] 是否包含了验证和错误矩阵？
- [ ] 是否包含了 Good/Base/Bad 案例？
- [ ] 是否包含了带有断言要点的必需测试？
- [ ] 是否放在了正确的 code-spec 文件中？
- [ ] 是否与已有内容重复？
- [ ] 新团队成员能理解吗？

---

## 与其他命令的关系

```
Development Flow:
  Learn something → /trellis:update-spec → Knowledge captured
       ↑                                  ↓
  /trellis:break-loop ←──────────────────── Future sessions benefit
  (deep bug analysis)
```

- `/trellis:break-loop` - 深度分析 bug，通常会揭示需要更新的 spec
- `/trellis:update-spec` - 实际执行更新
- `/trellis:finish-work` - 提醒你检查 spec 是否需要更新

---

## 核心理念

> **Code-spec 是活文档。每一次调试 session、每一个"aha moment"都是让实现合约更清晰的机会。**

目标是**机构记忆（institutional memory）**：
- 一个人学到的，所有人受益
- AI 在一个 session 中学到的，持久化到未来的 session
- 错误变成文档化的护栏
