"""
Trellis 工作流（workflow）脚本的公共工具。

此模块提供其他 Trellis 脚本使用的共享功能。
"""

import io
import sys

# =============================================================================
# Windows 编码修复（必须放在最前面，在任何其他输出之前）
# =============================================================================
# 在 Windows 上，stdout 默认使用系统代码页（通常为 GBK/CP936）。
# 这会导致打印非 ASCII 字符时出现 UnicodeEncodeError。
#
# 任何从 common 导入的脚本都会自动获得此修复。
# =============================================================================


def _configure_stream(stream: object) -> object:
    """在 Windows 上配置流使用 UTF-8 编码。"""
    # 首先尝试 reconfigure()（Python 3.7+，更可靠）
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        return stream
    # 回退方案：detach 后用 TextIOWrapper 重新包装
    elif hasattr(stream, "detach"):
        return io.TextIOWrapper(
            stream.detach(),  # type: ignore[union-attr]
            encoding="utf-8",
            errors="replace",
        )
    return stream


if sys.platform == "win32":
    sys.stdout = _configure_stream(sys.stdout)  # type: ignore[assignment]
    sys.stderr = _configure_stream(sys.stderr)  # type: ignore[assignment]
    sys.stdin = _configure_stream(sys.stdin)  # type: ignore[assignment]


def configure_encoding() -> None:
    """
    在 Windows 上配置 stdout/stderr/stdin 使用 UTF-8 编码。

    当从 common 导入时会自动调用此函数，
    但对于不导入 common 的脚本也可以手动调用。

    多次调用是安全的。
    """
    global sys
    if sys.platform == "win32":
        sys.stdout = _configure_stream(sys.stdout)  # type: ignore[assignment]
        sys.stderr = _configure_stream(sys.stderr)  # type: ignore[assignment]
        sys.stdin = _configure_stream(sys.stdin)  # type: ignore[assignment]


from .paths import (
    DIR_WORKFLOW,
    DIR_WORKSPACE,
    DIR_TASKS,
    DIR_ARCHIVE,
    DIR_SPEC,
    DIR_SCRIPTS,
    FILE_DEVELOPER,
    FILE_CURRENT_TASK,
    FILE_TASK_JSON,
    FILE_JOURNAL_PREFIX,
    get_repo_root,
    get_developer,
    check_developer,
    get_tasks_dir,
    get_workspace_dir,
    get_active_journal_file,
    count_lines,
    get_current_task,
    get_current_task_abs,
    normalize_task_ref,
    resolve_task_ref,
    set_current_task,
    clear_current_task,
    has_current_task,
    generate_task_date_prefix,
)

from .active_task import (
    ActiveTask,
    clear_active_task,
    resolve_active_task,
    resolve_context_key,
    set_active_task,
)
