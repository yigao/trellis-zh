# 将 Trellis 文档和 Python 代码全部中文化

## 目标

将 `.trellis/` 和 `.claude/` 目录下的所有 Markdown 文档翻译为中文，对所有 Python 代码添加中文注释，使整个 Trellis 系统对中文开发者友好。

## 已知信息

* 用户 gaoyi 是中文开发者，希望 Trellis 系统完全中文化
* 范围：`.trellis/` + `.claude/` 全部文件
* Python 代码：~9,400 行（`.trellis/scripts/` 28 个文件 + `.claude/hooks/` 3 个文件）
* Markdown 文档：~5,300 行（`.trellis/` 21 个文件 + `.claude/` 32 个文件）
* 不含 `__pycache__/` 和 `.json`/`.yaml`/`.jsonl` 等数据文件

## 决策记录 (ADR-lite)

* **Python 代码中文化方式**: 全部 docstring + 行内注释中文化，函数名/变量名保持英文（选项 1）
* **技术术语策略**: 术语保留英文，首次出现附中文注释标注，如 hook（钩子）、agent（智能体）、spec（规范）、worktree（工作树）、PRD（产品需求文档）等（选项 1）
* **用户可见字符串**: 翻译注释 + print/log/错误消息等用户可见字符串，但保留 API 返回值、JSON key 等机器接口原样（选项 2）
* **Markdown 翻译粒度**: 正文翻译为中文，代码块（```...```）和 YAML frontmatter 保留原文（选项 1）
* **验证方式**: 代码可运行验证 + 关键文件抽样人工审查（选项 2）

## 需求

* 所有 `.md` 文档翻译为简体中文（正文部分）
* 所有 `.py` 文件添加中文 docstring + 行内注释
* 翻译用户可见的 print/log/错误消息等字符串，保留 API/JSON key 不动
* 代码块和 frontmatter 保留原文

## 验收标准

* [ ] 所有 Markdown 文件正文为中文
* [ ] 所有 Python 文件有完整的中文 docstring 和行内注释
* [ ] Python 代码运行不受影响（仅注释/字符串翻译）
* [ ] API 返回值、JSON key 等机器接口未改动

## 完成定义

* 所有 84 个目标文件已处理（31 个 .py + 53 个 .md）
* Python 代码语法无误、可正常运行
* 无遗漏文件

## 明确不包含

* `__pycache__/` 目录
* `.json`、`.yaml`、`.jsonl` 等纯数据/配置文件
* `.gitignore`、`.version`、`.template-hashes.json` 等元数据文件
* 修改函数名/变量名（保持英文）
* 修改 API 返回值结构

## 实施计划

* **第 1 批**: `.trellis/scripts/common/` 下 21 个 Python 文件 — 核心公共模块
* **第 2 批**: `.trellis/scripts/` 根目录下 7 个 Python 文件 — 入口脚本
* **第 3 批**: `.claude/hooks/` 下 3 个 Python 钩子文件
* **第 4 批**: `.trellis/` 下 Markdown 文档（spec、workflow、workspace 等）
* **第 5 批**: `.claude/` 下 Markdown 文档（skills、agents、commands）
* **第 6 批**: `.claude/skills/trellis-meta/references/` 下所有 Markdown 参考文档

## 技术笔记

* 文件清单已通过 Glob 获取
* 总行数已通过 wc -l 统计
* 翻译时注意保持术语一致性，建议先建立术语对照表
