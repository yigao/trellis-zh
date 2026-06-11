# 工作区索引

> 所有开发者的全部 AI 智能体工作记录

---

## 概览

此目录追踪本项目中使用 AI 智能体的所有开发者记录。

### 文件结构

```
workspace/
|-- index.md              # 本文件 - 主索引
+-- {developer}/          # 每个开发者的目录
    |-- index.md          # 个人索引，含 session 历史
    |-- tasks/            # 任务文件
    |   |-- *.json        # 活跃 task
    |   +-- archive/      # 按月份归档的 task
    +-- journal-N.md      # 日志文件（按序号：1、2、3……）
```

---

## 活跃开发者

| 开发者 | 最后活跃 | Session 数 | 活跃文件 |
|-----------|-------------|----------|-------------|
| （暂无） | - | - | - |

---

## 入门指南

### 新开发者

运行初始化脚本：

```bash
py -3 ./.trellis/scripts/init_developer.py <your-name>
```

这将：
1. 创建你的身份文件（gitignored）
2. 创建你的进度目录
3. 创建你的个人索引
4. 创建初始 journal 文件

### 回归开发者

1. 获取你的开发者名称：
   ```bash
   py -3 ./.trellis/scripts/get_developer.py
   ```

2. 读取你的个人索引：
   ```bash
   cat .trellis/workspace/$(py -3 ./.trellis/scripts/get_developer.py)/index.md
   ```

---

## 指南

### 日志文件规则

- 每个 journal 文件**最多 2000 行**
- 达到上限后，创建 `journal-{N+1}.md`
- 创建新文件时更新你的个人 `index.md`

### Session 记录格式

每个 session 应包含：
- 摘要：一句话描述
- 分支：工作在哪个 `branch（分支）` 上
- 主要变更：修改了什么
- Git 提交：提交哈希和消息
- 下一步：接下来要做什么

---

## Session 模板

记录 session 时使用此模板：

```markdown
## Session {N}: {Title}

**Date**: YYYY-MM-DD
**Task**: {task-name}
**Branch**: `{branch-name}`

### Summary

{One-line summary}

### Main Changes

- {Change 1}
- {Change 2}

### Git Commits

| Hash | Message |
|------|---------|
| `abc1234` | {commit message} |

### Testing

- [OK] {Test result}

### Status

[OK] **Completed** / # **In Progress** / [P] **Blocked**

### Next Steps

- {Next step 1}
- {Next step 2}
```

---

**语言**：所有文档必须用 **English** 编写。
