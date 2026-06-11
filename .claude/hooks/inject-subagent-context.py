#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多平台子智能体（sub-agent）上下文注入钩子（hook）

在子智能体（implement、check、research）被派生时注入任务特定的上下文。

核心设计理念：
- Hook 负责注入所有上下文，子智能体以完整信息自主工作
- 每个智能体有一个专用的 JSONL 文件定义其上下文
- 无需恢复，无需分段，行为由代码而非提示词控制

触发时机：PreToolUse（Task 工具调用之前）

上下文来源：Trellis 活动任务（active task）解析器指向任务目录
- implement.jsonl - Implement 智能体专用上下文
- check.jsonl     - Check 智能体专用上下文
- prd.md          - 需求文档
- info.md         - 技术设计文档
- codex-review-output.txt - 代码审查结果
"""
from __future__ import annotations

# 重要：在最开始就抑制所有警告
import warnings
warnings.filterwarnings("ignore")

import json
import os
import sys
from pathlib import Path
from typing import Any

# 重要：在 Windows 上强制 stdout 使用 UTF-8
# 这修复了输出非 ASCII 字符时的 UnicodeEncodeError
if sys.platform.startswith("win"):
    import io as _io
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    elif hasattr(sys.stdout, "detach"):
        sys.stdout = _io.TextIOWrapper(sys.stdout.detach(), encoding="utf-8", errors="replace")  # type: ignore[union-attr]


# =============================================================================
# 路径常量（修改此处可重命名目录）
# =============================================================================

DIR_WORKFLOW = ".trellis"
DIR_SPEC = "spec"
FILE_TASK_JSON = "task.json"

# =============================================================================
# 子智能体常量（修改此处可重命名子智能体类型）
# =============================================================================

AGENT_IMPLEMENT = "trellis-implement"
AGENT_CHECK = "trellis-check"
AGENT_RESEARCH = "trellis-research"

# 需要任务目录的智能体
AGENTS_REQUIRE_TASK = (AGENT_IMPLEMENT, AGENT_CHECK)
# 所有支持的智能体
AGENTS_ALL = (AGENT_IMPLEMENT, AGENT_CHECK, AGENT_RESEARCH)


def find_repo_root(start_path: str) -> str | None:
    """
    从 start_path 向上查找 git 仓库（repository）根目录

    返回值：
        仓库根路径，未找到则返回 None
    """
    current = Path(start_path).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return str(current)
        current = current.parent
    return None


def _detect_platform(input_data: dict) -> str | None:
    if isinstance(input_data.get("cursor_version"), str):
        return "cursor"
    env_map = {
        "CLAUDE_PROJECT_DIR": "claude",
        "CURSOR_PROJECT_DIR": "cursor",
        "CODEBUDDY_PROJECT_DIR": "codebuddy",
        "FACTORY_PROJECT_DIR": "droid",
        "GEMINI_PROJECT_DIR": "gemini",
        "QODER_PROJECT_DIR": "qoder",
        "KIRO_PROJECT_DIR": "kiro",
        "COPILOT_PROJECT_DIR": "copilot",
    }
    for env_name, platform in env_map.items():
        if os.environ.get(env_name):
            return platform
    script_parts = set(Path(sys.argv[0]).parts)
    if ".claude" in script_parts:
        return "claude"
    if ".cursor" in script_parts:
        return "cursor"
    if ".gemini" in script_parts:
        return "gemini"
    if ".qoder" in script_parts:
        return "qoder"
    if ".codebuddy" in script_parts:
        return "codebuddy"
    if ".factory" in script_parts:
        return "droid"
    if ".kiro" in script_parts:
        return "kiro"
    return None


def get_current_task(repo_root: str, input_data: dict) -> str | None:
    """通过统一的活动任务解析器解析当前任务（current task）目录。"""
    scripts_dir = Path(repo_root) / DIR_WORKFLOW / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from common.active_task import resolve_active_task  # type: ignore[import-not-found]
    except Exception:
        return None

    active = resolve_active_task(
        Path(repo_root),
        input_data,
        platform=_detect_platform(input_data),
    )
    return active.task_path


def read_file_content(base_path: str, file_path: str) -> str | None:
    """读取文件内容，文件不存在则返回 None"""
    full_path = os.path.join(base_path, file_path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None
    return None


def read_directory_contents(
    base_path: str, dir_path: str, max_files: int = 20
) -> list[tuple[str, str]]:
    """
    读取目录中所有 .md 文件

    参数：
        base_path: 基础路径（通常是 repo_root）
        dir_path: 目录相对路径
        max_files: 最大读取文件数（防止目录过大）

    返回值：
        [(file_path, content), ...]
    """
    full_path = os.path.join(base_path, dir_path)
    if not os.path.exists(full_path) or not os.path.isdir(full_path):
        return []

    results = []
    try:
        # 仅读取 .md 文件，按文件名排序
        md_files = sorted(
            [
                f
                for f in os.listdir(full_path)
                if f.endswith(".md") and os.path.isfile(os.path.join(full_path, f))
            ]
        )

        for filename in md_files[:max_files]:
            file_full_path = os.path.join(full_path, filename)
            relative_path = os.path.join(dir_path, filename)
            try:
                with open(file_full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    results.append((relative_path, content))
            except Exception:
                continue
    except Exception:
        pass

    return results


def read_jsonl_entries(base_path: str, jsonl_path: str) -> list[tuple[str, str]]:
    """
    读取 JSONL 文件中引用的所有文件/目录内容

    结构定义：
        {"file": "path/to/file.md", "reason": "..."}
        {"file": "path/to/dir/", "type": "directory", "reason": "..."}
        {"_example": "..."}          # 种子行 — 跳过（无 `file` 字段）

    不含 ``file`` 字段的行（例如 ``task.py create`` 在智能体整理条目之前
    写入的自描述种子行）将被静默跳过。如果结果条目列表为空，将向 stderr
    输出一条警告，以便操作者调试缺失的上下文。

    返回值：
        [(path, content), ...]
    """
    full_path = os.path.join(base_path, jsonl_path)
    if not os.path.exists(full_path):
        print(
            f"[inject-subagent-context] 警告: {jsonl_path} 未找到 — "
            f"子智能体将仅收到 prd.md",
            file=sys.stderr,
        )
        return []

    results = []
    saw_real_entry = False
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    file_path = item.get("file") or item.get("path")
                    entry_type = item.get("type", "file")

                    if not file_path:
                        # 种子/注释行 — 静默跳过
                        continue

                    saw_real_entry = True
                    if entry_type == "directory":
                        # 读取目录中所有 .md 文件
                        dir_contents = read_directory_contents(base_path, file_path)
                        results.extend(dir_contents)
                    else:
                        # 读取单个文件
                        content = read_file_content(base_path, file_path)
                        if content:
                            results.append((file_path, content))
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    if not saw_real_entry:
        print(
            f"[inject-subagent-context] 警告: {jsonl_path} 没有已整理的条目"
            f"（仅有种子/空行）— 子智能体将仅收到"
            f"prd.md。请参阅 workflow.md 阶段 1.3 了解整理指南。",
            file=sys.stderr,
        )

    return results




def get_agent_context(repo_root: str, task_dir: str, agent_type: str) -> str:
    """
    从指定智能体的 {agent_type}.jsonl 获取上下文。
    仅读取 implement.jsonl 或 check.jsonl（任务系统创建的两个 JSONL 文件）。
    """
    context_parts = []

    agent_jsonl = f"{task_dir}/{agent_type}.jsonl"
    for file_path, content in read_jsonl_entries(repo_root, agent_jsonl):
        context_parts.append(f"=== {file_path} ===\n{content}")

    return "\n\n".join(context_parts)


def get_implement_context(repo_root: str, task_dir: str) -> str:
    """
    Implement 智能体的完整上下文

    读取顺序：
    1. implement.jsonl 中的所有文件（开发规范）
    2. prd.md（需求文档）
    3. info.md（技术设计文档）
    """
    context_parts = []

    # 1. 读取 implement.jsonl
    base_context = get_agent_context(repo_root, task_dir, "implement")
    if base_context:
        context_parts.append(base_context)

    # 2. 需求文档
    prd_content = read_file_content(repo_root, f"{task_dir}/prd.md")
    if prd_content:
        context_parts.append(f"=== {task_dir}/prd.md (需求文档) ===\n{prd_content}")

    # 3. 技术设计文档
    info_content = read_file_content(repo_root, f"{task_dir}/info.md")
    if info_content:
        context_parts.append(
            f"=== {task_dir}/info.md (技术设计文档) ===\n{info_content}"
        )

    return "\n\n".join(context_parts)


def get_check_context(repo_root: str, task_dir: str) -> str:
    """
    Check 智能体上下文：check.jsonl + prd.md
    """
    context_parts = []

    for file_path, content in read_jsonl_entries(repo_root, f"{task_dir}/check.jsonl"):
        context_parts.append(f"=== {file_path} ===\n{content}")

    prd_content = read_file_content(repo_root, f"{task_dir}/prd.md")
    if prd_content:
        context_parts.append(f"=== {task_dir}/prd.md (需求文档) ===\n{prd_content}")

    return "\n\n".join(context_parts)


def get_finish_context(repo_root: str, task_dir: str) -> str:
    """
    Finish 阶段的上下文：复用 check.jsonl + prd.md
    （Finish 是最终检查，使用相同的上下文来源。）
    """
    return get_check_context(repo_root, task_dir)



def build_implement_prompt(original_prompt: str, context: str) -> str:
    """为 Implement 构建完整的提示词"""
    return f"""<!-- trellis-hook-injected -->
# Implement 智能体任务

你是多智能体管线中的 Implement 智能体。

## 你的上下文

以下是你需要了解的所有信息：

{context}

---

## 你的任务

{original_prompt}

---

## 工作流

1. **理解规范** - 所有开发规范（spec）已在上方注入，请认真理解
2. **理解需求** - 阅读需求文档和技术设计文档
3. **实现功能** - 遵循规范和设计进行实现
4. **自检** - 对照检查规范确保代码质量

## 重要约束

- 不要执行 git commit，仅做代码修改
- 遵循上方注入的所有开发规范
- 完成后报告修改/创建的文件列表"""


def build_check_prompt(original_prompt: str, context: str) -> str:
    """为 Check 构建完整的提示词"""
    return f"""<!-- trellis-hook-injected -->
# Check 智能体任务

你是多智能体管线中的 Check 智能体（代码和跨层检查器）。

## 你的上下文

以下是所有你需要的检查规范和开发规范：

{context}

---

## 你的任务

{original_prompt}

---

## 工作流

1. **获取变更** - 运行 `git diff --name-only` 和 `git diff` 获取代码变更
2. **对照规范检查** - 逐项对照上方规范进行检查
3. **自行修复** - 直接修复问题，而非仅报告
4. **运行验证** - 运行项目的 lint 和 typecheck 命令

## 重要约束

- 自己修复问题，不要仅报告
- 必须执行检查规范中的完整检查清单
- 特别注意影响范围分析（L1-L5）"""


def build_finish_prompt(original_prompt: str, context: str) -> str:
    """为 Finish（PR 前的最终检查）构建完整的提示词"""
    return f"""<!-- trellis-hook-injected -->
# Finish 智能体任务

你正在创建 PR 之前执行最终检查。

## 你的上下文

Finish 检查清单和需求：

{context}

---

## 你的任务

{original_prompt}

---

## 工作流

1. **审查变更** - 运行 `git diff --name-only` 查看所有变更文件
2. **验证需求** - 逐一检查 prd.md 中的每条需求是否已实现
3. **规范同步** - 分析变更是否引入了新模式、新约定或新惯例
   - 如果发现新模式/约定：读取目标 spec 文件 → 更新它 → 必要时更新 index.md
   - 如果是基础设施/跨层变更：遵循 update-spec.md 中的 7 段式强制模板
   - 如果是纯代码修复且无新模式：跳过此步
4. **运行最终检查** - 执行 lint 和 typecheck
5. **确认就绪** - 确保代码已准备好提交 PR

## 重要约束

- 当发现规范缺口时可以更新 spec 文件（以 update-spec.md 为指南）
- 编辑前必须先读取目标 spec 文件（避免重复已有内容）
- 不要为微小变更（拼写错误、格式调整、明显修复）更新规范
- 如果发现严重的代码问题，明确报告（修复规范而非代码）
- 验证 prd.md 中的所有验收标准均已满足"""



def get_research_context(repo_root: str, task_dir: str | None) -> str:
    """
    Research 智能体上下文 — 规范（spec）目录的项目结构概览。

    `task_dir` 参数保留是为了与 get_implement_context / get_check_context
    保持签名一致，以便调度器可以统一调用。
    """
    _ = task_dir
    context_parts = []

    # 1. 项目结构概览（动态发现 spec 目录）
    spec_path = f"{DIR_WORKFLOW}/{DIR_SPEC}"
    spec_root = Path(repo_root) / DIR_WORKFLOW / DIR_SPEC

    # 动态构建 spec 树
    tree_lines = [f"{spec_path}/"]
    if spec_root.is_dir():
        pkg_dirs = sorted(d for d in spec_root.iterdir() if d.is_dir())
        for i, pkg_dir in enumerate(pkg_dirs):
            is_last = i == len(pkg_dirs) - 1
            prefix = "└── " if is_last else "├── "
            layers = sorted(d.name for d in pkg_dir.iterdir() if d.is_dir())
            layer_info = f" ({', '.join(layers)})" if layers else ""
            tree_lines.append(f"{prefix}{pkg_dir.name}/{layer_info}")

    spec_tree = "\n".join(tree_lines)

    project_structure = f"""## 项目 Spec 目录结构

```
{spec_tree}
```

获取结构化的软件包（package）信息，运行：`py -3 ./{DIR_WORKFLOW}/scripts/get_context.py --mode packages`

## 搜索提示

- Spec 文件：`{spec_path}/**/*.md`
- 代码搜索：使用 Glob 和 Grep 工具
- 技术方案：使用 mcp__exa__web_search_exa 或 mcp__exa__get_code_context_exa"""

    context_parts.append(project_structure)

    return "\n\n".join(context_parts)


def build_research_prompt(original_prompt: str, context: str) -> str:
    """为 Research 构建完整的提示词"""
    return f"""# Research 智能体任务

你是多智能体管线中的 Research 智能体（搜索研究员）。

## 核心原则

**你只做一件事：查找和解释信息。**

你是记录者，不是审查者。

## 项目信息

{context}

---

## 你的任务

{original_prompt}

---

## 工作流

1. **理解查询** - 确定搜索类型（内部/外部）和范围
2. **规划搜索** - 对复杂查询列出搜索步骤
3. **执行搜索** - 并行执行多个独立搜索
4. **整理结果** - 输出结构化的报告

## 搜索工具

| 工具 | 用途 |
|------|------|
| Glob | 按文件名模式搜索 |
| Grep | 按内容搜索 |
| Read | 读取文件内容 |
| mcp__exa__web_search_exa | 外部网页搜索 |
| mcp__exa__get_code_context_exa | 外部代码/文档搜索 |

## 严格边界

**仅允许**：描述存在什么、在哪里、如何工作

**禁止**（除非明确要求）：
- 提出改进建议
- 批评实现方式
- 建议重构
- 修改任何文件

## 报告格式

提供结构化的搜索结果，包括：
- 找到的文件列表（含路径）
- 代码模式分析（如适用）
- 相关 spec 文档
- 外部参考（如有）"""


def _string_value(value: Any) -> str:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped
    return ""


def _extract_subagent_name(value: Any) -> str:
    """从常见平台编码中提取子智能体名称。

    Cursor 的原生 Task 参数将自定义子智能体编码为 protobuf oneof，
    在 hook 的 JSON 中可能表现为 ``{"custom": {"name": "..."}}``
    或 ``{"type": {"case": "custom", "value": {"name": "..."}}}``。
    """
    direct = _string_value(value)
    if direct:
        return direct

    if not isinstance(value, dict):
        return ""

    for key in ("name", "subagent_type_name", "subagentTypeName"):
        direct = _string_value(value.get(key))
        if direct:
            return direct

    custom = value.get("custom")
    if isinstance(custom, dict):
        custom_name = _string_value(custom.get("name"))
        if custom_name:
            return custom_name

    oneof = value.get("type")
    if isinstance(oneof, dict):
        case_name = _string_value(oneof.get("case"))
        if case_name == "custom":
            nested_value = oneof.get("value")
            if isinstance(nested_value, dict):
                custom_name = _string_value(nested_value.get("name"))
                if custom_name:
                    return custom_name
        if case_name:
            return case_name

    case_name = _string_value(value.get("case"))
    if case_name == "custom":
        nested_value = value.get("value")
        if isinstance(nested_value, dict):
            custom_name = _string_value(nested_value.get("name"))
            if custom_name:
                return custom_name
    if case_name:
        return case_name

    for agent_name in AGENTS_ALL:
        if agent_name in value:
            return agent_name

    return ""


def _extract_subagent_type(tool_input: dict) -> str:
    for key in (
        "subagent_type",
        "subagentType",
        "subagent_type_name",
        "subagentTypeName",
        "agent_type",
        "agentType",
        "name",
    ):
        agent_name = _extract_subagent_name(tool_input.get(key))
        if agent_name:
            return agent_name
    return ""


def _parse_hook_input(input_data: dict) -> tuple[str, str, dict]:
    """解析不同平台格式的 hook 输入。

    返回值 (subagent_type, original_prompt, tool_input)。
    处理以下平台：
    - Claude Code / Qoder / CodeBuddy / Droid: tool_name=Task|Agent, tool_input.subagent_type
    - Cursor: tool_name=Task|Subagent, tool_input.subagent_type
    - Copilot CLI: toolName=task（camelCase 键名，小写值）
    - Gemini CLI: tool_name 即智能体名称（BeforeTool 匹配器已过滤）
    - Kiro: agentSpawn hook，agent_name 字段在顶层
    """
    tool_input = input_data.get("tool_input", {})

    # 标准格式：Task/Agent 工具，带 subagent_type
    tool_name = input_data.get("tool_name", "") or input_data.get("toolName", "")
    if tool_name.lower() in ("task", "agent", "subagent"):
        return (
            _extract_subagent_type(tool_input),
            tool_input.get("prompt", ""),
            tool_input,
        )

    # Kiro：agentSpawn hook 在顶层传递 agent_name
    agent_name = input_data.get("agent_name", "")
    if agent_name:
        return agent_name, tool_input.get("prompt", input_data.get("prompt", "")), tool_input

    # Gemini CLI：BeforeTool 中 tool_name 就是智能体名称
    # （匹配器已确保是我们的智能体之一）
    if tool_name in AGENTS_ALL:
        return tool_name, tool_input.get("prompt", ""), tool_input

    # Copilot CLI：toolName 字段（camelCase），值可能是智能体名称
    tool_name_camel = input_data.get("toolName", "")
    if tool_name_camel in AGENTS_ALL:
        return tool_name_camel, input_data.get("toolArgs", ""), tool_input

    return "", "", tool_input


def main():
    if os.environ.get("TRELLIS_HOOKS") == "0" or os.environ.get("TRELLIS_DISABLE_HOOKS") == "1":
        sys.exit(0)

    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    subagent_type, original_prompt, tool_input = _parse_hook_input(input_data)
    cwd = input_data.get("cwd", os.getcwd())

    # 仅处理我们关注的子智能体类型
    if subagent_type not in AGENTS_ALL:
        sys.exit(0)

    # 查找仓库根目录
    repo_root = find_repo_root(cwd)
    if not repo_root:
        sys.exit(0)

    # 获取当前任务目录（research 不需要任务目录）
    task_dir = get_current_task(repo_root, input_data)

    # implement/check 需要任务目录
    if subagent_type in AGENTS_REQUIRE_TASK:
        if not task_dir:
            sys.exit(0)
        # 检查任务目录是否存在
        task_dir_full = os.path.join(repo_root, task_dir)
        if not os.path.exists(task_dir_full):
            sys.exit(0)

    # 检查提示词中是否有 [finish] 标记（check 智能体使用 finish 上下文）
    is_finish_phase = "[finish]" in original_prompt.lower()

    # 根据子智能体类型获取上下文并构建提示词
    if subagent_type == AGENT_IMPLEMENT:
        assert task_dir is not None  # 上文已验证
        context = get_implement_context(repo_root, task_dir)
        new_prompt = build_implement_prompt(original_prompt, context)
    elif subagent_type == AGENT_CHECK:
        assert task_dir is not None  # 上文已验证
        if is_finish_phase:
            # Finish 阶段：使用 finish 上下文（更轻量，专注于最终验证）
            context = get_finish_context(repo_root, task_dir)
            new_prompt = build_finish_prompt(original_prompt, context)
        else:
            # 常规检查阶段：使用 check 上下文（完整规范用于自修复循环）
            context = get_check_context(repo_root, task_dir)
            new_prompt = build_check_prompt(original_prompt, context)
    elif subagent_type == AGENT_RESEARCH:
        # Research 可以在没有任务目录的情况下工作
        context = get_research_context(repo_root, task_dir)
        new_prompt = build_research_prompt(original_prompt, context)
    else:
        sys.exit(0)

    if not context:
        sys.exit(0)

    # 返回更新后的输入 — 使用覆盖所有平台的多格式输出。
    # 大多数平台会忽略无法识别的字段，因此我们包含多种格式。
    # 平台会选择自己能理解的字段。
    updated = {**tool_input, "prompt": new_prompt}
    output = {
        # Claude Code / Qoder / CodeBuddy / Droid 格式
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": updated,
        },
        # Cursor 格式
        "permission": "allow",
        "updated_input": updated,
        # Gemini 格式
        "updatedInput": updated,
    }

    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
