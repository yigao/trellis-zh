#!/usr/bin/env python3
"""
任务队列工具函数。

提供：
    list_tasks_by_status   - 按状态列出任务
    list_pending_tasks     - 列出待处理的任务
    list_tasks_by_assignee - 按指派人列出任务
    list_my_tasks          - 列出当前开发者（developer）的任务
    get_task_stats         - 获取 P0/P1/P2/P3 优先级（priority）计数
"""

from __future__ import annotations

from pathlib import Path

from .paths import (
    get_repo_root,
    get_developer,
    get_tasks_dir,
)
from .tasks import iter_active_tasks


# =============================================================================
# 内部辅助函数
# =============================================================================

def _task_to_dict(t) -> dict:
    """将 TaskInfo 转换为调用方期望的字典格式。"""
    return {
        "priority": t.priority,
        "id": t.raw.get("id", ""),
        "title": t.title,
        "status": t.status,
        "assignee": t.assignee or "-",
        "dir": t.dir_name,
        "children": list(t.children),
        "parent": t.parent,
    }


# =============================================================================
# 公共函数
# =============================================================================

def list_tasks_by_status(
    filter_status: str | None = None,
    repo_root: Path | None = None
) -> list[dict]:
    """按状态（status）列出任务。

    Args:
        filter_status: 可选的状态过滤器。
        repo_root: 仓库根目录路径。默认自动检测。

    Returns:
        任务信息字典列表，键包括：priority, id, title, status, assignee。
    """
    if repo_root is None:
        repo_root = get_repo_root()

    tasks_dir = get_tasks_dir(repo_root)
    results = []

    for t in iter_active_tasks(tasks_dir):
        if filter_status and t.status != filter_status:
            continue
        results.append(_task_to_dict(t))

    return results


def list_pending_tasks(repo_root: Path | None = None) -> list[dict]:
    """列出待处理的任务。

    Args:
        repo_root: 仓库根目录路径。默认自动检测。

    Returns:
        任务信息字典列表。
    """
    return list_tasks_by_status("planning", repo_root)


def list_tasks_by_assignee(
    assignee: str,
    filter_status: str | None = None,
    repo_root: Path | None = None
) -> list[dict]:
    """列出指派给特定开发者的任务。

    Args:
        assignee: 开发者名称。
        filter_status: 可选的状态过滤器。
        repo_root: 仓库根目录路径。默认自动检测。

    Returns:
        任务信息字典列表。
    """
    if repo_root is None:
        repo_root = get_repo_root()

    tasks_dir = get_tasks_dir(repo_root)
    results = []

    for t in iter_active_tasks(tasks_dir):
        if (t.assignee or "-") != assignee:
            continue
        if filter_status and t.status != filter_status:
            continue
        results.append(_task_to_dict(t))

    return results


def list_my_tasks(
    filter_status: str | None = None,
    repo_root: Path | None = None
) -> list[dict]:
    """列出当前开发者的任务。

    Args:
        filter_status: 可选的状态过滤器。
        repo_root: 仓库根目录路径。默认自动检测。

    Returns:
        任务信息字典列表。

    Raises:
        ValueError: 如果开发者未设置。
    """
    if repo_root is None:
        repo_root = get_repo_root()

    developer = get_developer(repo_root)
    if not developer:
        raise ValueError("开发者未设置")

    return list_tasks_by_assignee(developer, filter_status, repo_root)


def get_task_stats(repo_root: Path | None = None) -> dict[str, int]:
    """获取任务统计信息。

    Args:
        repo_root: 仓库根目录路径。默认自动检测。

    Returns:
        字典，键包括：P0, P1, P2, P3, Total。
    """
    if repo_root is None:
        repo_root = get_repo_root()

    tasks_dir = get_tasks_dir(repo_root)
    stats = {"P0": 0, "P1": 0, "P2": 0, "P3": 0, "Total": 0}

    for t in iter_active_tasks(tasks_dir):
        if t.priority in stats:
            stats[t.priority] += 1
        stats["Total"] += 1

    return stats


def format_task_stats(stats: dict[str, int]) -> str:
    """将任务统计信息格式化为字符串。

    Args:
        stats: 来自 get_task_stats 的统计字典。

    Returns:
        格式化后的字符串，如 "P0:0 P1:1 P2:2 P3:0 Total:3"。
    """
    return f"P0:{stats['P0']} P1:{stats['P1']} P2:{stats['P2']} P3:{stats['P3']} Total:{stats['Total']}"


# =============================================================================
# 主入口（用于测试）
# =============================================================================

if __name__ == "__main__":
    stats = get_task_stats()
    print(format_task_stats(stats))
    print()
    print("待处理的任务：")
    for task in list_pending_tasks():
        print(f"  {task['priority']}|{task['id']}|{task['title']}|{task['status']}|{task['assignee']}")
