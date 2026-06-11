"""
任务数据访问层。

加载和遍历任务目录的唯一数据源。
替代了散落在 9+ 个文件中的 task.json 解析逻辑。

提供：
    load_task          — 按目录路径加载单个任务
    iter_active_tasks  — 遍历所有活动（非归档）任务（已排序）
    get_all_statuses   — 获取 {dir_name: status} 映射以计算子任务进度
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from .io import read_json
from .paths import FILE_TASK_JSON
from .types import TaskInfo


def load_task(task_dir: Path) -> TaskInfo | None:
    """从包含 task.json 的目录加载任务。

    Args:
        task_dir: 任务目录的绝对路径。

    Returns:
        如果 task.json 存在且有效则返回 TaskInfo，否则返回 None。
    """
    task_json = task_dir / FILE_TASK_JSON
    if not task_json.is_file():
        return None

    data = read_json(task_json)
    if not data:
        return None

    return TaskInfo(
        dir_name=task_dir.name,
        directory=task_dir,
        title=data.get("title") or data.get("name") or "unknown",
        status=data.get("status", "unknown"),
        assignee=data.get("assignee", ""),
        priority=data.get("priority", "P2"),
        children=tuple(data.get("children", [])),
        parent=data.get("parent"),
        package=data.get("package"),
        raw=data,
    )


def iter_active_tasks(tasks_dir: Path) -> Iterator[TaskInfo]:
    """遍历所有活动（非归档）任务，按目录名排序。

    跳过 "archive" 目录以及没有有效 task.json 的目录。

    Args:
        tasks_dir: 任务目录的路径。

    Yields:
        每个有效任务的 TaskInfo。
    """
    if not tasks_dir.is_dir():
        return

    for d in sorted(tasks_dir.iterdir()):
        if not d.is_dir() or d.name == "archive":
            continue
        info = load_task(d)
        if info is not None:
            yield info


def get_all_statuses(tasks_dir: Path) -> dict[str, str]:
    """获取所有活动任务的 {dir_name: status} 映射。

    用于在无需加载完整 TaskInfo 的情况下计算子任务进度。

    Args:
        tasks_dir: 任务目录的路径。

    Returns:
        将目录名映射到状态字符串的字典。
    """
    return {t.dir_name: t.status for t in iter_active_tasks(tasks_dir)}


def children_progress(
    children: tuple[str, ...] | list[str],
    all_statuses: dict[str, str],
) -> str:
    """格式化子任务进度字符串，如 " [2/3 done]"。

    Args:
        children: 子任务目录名列表。
        all_statuses: 来自 get_all_statuses() 的状态映射。

    Returns:
        格式化后的字符串；如果没有子任务则返回 ""。
    """
    if not children:
        return ""
    # 不在活动状态列表中的子任务表示已被归档（cmd_archive 在移动目录前
    # 会将 status 设为 completed）。将其计入已完成，以免父任务进度
    # 在子任务归档后出现倒退。
    done = sum(
        1 for c in children
        if c not in all_statuses or all_statuses.get(c) in ("completed", "done")
    )
    return f" [{done}/{len(children)} done]"
