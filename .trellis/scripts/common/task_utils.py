#!/usr/bin/env python3
"""
任务工具函数。

提供：
    is_safe_task_path   - 验证任务路径是否可安全操作
    find_task_by_name   - 按名称查找任务目录
    resolve_task_dir    - 从名称、相对路径或绝对路径解析任务目录
    archive_task_dir    - 将任务归档到按月组织的目录
    run_task_hooks      - 运行任务事件的生命周期 hook（钩子）
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

from .paths import get_repo_root, get_tasks_dir


# =============================================================================
# 路径安全
# =============================================================================

def is_safe_task_path(task_path: str, repo_root: Path | None = None) -> bool:
    """检查相对任务路径是否可安全操作。

    Args:
        task_path: 任务路径（相对于 repo_root）。
        repo_root: 仓库根目录路径。默认自动检测。

    Returns:
        安全则返回 True，危险则返回 False。
    """
    if repo_root is None:
        repo_root = get_repo_root()

    normalized = task_path.replace("\\", "/")

    # 检查空值或 null
    if not normalized or normalized == "null":
        print("错误：任务路径为空", file=sys.stderr)
        return False

    # 拒绝绝对路径
    if Path(task_path).is_absolute():
        print(f"错误：不允许使用绝对路径：{task_path}", file=sys.stderr)
        return False

    # 拒绝 ".", "..", 以 "./" 或 "../" 开头的路径，或包含 ".." 的路径
    if normalized in (".", "..") or normalized.startswith("./") or normalized.startswith("../") or ".." in normalized:
        print(f"错误：不允许路径遍历：{task_path}", file=sys.stderr)
        return False

    # 最终检查：确保解析后的路径不是仓库根目录
    abs_path = repo_root / Path(normalized)
    if abs_path.exists():
        try:
            resolved = abs_path.resolve()
            root_resolved = repo_root.resolve()
            if resolved == root_resolved:
                print(f"错误：路径解析为仓库根目录：{task_path}", file=sys.stderr)
                return False
        except (OSError, IOError):
            pass

    return True


# =============================================================================
# 任务查找
# =============================================================================

def find_task_by_name(task_name: str, tasks_dir: Path) -> Path | None:
    """按名称查找任务目录（精确匹配或后缀匹配）。

    Args:
        task_name: 要查找的任务名称。
        tasks_dir: 任务目录路径。

    Returns:
        任务目录的绝对路径，未找到则返回 None。
    """
    if not task_name or not tasks_dir or not tasks_dir.is_dir():
        return None

    # 先尝试精确匹配
    exact_match = tasks_dir / task_name
    if exact_match.is_dir():
        return exact_match

    # 再尝试后缀匹配（例如 "my-task" 匹配 "01-21-my-task"）
    for d in tasks_dir.iterdir():
        if d.is_dir() and d.name.endswith(f"-{task_name}"):
            return d

    return None


# =============================================================================
# 归档操作
# =============================================================================

def archive_task_dir(task_dir_abs: Path, repo_root: Path | None = None) -> Path | None:
    """将任务目录归档到 archive/{YYYY-MM}/。

    Args:
        task_dir_abs: 任务目录的绝对路径。
        repo_root: 仓库根目录路径。默认自动检测。

    Returns:
        归档后的目录路径，出错则返回 None。
    """
    if not task_dir_abs.is_dir():
        print(f"错误：任务目录未找到：{task_dir_abs}", file=sys.stderr)
        return None

    # 获取任务目录的父目录
    tasks_dir = task_dir_abs.parent
    archive_dir = tasks_dir / "archive"
    year_month = datetime.now().strftime("%Y-%m")
    month_dir = archive_dir / year_month

    # 创建归档目录
    try:
        month_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, IOError) as e:
        print(f"错误：创建归档目录失败：{e}", file=sys.stderr)
        return None

    # 将任务移动到归档目录
    task_name = task_dir_abs.name
    dest = month_dir / task_name

    try:
        shutil.move(str(task_dir_abs), str(dest))
    except (OSError, IOError, shutil.Error) as e:
        print(f"错误：将任务移动到归档目录失败：{e}", file=sys.stderr)
        return None

    return dest


def archive_task_complete(
    task_dir_abs: Path,
    repo_root: Path | None = None
) -> dict[str, str]:
    """完整归档工作流（workflow）：归档目录。

    Args:
        task_dir_abs: 任务目录的绝对路径。
        repo_root: 仓库根目录路径。默认自动检测。

    Returns:
        包含归档结果信息的字典。
    """
    if not task_dir_abs.is_dir():
        print(f"错误：任务目录未找到：{task_dir_abs}", file=sys.stderr)
        return {}

    archive_dest = archive_task_dir(task_dir_abs, repo_root)
    if archive_dest:
        return {"archived_to": str(archive_dest)}

    return {}


# =============================================================================
# 任务目录解析
# =============================================================================

def resolve_task_dir(target_dir: str, repo_root: Path) -> Path:
    """将任务目录解析为绝对路径。

    支持：
    - 绝对路径：/path/to/task
    - 相对路径：.trellis/tasks/01-31-my-task
    - 任务名称：my-task（使用 find_task_by_name 查找）

    Args:
        target_dir: 任务目录的指定方式。
        repo_root: 仓库根目录路径。

    Returns:
        解析后的绝对路径。
    """
    if not target_dir:
        return Path()

    normalized = target_dir.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]

    # 绝对路径
    if Path(target_dir).is_absolute():
        return Path(target_dir)

    # 相对路径（包含路径分隔符或以 .trellis 开头）
    if "/" in normalized or normalized.startswith(".trellis"):
        return repo_root / Path(normalized)

    # 任务名称 — 尝试在任务目录中查找
    tasks_dir = get_tasks_dir(repo_root)
    found = find_task_by_name(target_dir, tasks_dir)
    if found:
        return found

    # 回退：视为相对路径处理
    return repo_root / Path(normalized)


# =============================================================================
# 生命周期 Hook
# =============================================================================

def run_task_hooks(event: str, task_json_path: Path, repo_root: Path) -> None:
    """运行任务事件的生命周期 hook。

    Args:
        event: 事件名称（例如 "after_create"）。
        task_json_path: 任务 task.json 的绝对路径。
        repo_root: 仓库根目录，用于 cwd 和配置查找。
    """
    import os
    import subprocess

    from .config import get_hooks
    from .log import Colors, colored

    commands = get_hooks(event, repo_root)
    if not commands:
        return

    env = {**os.environ, "TASK_JSON_PATH": str(task_json_path)}

    for cmd in commands:
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=repo_root,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                print(
                    colored(f"[警告] Hook 执行失败（{event}）：{cmd}", Colors.YELLOW),
                    file=sys.stderr,
                )
                if result.stderr.strip():
                    print(f"  {result.stderr.strip()}", file=sys.stderr)
        except Exception as e:
            print(
                colored(f"[警告] Hook 错误（{event}）：{cmd} — {e}", Colors.YELLOW),
                file=sys.stderr,
            )


# =============================================================================
# 主入口（用于测试）
# =============================================================================

if __name__ == "__main__":
    repo = get_repo_root()
    tasks = get_tasks_dir(repo)

    print(f"Tasks dir: {tasks}")
    print(f"is_safe_task_path('.trellis/tasks/test'): {is_safe_task_path('.trellis/tasks/test', repo)}")
    print(f"is_safe_task_path('../test'): {is_safe_task_path('../test', repo)}")
