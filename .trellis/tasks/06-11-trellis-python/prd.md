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

* **Python 代码中文化方式**: 全部 docstring + 行内注释中文化，函数名/变量名保持英文
* **技术术语策略**: 术语保留英文，首次出现附中文注释标注（如 hook（钩子）、agent（智能体））
* **用户可见字符串**: 同时翻译注释 + print/log/错误消息等用户可见字符串，但保留 API 返回值、JSON key 等机器接口的原样
* **Markdown 翻译粒度**: 正文翻译为中文，代码块和 YAML frontmatter 保留原文

## 待确认问题

* Markdown 文档翻译粒度
* 验证方式

## 需求（逐步完善中）

* 所有 `.md` 文档翻译为简体中文
* 所有 `.py` 文件添加中文注释（docstring + 行内注释）

## 验收标准

* [ ] 所有 Markdown 文件内容为中文
* [ ] 所有 Python 文件有完整的中文 docstring 和行内注释
* [ ] Python 代码运行不受影响（仅注释变更）

## 完成定义

* 所有目标文件已处理
* Python 代码可正常运行
* 无遗漏文件

## 明确不包含

* `__pycache__/` 目录
* `.json`、`.yaml`、`.jsonl` 等纯数据/配置文件
* `.gitignore`、`.version`、`.template-hashes.json` 等元数据文件
* 修改函数名/变量名（保持英文）

## 技术笔记

* 文件清单已通过 Glob 获取
* 总行数已通过 wc -l 统计
