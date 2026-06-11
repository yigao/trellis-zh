#!/usr/bin/env python3
"""
开发者管理工具。

提供：
    init_developer     - 初始化开发者
    ensure_developer   - 确保开发者已初始化（如果未初始化则退出）
    show_developer_info - 显示开发者信息
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from .paths import (
    DIR_WORKFLOW,
    DIR_WORKSPACE,
    DIR_TASKS,
    FILE_DEVELOPER,
    FILE_JOURNAL_PREFIX,
    get_repo_root,
    get_developer,
    check_developer,
)


# =============================================================================
# 开发者初始化
# =============================================================================

def init_developer(name: str, repo_root: Path | None = None) -> bool:
    """初始化开发者。

    创建：
        - .trellis/.developer 文件（含开发者信息）
        - .trellis/workspace/<name>/ 目录结构
        - 初始日志文件和 index.md

    Args:
        name: 开发者名称。
        repo_root: 仓库根目录路径。默认为自动检测。

    Returns:
        成功返回 True，出错返回 False。
    """
    if not name:
        print("错误：开发者名称为必填项", file=sys.stderr)
        return False

    if repo_root is None:
        repo_root = get_repo_root()

    dev_file = repo_root / DIR_WORKFLOW / FILE_DEVELOPER
    workspace_dir = repo_root / DIR_WORKFLOW / DIR_WORKSPACE / name

    # 创建 .developer 文件
    initialized_at = datetime.now().isoformat()
    try:
        dev_file.write_text(
            f"name={name}\ninitialized_at={initialized_at}\n",
            encoding="utf-8"
        )
    except (OSError, IOError) as e:
        print(f"错误：创建 .developer 文件失败：{e}", file=sys.stderr)
        return False

    # 创建工作区目录结构
    try:
        workspace_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, IOError) as e:
        print(f"错误：创建工作区目录失败：{e}", file=sys.stderr)
        return False

    # 创建初始日志文件
    journal_file = workspace_dir / f"{FILE_JOURNAL_PREFIX}1.md"
    if not journal_file.exists():
        today = datetime.now().strftime("%Y-%m-%d")
        journal_content = f"""# 日志 - {name}（第 1 部分）

> AI 开发会话日志
> 开始日期：{today}

---

"""
        try:
            journal_file.write_text(journal_content, encoding="utf-8")
        except (OSError, IOError) as e:
            print(f"错误：创建日志文件失败：{e}", file=sys.stderr)
            return False

    # 创建 index.md（含自动更新标记）
    index_file = workspace_dir / "index.md"
    if not index_file.exists():
        index_content = f"""# 工作区索引 - {name}

> AI 开发会话的日志追踪。

---

## 当前状态

<!-- @@@auto:current-status -->
- **活动文件**：`journal-1.md`
- **会话总数**：0
- **最近活动**：-
<!-- @@@/auto:current-status -->

---

## 活动文档

<!-- @@@auto:active-documents -->
| 文件 | 行数 | 状态 |
|------|-------|--------|
| `journal-1.md` | ~0 | 活动 |
<!-- @@@/auto:active-documents -->

---

## 会话历史

<!-- @@@auto:session-history -->
| # | 日期 | 标题 | 提交 | 分支 |
|---|------|-------|---------|--------|
<!-- @@@/auto:session-history -->

---

## 备注

- 会话会追加到日志文件中
- 当日志文件超过 2000 行时，会创建新的日志文件
- 使用 `add_session.py` 记录会话
"""
        try:
            index_file.write_text(index_content, encoding="utf-8")
        except (OSError, IOError) as e:
            print(f"错误：创建 index.md 失败：{e}", file=sys.stderr)
            return False

    print(f"开发者已初始化：{name}")
    print(f"  .developer 文件：{dev_file}")
    print(f"  工作区目录：{workspace_dir}")

    return True


def ensure_developer(repo_root: Path | None = None) -> None:
    """确保开发者已初始化，如果未初始化则退出。

    Args:
        repo_root: 仓库根目录路径。默认为自动检测。
    """
    if repo_root is None:
        repo_root = get_repo_root()

    if not check_developer(repo_root):
        print("错误：开发者未初始化。", file=sys.stderr)
        print(f"运行：py -3 ./{DIR_WORKFLOW}/scripts/init_developer.py <你的名称>", file=sys.stderr)
        sys.exit(1)


def show_developer_info(repo_root: Path | None = None) -> None:
    """显示开发者信息。

    Args:
        repo_root: 仓库根目录路径。默认为自动检测。
    """
    if repo_root is None:
        repo_root = get_repo_root()

    developer = get_developer(repo_root)

    if not developer:
        print("开发者：（未初始化）")
    else:
        print(f"开发者：{developer}")
        print(f"工作区：{DIR_WORKFLOW}/{DIR_WORKSPACE}/{developer}/")
        print(f"任务：{DIR_WORKFLOW}/{DIR_TASKS}/")


# =============================================================================
# 主入口（用于测试）
# =============================================================================

if __name__ == "__main__":
    show_developer_info()
