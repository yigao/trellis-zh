"""
Trellis 自有路径的安全 git-add 辅助工具。

为什么需要此模块
----------------------
真实用户事故：某项目的 `.gitignore` 中列出了 `.trellis/`（公司范围模板 /
个人习惯）。当 `add_session.py` 和 `task.py archive` 执行自动提交（commit）
时，`git add` 因 `ignored by .gitignore` 而失败，驱动工作流的 AI
智能体通过重试 `git add -f .trellis/` 来"修复"问题 —
这导致扇出包含了所有被忽略的子目录
（`.trellis/.backup-*/`、`.trellis/worktrees/`、`.trellis/.template-hashes.json`、
`.trellis/.runtime/`），提交了 548 个文件 / 83474 行缓存和备份数据。

设计原则
------
- 脚本只暂存（stage）特定的产品路径（日志文件、index.md、
  当前任务目录、归档（archive）目录）。绝不暂存整个 `.trellis/` 树。
- 如果普通的 `git add <特定路径>` 因 "ignored by" 而失败，不要用
  ``-f`` 重试。`.trellis/` 出现在 `.gitignore` 中应视为用户意图
  （"将 .trellis/ 保留在本地"）。脚本会警告并跳过
  自动提交；希望自动暂存的用户可以修复其 `.gitignore`
  或设置 ``session_auto_commit: false`` 并自行管理 git。
- 警告信息包含反面示例：``不要使用 `git add -f .trellis/` ……``
  这样任何重新读取日志的 AI 都不会重蹈覆辙。

历史记录：0.5.10 版本在特定路径上引入了自动 ``git add -f`` 重试。
该行为在 0.5.11 版本中被回滚 — 即使用户已通过 gitignore 忽略，
自动强制添加仍违反用户意图，即使路径列表很窄也是如此。
粗粒度的禁用命令保持禁用状态，细粒度的自动 ``-f`` 也已移除。
"""

from __future__ import annotations

import sys
from pathlib import Path

from .git import run_git
from .paths import (
    DIR_ARCHIVE,
    DIR_TASKS,
    DIR_WORKFLOW,
    DIR_WORKSPACE,
    FILE_JOURNAL_PREFIX,
    get_developer,
)


# .trellis/ 下绝对不能被自动暂存的路径。在此列出以便
# 向用户发出的警告可以展示需要单独忽略的具体子路径，
# 而不是忽略整个 `.trellis/` 树。
TRELLIS_IGNORED_SUBPATHS = (
    ".trellis/.backup-*",
    ".trellis/worktrees/",
    ".trellis/.template-hashes.json",
    ".trellis/.runtime/",
    ".trellis/.cache/",
)


def safe_trellis_paths_to_add(repo_root: Path) -> list[str]:
    """返回自动提交应暂存的仓库相对路径列表。

    仅包含磁盘上实际存在的路径，以便调用方不会向 git 传递不存在的参数。
    调用方负责在之后进行 `git diff --cached` 检查。

    包含：
      - .trellis/workspace/<开发者>/journal-*.md
      - .trellis/workspace/<开发者>/index.md
      - .trellis/tasks/<任务目录>/   （每个活动任务目录）
      - .trellis/tasks/archive/      （整个归档子树，如果存在）

    排除（有意为之 — 这些路径不得被暂存）：
      - .trellis/.backup-*、.trellis/worktrees/、
        .trellis/.template-hashes.json、.trellis/.runtime/、.trellis/.cache/
    """
    paths: list[str] = []

    # 工作区日志文件 + index.md
    developer = get_developer(repo_root)
    if developer:
        ws = repo_root / DIR_WORKFLOW / DIR_WORKSPACE / developer
        if ws.is_dir():
            for f in sorted(ws.glob(f"{FILE_JOURNAL_PREFIX}*.md")):
                if f.is_file():
                    paths.append(
                        f"{DIR_WORKFLOW}/{DIR_WORKSPACE}/{developer}/{f.name}"
                    )
            index_md = ws / "index.md"
            if index_md.is_file():
                paths.append(
                    f"{DIR_WORKFLOW}/{DIR_WORKSPACE}/{developer}/index.md"
                )

    # 活动任务：tasks/ 下的每个直接子目录（目录且不是
    # 归档根目录）。归档子树作为单个路径在下方添加。
    tasks_dir = repo_root / DIR_WORKFLOW / DIR_TASKS
    if tasks_dir.is_dir():
        for child in sorted(tasks_dir.iterdir()):
            if not child.is_dir():
                continue
            if child.name == DIR_ARCHIVE:
                continue
            paths.append(f"{DIR_WORKFLOW}/{DIR_TASKS}/{child.name}")

        archive_dir = tasks_dir / DIR_ARCHIVE
        if archive_dir.is_dir():
            paths.append(f"{DIR_WORKFLOW}/{DIR_TASKS}/{DIR_ARCHIVE}")

    return paths


def safe_archive_paths_to_add(
    repo_root: Path,
    task_name: str | None = None,
    modified_children: list[str] | None = None,
) -> list[str]:
    """返回 `task.py archive` 之后应暂存的路径。

    范围仅限于归档操作实际触及的路径：

      - 归档子树（刚移动的任务所在位置）
      - 源任务目录（用于源端的删除操作；调用方将此与
        `git rm --cached` 配合使用，因为 `git add` 不会暂存
        工作树中已不存在路径的删除操作）
      - 任何子任务目录，其 `task.json` 被编辑以移除
        已归档的父任务（父子关系更新）

    这种窄范围避免了"范围蔓延" — 其他活动任务目录中的
    脏变更（并行窗口编辑）不会被捆绑到归档提交中。
    调用方在各自的提交边界内处理每种变更。

    向后兼容：无参数时，该函数以旧方式遍历整个
    `.trellis/tasks/` 子树（活动任务 + 归档）。新的
    调用方应始终传递 `task_name`。
    """
    paths: list[str] = []
    tasks_dir = repo_root / DIR_WORKFLOW / DIR_TASKS
    if not tasks_dir.is_dir():
        return paths

    archive_dir = tasks_dir / DIR_ARCHIVE

    if task_name is not None:
        # 窄范围 — 仅包含磁盘上仍存在的路径（这样
        # `git add` 不会对已移走的源路径报错）。调用方
        # 通过 `git rm --cached` 显式处理源端删除。
        if archive_dir.is_dir():
            paths.append(
                f"{DIR_WORKFLOW}/{DIR_TASKS}/{DIR_ARCHIVE}"
            )
        for child_name in modified_children or []:
            paths.append(f"{DIR_WORKFLOW}/{DIR_TASKS}/{child_name}")
        return paths

    # 旧版宽范围（无 task_name）：保留旧行为，以便尚未
    # 更新的调用方继续正常工作。
    if archive_dir.is_dir():
        paths.append(f"{DIR_WORKFLOW}/{DIR_TASKS}/{DIR_ARCHIVE}")
    for child in sorted(tasks_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name == DIR_ARCHIVE:
            continue
        paths.append(f"{DIR_WORKFLOW}/{DIR_TASKS}/{child.name}")
    return paths


def _stderr_indicates_ignored(stderr: str) -> bool:
    """git add 错误表明路径被 .gitignore 排除。"""
    if not stderr:
        return False
    lowered = stderr.lower()
    return "ignored by" in lowered


def safe_git_add(
    paths: list[str], repo_root: Path
) -> tuple[bool, bool, str]:
    """在特定路径上运行 `git add`；绝不使用 -f 重试。

    返回 ``(success, used_force, stderr)``。``used_force`` 字段保留
    是为了与 0.5.10 实现的签名兼容，但始终为
    ``False`` — 我们绝不自动强制添加。

    行为：
      - 未传入路径 → 成功，未使用强制，空 stderr。
      - 普通 ``git add -- <paths>`` 成功 → 返回成功。
      - 普通方式失败（任何原因 — 被忽略或其他）→ 返回失败并
        附带 stderr。调用方应检查 stderr（参见
        :func:`print_gitignore_warning`）并跳过自动提交。
    """
    if not paths:
        return True, False, ""

    rc, _, err = run_git(["add", "--", *paths], cwd=repo_root)
    if rc == 0:
        return True, False, ""
    return False, False, err


def print_gitignore_warning(paths: list[str]) -> None:
    """向用户（以及任何读取日志的 AI）解释如何处理。

    重要：包含反面示例
    ``不要使用 `git add -f .trellis/``` — 已知智能体会在读取
    此警告时自行发明该命令，导致扇出到被忽略的缓存/备份。
    """
    print(
        "[警告] git add 失败，因为 .trellis/ 路径被您的 .gitignore 忽略。",
        file=sys.stderr,
    )
    print(
        "[警告] 跳过自动提交。日志/任务文件仍然已写入磁盘；",
        file=sys.stderr,
    )
    print(
        "[警告] git 未被触及。",
        file=sys.stderr,
    )
    print("[警告]", file=sys.stderr)
    print(
        "[警告] Trellis 管理以下特定路径，它们应该被追踪：",
        file=sys.stderr,
    )
    if paths:
        for p in paths:
            print(f"[警告]   {p}", file=sys.stderr)
    else:
        print(
            "[警告]   .trellis/workspace/<开发者>/{journal-*.md,index.md}",
            file=sys.stderr,
        )
        print(
            "[警告]   .trellis/tasks/<任务目录>/",
            file=sys.stderr,
        )
        print(
            "[警告]   .trellis/tasks/archive/",
            file=sys.stderr,
        )
    print("[警告]", file=sys.stderr)
    print(
        "[警告] 建议：将 .gitignore 中的 `.trellis/` 改为具体的",
        file=sys.stderr,
    )
    print(
        "[警告] 应保持忽略的子路径，例如：",
        file=sys.stderr,
    )
    for sub in TRELLIS_IGNORED_SUBPATHS:
        print(f"[警告]   {sub}", file=sys.stderr)
    print("[警告]", file=sys.stderr)
    print(
        "[警告] 或者，如果您有意将 .trellis/ 保留在本地，请在",
        file=sys.stderr,
    )
    print(
        "[警告] .trellis/config.yaml 中设置：",
        file=sys.stderr,
    )
    print(
        "[警告]   session_auto_commit: false",
        file=sys.stderr,
    )
    print(
        "[警告] 这样脚本将完全跳过 git，您可以手动通过",
        file=sys.stderr,
    )
    print(
        "[警告] `git status` / `git add` / `git commit` 来审查和提交。",
        file=sys.stderr,
    )
    print("[警告]", file=sys.stderr)
    print(
        "[警告] 不要使用 `git add -f .trellis/` — 它会引入备份、worktree、",
        file=sys.stderr,
    )
    print(
        "[警告] 和运行时缓存，这些绝不应被提交。",
        file=sys.stderr,
    )
