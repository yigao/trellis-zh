#!/usr/bin/env python3
"""
任务 JSONL 上下文（context）管理。

提供：
    cmd_add_context   - 向 JSONL 上下文文件添加条目
    cmd_validate      - 验证 JSONL 上下文文件
    cmd_list_context  - 列出 JSONL 上下文条目

注意：
    ``cmd_init_context`` 已在 v0.5.0-beta.12 中移除。JSONL 上下文文件
    现在在 ``task.py create`` 时以自描述的 ``_example`` 行播种；
    AI 代理在工作流（workflow）的 Phase 1.3 中管理实际条目。
    参见 ``.trellis/workflow.md`` Phase 1.3 了解当前说明。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .log import Colors, colored
from .paths import get_repo_root
from .task_utils import resolve_task_dir


# =============================================================================
# 命令：add-context
# =============================================================================

def cmd_add_context(args: argparse.Namespace) -> int:
    """向 JSONL 上下文文件添加条目。"""
    repo_root = get_repo_root()
    target_dir = resolve_task_dir(args.dir, repo_root)

    jsonl_name = args.file
    path = args.path
    reason = args.reason or "手动添加"

    if not target_dir.is_dir():
        print(colored(f"错误：目录未找到：{target_dir}", Colors.RED))
        return 1

    # 支持简写
    if not jsonl_name.endswith(".jsonl"):
        jsonl_name = f"{jsonl_name}.jsonl"

    jsonl_file = target_dir / jsonl_name
    full_path = repo_root / path

    entry_type = "file"
    if full_path.is_dir():
        entry_type = "directory"
        if not path.endswith("/"):
            path = f"{path}/"
    elif not full_path.is_file():
        print(colored(f"错误：路径未找到：{path}", Colors.RED))
        return 1

    # 检查是否已存在
    if jsonl_file.is_file():
        content = jsonl_file.read_text(encoding="utf-8")
        if f'"{path}"' in content:
            print(colored(f"警告：{path} 的条目已存在", Colors.YELLOW))
            return 0

    # 添加条目
    entry: dict
    if entry_type == "directory":
        entry = {"file": path, "type": "directory", "reason": reason}
    else:
        entry = {"file": path, "reason": reason}

    with jsonl_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(colored(f"已添加 {entry_type}：{path}", Colors.GREEN))
    return 0


# =============================================================================
# 命令：validate
# =============================================================================

def cmd_validate(args: argparse.Namespace) -> int:
    """验证 JSONL 上下文文件。"""
    repo_root = get_repo_root()
    target_dir = resolve_task_dir(args.dir, repo_root)

    if not target_dir.is_dir():
        print(colored("错误：需要任务目录", Colors.RED))
        return 1

    print(colored("=== 验证上下文文件 ===", Colors.BLUE))
    print(f"目标目录：{target_dir}")
    print()

    total_errors = 0
    for jsonl_name in ["implement.jsonl", "check.jsonl"]:
        jsonl_file = target_dir / jsonl_name
        errors = _validate_jsonl(jsonl_file, repo_root)
        total_errors += errors

    print()
    if total_errors == 0:
        print(colored("✓ 所有验证通过", Colors.GREEN))
        return 0
    else:
        print(colored(f"✗ 验证失败（{total_errors} 个错误）", Colors.RED))
        return 1


def _validate_jsonl(jsonl_file: Path, repo_root: Path) -> int:
    """验证单个 JSONL 文件。

    种子行（没有 ``file`` 字段 — 通常是 ``{"_example": "..."}``）
    会被静默跳过；它们是自描述的注释，不是实际条目。
    """
    file_name = jsonl_file.name
    errors = 0

    if not jsonl_file.is_file():
        print(f"  {colored(f'{file_name}：未找到（已跳过）', Colors.YELLOW)}")
        return 0

    line_num = 0
    real_entries = 0
    for line in jsonl_file.read_text(encoding="utf-8").splitlines():
        line_num += 1
        if not line.strip():
            continue

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            print(f"  {colored(f'{file_name}:{line_num}：无效的 JSON', Colors.RED)}")
            errors += 1
            continue

        file_path = data.get("file")
        entry_type = data.get("type", "file")

        if not file_path:
            # 种子 / 注释行 — 静默跳过
            continue

        real_entries += 1
        full_path = repo_root / file_path
        if entry_type == "directory":
            if not full_path.is_dir():
                print(f"  {colored(f'{file_name}:{line_num}：目录未找到：{file_path}', Colors.RED)}")
                errors += 1
        else:
            if not full_path.is_file():
                print(f"  {colored(f'{file_name}:{line_num}：文件未找到：{file_path}', Colors.RED)}")
                errors += 1

    if errors == 0:
        print(f"  {colored(f'{file_name}：✓（{real_entries} 个条目）', Colors.GREEN)}")
    else:
        print(f"  {colored(f'{file_name}：✗（{errors} 个错误）', Colors.RED)}")

    return errors


# =============================================================================
# 命令：list-context
# =============================================================================

def cmd_list_context(args: argparse.Namespace) -> int:
    """列出 JSONL 上下文条目。"""
    repo_root = get_repo_root()
    target_dir = resolve_task_dir(args.dir, repo_root)

    if not target_dir.is_dir():
        print(colored("错误：需要任务目录", Colors.RED))
        return 1

    print(colored("=== 上下文文件 ===", Colors.BLUE))
    print()

    for jsonl_name in ["implement.jsonl", "check.jsonl"]:
        jsonl_file = target_dir / jsonl_name
        if not jsonl_file.is_file():
            continue

        print(colored(f"[{jsonl_name}]", Colors.CYAN))

        count = 0
        seed_only = True
        for line in jsonl_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            file_path = data.get("file")
            if not file_path:
                # 种子 / 注释行 — 不计为实际条目
                continue
            seed_only = False

            count += 1
            entry_type = data.get("type", "file")
            reason = data.get("reason", "-")

            if entry_type == "directory":
                print(f"  {colored(f'{count}.', Colors.GREEN)} [DIR] {file_path}")
            else:
                print(f"  {colored(f'{count}.', Colors.GREEN)} {file_path}")
            print(f"     {colored('→', Colors.YELLOW)} {reason}")

        if seed_only:
            print(f"  {colored('（尚无已管理的条目 — 仅有种子行）', Colors.YELLOW)}")

        print()

    return 0
