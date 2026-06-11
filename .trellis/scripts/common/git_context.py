#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git 和会话上下文工具。

入口适配层 — 委托给 session_context 和 packages_context。

提供：
    output_json - 以 JSON 格式输出上下文
    output_text - 以文本格式输出上下文
"""

from __future__ import annotations

import json

from .git import run_git
from .session_context import (
    get_context_json,
    get_context_text,
    get_context_record_json,
    get_context_text_record,
    output_json,
    output_text,
)
from .packages_context import (
    get_context_packages_text,
    get_context_packages_json,
)
from .trellis_config import read_trellis_config
from .workflow_phase import (
    filter_platform,
    get_phase_index,
    get_step,
    resolve_effective_platform,
)

# 向后兼容的别名 — 外部模块导入此名称
_run_git_command = run_git


# =============================================================================
# 主入口
# =============================================================================

def main() -> None:
    """CLI 入口点。"""
    import argparse

    parser = argparse.ArgumentParser(description="获取 AI 智能体（agent）的会话上下文")
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="以 JSON 格式输出（适用于任何 --mode）",
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["default", "record", "packages", "phase"],
        default="default",
        help="输出模式：default（完整上下文）、record（用于 record-session）、packages（仅软件包信息）、phase（工作流步骤提取）",
    )
    parser.add_argument(
        "--step",
        help="用于 --mode phase 的步骤 ID，例如 1.1、2.2。省略则获取阶段（phase）索引。",
    )
    parser.add_argument(
        "--platform",
        help="用于 --mode phase 的平台名称，例如 cursor、claude-code。过滤带有平台标记的块。",
    )

    args = parser.parse_args()

    if args.mode == "record":
        if args.json:
            print(json.dumps(get_context_record_json(), indent=2, ensure_ascii=False))
        else:
            print(get_context_text_record())
    elif args.mode == "packages":
        if args.json:
            print(json.dumps(get_context_packages_json(), indent=2, ensure_ascii=False))
        else:
            print(get_context_packages_text())
    elif args.mode == "phase":
        content = get_step(args.step) if args.step else get_phase_index()
        if not content.strip():
            if args.step:
                parser.exit(2, f"未找到步骤：{args.step}\n")
            else:
                parser.exit(2, "在 workflow.md 中未找到阶段索引部分\n")
        if args.platform:
            effective = resolve_effective_platform(
                args.platform, read_trellis_config()
            )
            content = filter_platform(content, effective)
        print(content, end="")
    else:
        if args.json:
            output_json()
        else:
            output_text()


if __name__ == "__main__":
    main()
