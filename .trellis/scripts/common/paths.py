#!/usr/bin/env python3
"""
Trellis 工作流（workflow）的通用路径工具。

提供：
    get_repo_root          - 获取仓库（repository）根目录
    get_developer          - 获取开发者（developer）名称
    get_workspace_dir      - 获取开发者工作区（workspace）目录
    get_tasks_dir          - 获取任务（task）目录
    get_active_journal_file - 获取当前日志（journal）文件
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


# =============================================================================
# 路径常量（在此处修改以重命名目录）
# =============================================================================

# 目录名称
DIR_WORKFLOW = ".trellis"
DIR_WORKSPACE = "workspace"
DIR_TASKS = "tasks"
DIR_ARCHIVE = "archive"
DIR_SPEC = "spec"
DIR_SCRIPTS = "scripts"

# 文件名
FILE_DEVELOPER = ".developer"
FILE_CURRENT_TASK = ".current-task"
FILE_TASK_JSON = "task.json"
FILE_JOURNAL_PREFIX = "journal-"


# =============================================================================
# 仓库根目录
# =============================================================================

def get_repo_root(start_path: Path | None = None) -> Path:
    """查找包含 .trellis/ 文件夹的最近目录。

    此函数正确处理嵌套 git 仓库的情况（例如，位于另一个仓库中的测试项目）。

    Args:
        start_path: 搜索的起始目录。默认为当前目录。

    Returns:
        仓库根目录的路径，如果找不到 .trellis/ 则返回当前目录。
    """
    current = (start_path or Path.cwd()).resolve()

    while current != current.parent:
        if (current / DIR_WORKFLOW).is_dir():
            return current
        current = current.parent

    # 如果找不到 .trellis/，回退到当前目录
    return Path.cwd().resolve()


# =============================================================================
# 开发者
# =============================================================================

def get_developer(repo_root: Path | None = None) -> str | None:
    """从 .developer 文件获取开发者名称。

    Args:
        repo_root: 仓库根目录路径。默认为自动检测。

    Returns:
        开发者名称，如果未初始化则返回 None。
    """
    if repo_root is None:
        repo_root = get_repo_root()

    dev_file = repo_root / DIR_WORKFLOW / FILE_DEVELOPER

    if not dev_file.is_file():
        return None

    try:
        content = dev_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith("name="):
                return line.split("=", 1)[1].strip()
    except (OSError, IOError):
        pass

    return None


def check_developer(repo_root: Path | None = None) -> bool:
    """检查开发者是否已初始化。

    Args:
        repo_root: 仓库根目录路径。默认为自动检测。

    Returns:
        如果开发者已初始化则返回 True。
    """
    return get_developer(repo_root) is not None


# =============================================================================
# 任务目录
# =============================================================================

def get_tasks_dir(repo_root: Path | None = None) -> Path:
    """获取任务目录路径。

    Args:
        repo_root: 仓库根目录路径。默认为自动检测。

    Returns:
        任务目录的路径。
    """
    if repo_root is None:
        repo_root = get_repo_root()
    return repo_root / DIR_WORKFLOW / DIR_TASKS


# =============================================================================
# 工作区目录
# =============================================================================

def get_workspace_dir(repo_root: Path | None = None) -> Path | None:
    """获取开发者工作区目录。

    Args:
        repo_root: 仓库根目录路径。默认为自动检测。

    Returns:
        工作区目录的路径，如果开发者未设置则返回 None。
    """
    if repo_root is None:
        repo_root = get_repo_root()

    developer = get_developer(repo_root)
    if developer:
        return repo_root / DIR_WORKFLOW / DIR_WORKSPACE / developer
    return None


# =============================================================================
# 日志文件
# =============================================================================

def get_active_journal_file(repo_root: Path | None = None) -> Path | None:
    """获取当前活动日志文件。

    Args:
        repo_root: 仓库根目录路径。默认为自动检测。

    Returns:
        活动日志文件的路径，如果未找到则返回 None。
    """
    if repo_root is None:
        repo_root = get_repo_root()

    workspace_dir = get_workspace_dir(repo_root)
    if workspace_dir is None or not workspace_dir.is_dir():
        return None

    latest: Path | None = None
    highest = 0

    for f in workspace_dir.glob(f"{FILE_JOURNAL_PREFIX}*.md"):
        if not f.is_file():
            continue

        # 从文件名中提取编号
        name = f.stem  # 例如 "journal-1"
        match = re.search(r"(\d+)$", name)
        if match:
            num = int(match.group(1))
            if num > highest:
                highest = num
                latest = f

    return latest


def count_lines(file_path: Path) -> int:
    """统计文件中的行数。

    Args:
        file_path: 文件路径。

    Returns:
        行数，如果文件不存在则返回 0。
    """
    if not file_path.is_file():
        return 0

    try:
        return len(file_path.read_text(encoding="utf-8").splitlines())
    except (OSError, IOError):
        return 0


# =============================================================================
# 当前任务管理
# =============================================================================

def normalize_task_ref(task_ref: str) -> str:
    """规范化任务引用以便稳定地运行时存储。

    存储的引用应优先使用仓库相对路径的 POSIX 格式，例如
    `.trellis/tasks/03-27-my-task`，即使在 Windows 上也是如此。绝对路径会被保留，
    除非调用方稍后可以将其转换回仓库相对路径的形式。
    """
    normalized = task_ref.strip()
    if not normalized:
        return ""

    path_obj = Path(normalized)
    if path_obj.is_absolute():
        return str(path_obj)

    normalized = normalized.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]

    if normalized.startswith(f"{DIR_TASKS}/"):
        return f"{DIR_WORKFLOW}/{normalized}"

    return normalized


def resolve_task_ref(task_ref: str, repo_root: Path | None = None) -> Path | None:
    """将任务引用解析为绝对任务目录路径。"""
    if repo_root is None:
        repo_root = get_repo_root()

    normalized = normalize_task_ref(task_ref)
    if not normalized:
        return None

    path_obj = Path(normalized)
    if path_obj.is_absolute():
        return path_obj

    if normalized.startswith(f"{DIR_WORKFLOW}/"):
        return repo_root / path_obj

    return repo_root / DIR_WORKFLOW / DIR_TASKS / path_obj


def get_current_task(
    repo_root: Path | None = None,
    platform_input: dict | None = None,
    platform: str | None = None,
) -> str | None:
    """获取当前任务目录路径（相对于 repo_root）。

    Args:
        repo_root: 仓库根目录路径。默认为自动检测。

    Returns:
        当前任务目录的相对路径，如果没有则返回 None。
    """
    if repo_root is None:
        repo_root = get_repo_root()

    from .active_task import resolve_active_task

    return resolve_active_task(repo_root, platform_input, platform).task_path


def get_current_task_abs(
    repo_root: Path | None = None,
    platform_input: dict | None = None,
    platform: str | None = None,
) -> Path | None:
    """获取当前任务目录的绝对路径。

    Args:
        repo_root: 仓库根目录路径。默认为自动检测。

    Returns:
        当前任务目录的绝对路径，如果没有则返回 None。
    """
    if repo_root is None:
        repo_root = get_repo_root()

    relative = get_current_task(repo_root, platform_input, platform)
    if relative:
        return resolve_task_ref(relative, repo_root)
    return None


def get_current_task_source(
    repo_root: Path | None = None,
    platform_input: dict | None = None,
    platform: str | None = None,
) -> tuple[str, str | None, str | None]:
    """获取活动任务来源，格式为 (`source`, `context_key`, `task_path`)。"""
    if repo_root is None:
        repo_root = get_repo_root()

    from .active_task import get_current_task_source as _get_source

    return _get_source(repo_root, platform_input, platform)


def set_current_task(
    task_path: str,
    repo_root: Path | None = None,
    platform_input: dict | None = None,
    platform: str | None = None,
) -> bool:
    """在会话（session）范围内设置当前任务。

    Args:
        task_path: 任务目录路径（相对于 repo_root）。
        repo_root: 仓库根目录路径。默认为自动检测。

    Returns:
        成功返回 True，出错返回 False。
    """
    if repo_root is None:
        repo_root = get_repo_root()

    from .active_task import set_active_task

    return set_active_task(
        task_path,
        repo_root,
        platform_input=platform_input,
        platform=platform,
    ) is not None


def clear_current_task(
    repo_root: Path | None = None,
    platform_input: dict | None = None,
    platform: str | None = None,
) -> bool:
    """在会话范围内清除当前任务。

    Args:
        repo_root: 仓库根目录路径。默认为自动检测。

    Returns:
        成功返回 True。
    """
    if repo_root is None:
        repo_root = get_repo_root()

    from .active_task import clear_active_task

    clear_active_task(
        repo_root,
        platform_input=platform_input,
        platform=platform,
    )
    return True


def has_current_task(repo_root: Path | None = None) -> bool:
    """检查是否有当前任务。

    Args:
        repo_root: 仓库根目录路径。默认为自动检测。

    Returns:
        如果已设置当前任务则返回 True。
    """
    return get_current_task(repo_root) is not None


# =============================================================================
# 任务 ID 生成
# =============================================================================

def generate_task_date_prefix() -> str:
    """基于日期生成任务 ID（MM-DD 格式）。

    Returns:
        日期前缀字符串（例如 "01-21"）。
    """
    return datetime.now().strftime("%m-%d")


# =============================================================================
# 单仓库（monorepo）/ 软件包（package）路径
# =============================================================================


def get_spec_dir(package: str | None = None, repo_root: Path | None = None) -> Path:
    """获取规范（spec）目录路径。

    单仓库：.trellis/spec
    带软件包的单仓库：.trellis/spec/<package>

    使用惰性导入以避免与 config.py 的循环依赖。
    """
    if repo_root is None:
        repo_root = get_repo_root()

    from .config import get_spec_base

    base = get_spec_base(package, repo_root)
    return repo_root / DIR_WORKFLOW / base


def get_package_path(package: str, repo_root: Path | None = None) -> Path | None:
    """从配置中获取软件包的源代码目录绝对路径。

    Returns:
        软件包目录的绝对路径，如果未找到则返回 None。
    """
    if repo_root is None:
        repo_root = get_repo_root()

    from .config import get_packages

    packages = get_packages(repo_root)
    if not packages or package not in packages:
        return None

    info = packages[package]
    if isinstance(info, dict):
        rel_path = info.get("path", package)
    else:
        rel_path = str(info)

    return repo_root / rel_path


# =============================================================================
# 主入口（用于测试）
# =============================================================================

if __name__ == "__main__":
    repo = get_repo_root()
    print(f"仓库根目录：{repo}")
    print(f"开发者：{get_developer(repo)}")
    print(f"任务目录：{get_tasks_dir(repo)}")
    print(f"工作区目录：{get_workspace_dir(repo)}")
    print(f"日志文件：{get_active_journal_file(repo)}")
    print(f"当前任务：{get_current_task(repo)}")
