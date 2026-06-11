#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流（Workflow）阶段提取。

从 .trellis/workflow.md 中提取步骤级别的内容，并可选择性地过滤
平台特定块。

workflow.md 中的平台标记语法:

    [Claude Code, Cursor, ...]
    智能体（agent）可用的内容
    [/Claude Code, Cursor, ...]

提供:
    get_phase_index   - 提取 Phase Index 部分（无 --step）
    get_step          - 提取单个步骤（#### X.X）部分
    filter_platform   - 移除不包含给定平台名称的平台块
"""

from __future__ import annotations

import re

from .paths import DIR_WORKFLOW, get_repo_root


def _workflow_md_path():
    return get_repo_root() / DIR_WORKFLOW / "workflow.md"

# 匹配平台标记行: "[A, B, C]" 或 "[/A, B, C]"
_MARKER_RE = re.compile(r"^\[(/?)([A-Za-z][^\[\]]*)\]\s*$")

# 步骤标题: "#### 1.0 Title" 或 "#### 1.0 ..."
_STEP_HEADING_RE = re.compile(r"^####\s+(\d+\.\d+)\b.*$")

# Phase Index 从这里开始；Phase 1/2/3 步骤主体跟随；在 Breadcrumbs 处结束。
_PHASE_INDEX_HEADING = "## Phase Index"


def _read_workflow() -> str:
    path = _workflow_md_path()
    if not path.exists():
        raise FileNotFoundError(f"workflow.md 未找到: {path}")
    return path.read_text(encoding="utf-8")


def _parse_marker(line: str) -> tuple[bool, list[str]] | None:
    """解析平台标记行。

    返回:
        (is_closing, [platform_names]) 如果该行是标记，否则返回 None。
    """
    m = _MARKER_RE.match(line)
    if not m:
        return None
    is_closing = m.group(1) == "/"
    names = [p.strip() for p in m.group(2).split(",") if p.strip()]
    return is_closing, names


def get_phase_index() -> str:
    """从 workflow.md 返回 Phase Index + Phase 1/2/3 步骤主体。

    匹配 SessionStart 钩子（hook）注入到 `<workflow>` 块中的内容:
    从 `## Phase Index` 开始，经过 `## Phase 1: Plan`、
    `## Phase 2: Execute`、`## Phase 3: Finish`，
    在 `## Customizing Trellis (for forks)`（面向 fork 的文档页脚）处停止。
    `[workflow-state:STATUS]` 标签块（自 v0.5.0-rc.0 起嵌入在 Phase Index 中）
    由 UserPromptSubmit hook 消费，因此从此输出中剥离。
    """
    text = _read_workflow()
    lines = text.splitlines()

    start: int | None = None
    end: int | None = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if start is None and stripped == _PHASE_INDEX_HEADING:
            start = i
            continue
        if start is not None and stripped == "## Customizing Trellis (for forks)":
            end = i
            break

    if start is None:
        return ""
    if end is None:
        end = len(lines)

    section = "\n".join(lines[start:end]).rstrip()
    # 剥离 [workflow-state:STATUS]...[/workflow-state:STATUS] 块，
    # 因为它们由 inject-workflow-state.py 每轮单独注入。
    import re as _re
    tag_re = _re.compile(
        r"\[workflow-state:([A-Za-z0-9_-]+)\]\s*\n.*?\n\s*\[/workflow-state:\1\]\n?",
        _re.DOTALL,
    )
    return tag_re.sub("", section).rstrip() + "\n"


def get_step(step_id: str) -> str:
    """返回匹配 step_id 的 `#### X.X` 部分（标题 + 主体）。

    主体在下一个 `####` 或 `---` 或 `##` 标题处结束（以先出现者为准）。
    """
    text = _read_workflow()
    lines = text.splitlines()

    start: int | None = None
    for i, line in enumerate(lines):
        m = _STEP_HEADING_RE.match(line)
        if m and m.group(1) == step_id:
            start = i
            break
    if start is None:
        return ""

    end: int = len(lines)
    for j in range(start + 1, len(lines)):
        line = lines[j]
        if line.startswith("#### "):
            end = j
            break
        if line.startswith("## "):
            end = j
            break
        # 第 0 列的水平分割线
        if line.strip() == "---":
            end = j
            break

    return "\n".join(lines[start:end]).rstrip() + "\n"


def _platform_matches(platform: str, block_names: list[str]) -> bool:
    """不区分大小写的模糊匹配: 接受 'cursor'、'Cursor'、'claude-code'、'Claude Code'。"""
    needle = platform.lower().replace("-", "").replace("_", "").replace(" ", "")
    for name in block_names:
        hay = name.lower().replace("-", "").replace("_", "").replace(" ", "")
        if needle == hay:
            return True
    return False


def resolve_effective_platform(platform: str, config: dict) -> str:
    """将 ``codex`` 映射到调度模式命名空间的虚拟平台名称。

    当传入 ``--platform codex`` 时，根据 ``.trellis/config.yaml`` 中的
    ``codex.dispatch_mode`` 返回 ``"codex-inline"``（默认）或
    ``"codex-sub-agent"``。然后 ``filter_platform`` 会展示标记列表中
    包含该命名空间名称的块（例如 ``[codex-sub-agent, ...]`` 或
    ``[codex-inline, Kilo, Antigravity, Windsurf]``）。

    默认为 ``inline``，因为 Codex 子智能体（sub-agent）以
    ``fork_turns="none"`` 隔离方式运行，无法继承父会话的
    任务上下文 — inline 模式保持主智能体掌控，这样上下文不会丢失。
    无效/缺失的值也会回退到 inline。

    其他平台原样返回。
    """
    if platform == "codex":
        mode = "inline"
        codex_cfg = config.get("codex") if isinstance(config, dict) else None
        if isinstance(codex_cfg, dict):
            cfg_mode = codex_cfg.get("dispatch_mode")
            if cfg_mode in ("inline", "sub-agent"):
                mode = cfg_mode
        return f"codex-{mode}"
    return platform


def filter_platform(content: str, platform: str) -> str:
    """保留在任何 `[...]` 块之外的行 + 包含该平台的块内的行。

    标记行本身从输出中丢弃。
    """
    lines = content.splitlines()
    out: list[str] = []

    in_block = False
    keep_block = False

    for line in lines:
        marker = _parse_marker(line)
        if marker is not None:
            is_closing, names = marker
            if not is_closing:
                in_block = True
                keep_block = _platform_matches(platform, names)
            else:
                in_block = False
                keep_block = False
            continue  # 丢弃标记行本身

        if in_block:
            if keep_block:
                out.append(line)
            continue
        out.append(line)

    # 合并因丢弃标记而产生的 3 个以上连续空行
    collapsed: list[str] = []
    blank_run = 0
    for line in out:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= 2:
                collapsed.append(line)
        else:
            blank_run = 0
            collapsed.append(line)

    return "\n".join(collapsed).rstrip() + "\n"
