#!/usr/bin/env python3
"""
任务 CRUD 操作。

提供：
    ensure_tasks_dir   - 确保任务目录存在
    cmd_create         - 创建新任务
    cmd_archive        - 归档已完成任务
    cmd_set_branch     - 设置任务的 git 分支
    cmd_set_base_branch - 设置 PR（拉取请求）目标分支
    cmd_set_scope      - 设置 PR 标题的范围（scope）
    cmd_add_subtask    - 将子（child）任务链接到父（parent）任务
    cmd_remove_subtask - 取消子任务与父任务的链接
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from .config import (
    get_packages,
    get_session_auto_commit,
    is_monorepo,
    resolve_package,
    validate_package,
)
from .git import run_git
from .io import read_json, write_json
from .log import Colors, colored
from .paths import (
    DIR_ARCHIVE,
    DIR_TASKS,
    DIR_WORKFLOW,
    FILE_TASK_JSON,
    generate_task_date_prefix,
    get_developer,
    get_repo_root,
    get_tasks_dir,
)
from .safe_commit import (
    print_gitignore_warning,
    safe_archive_paths_to_add,
    safe_git_add,
)
from .task_utils import (
    archive_task_complete,
    find_task_by_name,
    resolve_task_dir,
    run_task_hooks,
)


# =============================================================================
# 辅助函数
# =============================================================================

def _slugify(title: str) -> str:
    """将标题转换为 slug（仅适用于 ASCII）。"""
    result = title.lower()
    result = re.sub(r"[^a-z0-9]", "-", result)
    result = re.sub(r"-+", "-", result)
    result = result.strip("-")
    return result


def ensure_tasks_dir(repo_root: Path) -> Path:
    """确保任务目录存在。"""
    tasks_dir = get_tasks_dir(repo_root)
    archive_dir = tasks_dir / "archive"

    if not tasks_dir.exists():
        tasks_dir.mkdir(parents=True)
        print(colored(f"已创建任务目录：{tasks_dir}", Colors.GREEN), file=sys.stderr)

    if not archive_dir.exists():
        archive_dir.mkdir(parents=True)

    return tasks_dir


# =============================================================================
# 子代理平台检测 + JSONL 播种
# =============================================================================

# 消费 implement.jsonl / check.jsonl 的平台的配置目录。
# 与 src/types/ai-tools.ts 中的 AI_TOOLS 条目保持同步 — 这些是
# workflow.md 的 "agent-capable" Skill Routing 块中列出的平台
#（Class-1 hook-inject + Class-2 pull-based preludes）。Kilo / Antigravity /
# Windsurf 不在该列表中：它们不消费 JSONL。
_SUBAGENT_CONFIG_DIRS: tuple[str, ...] = (
    ".claude",
    ".cursor",
    ".codex",
    ".kiro",
    ".gemini",
    ".opencode",
    ".qoder",
    ".codebuddy",
    ".factory",   # Factory Droid
    ".github/copilot",
    ".pi",        # Pi Agent
)

_SEED_EXAMPLE = (
    "Fill with {\"file\": \"<path>\", \"reason\": \"<why>\"}. "
    "Put spec/research files only — no code paths. "
    "Run `py -3 .trellis/scripts/get_context.py --mode packages` to list available specs. "
    "Delete this line once real entries are added."
)


def _has_subagent_platform(repo_root: Path) -> bool:
    """如果配置了任何支持子代理的平台则返回 True。

    通过探测仓库根目录下的已知配置目录来检测。仅用于决定
    ``task.py create`` 是否应该播种空的 ``implement.jsonl`` /
    ``check.jsonl`` 文件。
    """
    for config_dir in _SUBAGENT_CONFIG_DIRS:
        if (repo_root / config_dir).is_dir():
            return True
    return False


def _write_seed_jsonl(path: Path) -> None:
    """写入一行带有自描述 ``_example`` 的种子 JSONL 文件。

    种子行没有 ``file`` 字段，因此下游消费者（hook + prelude）
    在遍历条目时通过 ``item.get("file")`` 自然会跳过它。
    该行纯粹作为 AI 管理者的文件内提示存在。
    """
    seed = {"_example": _SEED_EXAMPLE}
    path.write_text(json.dumps(seed, ensure_ascii=False) + "\n", encoding="utf-8")


# =============================================================================
# 命令：create
# =============================================================================

def cmd_create(args: argparse.Namespace) -> int:
    """创建新任务。"""
    repo_root = get_repo_root()

    if not args.title:
        print(colored("错误：标题为必填项", Colors.RED), file=sys.stderr)
        return 1

    # 验证 --package（CLI 来源：快速失败）
    package: str | None = getattr(args, "package", None)
    if not is_monorepo(repo_root):
        # 单仓库：忽略 --package，不带 package 前缀
        if package:
            print(colored(f"警告：在单仓库项目中 --package 被忽略", Colors.YELLOW), file=sys.stderr)
        package = None
    elif package:
        if not validate_package(package, repo_root):
            packages = get_packages(repo_root)
            available = ", ".join(sorted(packages.keys())) if packages else "(none)"
            print(colored(f"错误：未知软件包 '{package}'。可用：{available}", Colors.RED), file=sys.stderr)
            return 1
    else:
        # 自动推断：default_package → None（创建时还没有 task.json）
        package = resolve_package(repo_root=repo_root)

    # 默认指派人为当前开发者（developer）
    assignee = args.assignee
    if not assignee:
        assignee = get_developer(repo_root)
        if not assignee:
            print(colored("错误：未设置开发者。请先运行 init_developer.py 或使用 --assignee", Colors.RED), file=sys.stderr)
            return 1

    ensure_tasks_dir(repo_root)

    # 获取当前开发者作为创建者
    creator = get_developer(repo_root) or assignee

    # 若未提供则生成 slug
    slug = args.slug or _slugify(args.title)
    if not slug:
        print(colored("错误：无法从标题生成 slug", Colors.RED), file=sys.stderr)
        return 1

    # 以 MM-DD-slug 格式创建任务目录
    tasks_dir = get_tasks_dir(repo_root)
    date_prefix = generate_task_date_prefix()
    dir_name = f"{date_prefix}-{slug}"
    task_dir = tasks_dir / dir_name
    task_json_path = task_dir / FILE_TASK_JSON

    if task_dir.exists():
        print(colored(f"警告：任务目录已存在：{dir_name}", Colors.YELLOW), file=sys.stderr)
    else:
        task_dir.mkdir(parents=True)

    today = datetime.now().strftime("%Y-%m-%d")

    # 记录当前分支作为 base_branch（PR 目标）
    _, branch_out, _ = run_git(["branch", "--show-current"], cwd=repo_root)
    current_branch = branch_out.strip() or "main"

    task_data = {
        "id": slug,
        "name": slug,
        "title": args.title,
        "description": args.description or "",
        "status": "planning",
        "dev_type": None,
        "scope": None,
        "package": package,
        "priority": args.priority,
        "creator": creator,
        "assignee": assignee,
        "createdAt": today,
        "completedAt": None,
        "branch": None,
        "base_branch": current_branch,
        "worktree_path": None,
        "commit": None,
        "pr_url": None,
        "subtasks": [],
        "children": [],
        "parent": None,
        "relatedFiles": [],
        "notes": "",
        "meta": {},
    }

    write_json(task_json_path, task_data)

    # 为支持子代理的平台播种 implement.jsonl / check.jsonl。
    # 代理在 Phase 1.3 中管理实际条目（参见 .trellis/workflow.md）。
    # 无代理平台（Kilo / Antigravity / Windsurf）跳过此步骤 — 它们
    # 通过 trellis-before-dev skill 加载规范（spec），而非 JSONL。
    seeded_jsonl = False
    if _has_subagent_platform(repo_root):
        for jsonl_name in ("implement.jsonl", "check.jsonl"):
            jsonl_path = task_dir / jsonl_name
            if not jsonl_path.exists():
                _write_seed_jsonl(jsonl_path)
        seeded_jsonl = True

    # 处理 --parent：建立双向链接
    if args.parent:
        parent_dir = resolve_task_dir(args.parent, repo_root)
        parent_json_path = parent_dir / FILE_TASK_JSON
        if not parent_json_path.is_file():
            print(colored(f"警告：父任务 task.json 未找到：{args.parent}", Colors.YELLOW), file=sys.stderr)
        else:
            parent_data = read_json(parent_json_path)
            if parent_data:
                # 将子任务添加到父任务的 children 列表
                parent_children = parent_data.get("children", [])
                if dir_name not in parent_children:
                    parent_children.append(dir_name)
                    parent_data["children"] = parent_children
                    write_json(parent_json_path, parent_data)

                # 在子任务的 task.json 中设置 parent
                task_data["parent"] = parent_dir.name
                write_json(task_json_path, task_data)

                print(colored(f"已链接为子任务，父任务：{parent_dir.name}", Colors.GREEN), file=sys.stderr)

    # 自动激活新任务，以便每轮面包屑触发 planning 状态。
    # 尽力而为：若无会话（session）身份则优雅降级（在 AI 会话之外
    # 运行 CLI）— 任务仍然创建，用户可以稍后运行 task.py start。
    # 指针是 session 作用域的，因此绝不会影响其他 AI 会话。
    try:
        from .active_task import resolve_context_key, set_active_task
        if resolve_context_key():
            try:
                rel_dir = task_dir.relative_to(repo_root).as_posix()
            except ValueError:
                rel_dir = str(task_dir)
            set_active_task(rel_dir, repo_root)
    except Exception:
        pass

    print(colored(f"已创建任务：{dir_name}", Colors.GREEN), file=sys.stderr)
    print("", file=sys.stderr)
    print(colored("后续步骤：", Colors.BLUE), file=sys.stderr)
    print("  1. 创建包含需求的 prd.md", file=sys.stderr)
    if seeded_jsonl:
        print(
            "  2. 管理 implement.jsonl / check.jsonl（仅规范和研究文件 — "
            "参见 .trellis/workflow.md Phase 1.3）",
            file=sys.stderr,
        )
        print("  3. 运行：py -3 task.py start <dir>", file=sys.stderr)
    else:
        print("  2. 运行：py -3 task.py start <dir>", file=sys.stderr)
    print("", file=sys.stderr)

    # 输出相对路径以供脚本链式调用
    print(f"{DIR_WORKFLOW}/{DIR_TASKS}/{dir_name}")

    run_task_hooks("after_create", task_json_path, repo_root)
    return 0


# =============================================================================
# 命令：archive
# =============================================================================

def cmd_archive(args: argparse.Namespace) -> int:
    """归档已完成任务。"""
    repo_root = get_repo_root()
    task_name = args.name

    if not task_name:
        print(colored("错误：任务名称为必填项", Colors.RED), file=sys.stderr)
        return 1

    tasks_dir = get_tasks_dir(repo_root)

    # 解析任务目录（支持任务名称、相对路径或绝对路径）
    task_dir = resolve_task_dir(task_name, repo_root)

    if not task_dir or not task_dir.is_dir():
        print(colored(f"错误：任务未找到：{task_name}", Colors.RED), file=sys.stderr)
        print("活动任务：", file=sys.stderr)
        # 延迟导入以避免循环依赖
        from .tasks import iter_active_tasks
        for t in iter_active_tasks(tasks_dir):
            print(f"  - {t.dir_name}/", file=sys.stderr)
        return 1

    dir_name = task_dir.name
    task_json_path = task_dir / FILE_TASK_JSON

    # 归档前更新状态
    today = datetime.now().strftime("%Y-%m-%d")
    # 子任务目录名称列表，其 task.json 将被修改；传入
    # safe_archive_paths_to_add 以便在本次提交中暂存。
    modified_children: list[str] = []
    if task_json_path.is_file():
        data = read_json(task_json_path)
        if data:
            data["status"] = "completed"
            data["completedAt"] = today
            write_json(task_json_path, data)

            # 归档时处理子任务关系。
            # 将此任务保留在父任务的 children 列表中，以便进度
            # 计数器（children_progress）保持一致 — 不在活动
            # 集合中的子任务被视为已完成。
            task_children = data.get("children", [])

            # 如果这是父任务，清除所有子任务的 parent 字段
            if task_children:
                for child_name in task_children:
                    child_dir_path = find_task_by_name(child_name, tasks_dir)
                    if child_dir_path:
                        child_json = child_dir_path / FILE_TASK_JSON
                        if child_json.is_file():
                            child_data = read_json(child_json)
                            if child_data:
                                child_data["parent"] = None
                                write_json(child_json, child_data)
                                modified_children.append(child_dir_path.name)

    # 在路径移动之前，清除仍指向此任务的所有会话指针。
    from .active_task import clear_task_from_sessions
    clear_task_from_sessions(str(task_dir), repo_root)

    # 归档
    result = archive_task_complete(task_dir, repo_root)
    if "archived_to" in result:
        archive_dest = Path(result["archived_to"])
        year_month = archive_dest.parent.name
        print(colored(f"已归档：{dir_name} -> archive/{year_month}/", Colors.GREEN), file=sys.stderr)

        # 自动提交，除非指定了 --no-commit
        if not getattr(args, "no_commit", False):
            _auto_commit_archive(dir_name, repo_root, modified_children)

        # 返回归档路径
        print(f"{DIR_WORKFLOW}/{DIR_TASKS}/{DIR_ARCHIVE}/{year_month}/{dir_name}")

        # 使用归档后的路径运行 hook
        archived_json = archive_dest / FILE_TASK_JSON
        run_task_hooks("after_archive", archived_json, repo_root)
        return 0

    return 1


def _auto_commit_archive(
    task_name: str,
    repo_root: Path,
    modified_children: list[str] | None = None,
) -> None:
    """归档后暂存 Trellis 拥有的任务路径并提交。

    范围严格限定为已归档任务的源路径 + 目标路径，加上
    ``task.json`` 被编辑过的子任务目录（父→子关系更新）。
    其他活动任务目录中的脏变更不会被捆绑到归档提交中。

    如果 ``.gitignore`` 阻止了这些路径，我们会警告并跳过 — 我们
    不会使用 ``git add -f`` 重试。该警告明确禁止使用
    ``git add -f .trellis/``（这会导致缓存/备份被纳入），
    并引导用户使用 ``session_auto_commit: false``。

    尊重 ``.trellis/config.yaml`` 中的 ``session_auto_commit`` 设置：
    当设为 ``false`` 时，此函数立即返回而不触 git
    （磁盘上的归档目录移动不受影响）。
    """
    if not get_session_auto_commit(repo_root):
        print(
            "[OK] session_auto_commit: false — 跳过 git stage/commit。",
            file=sys.stderr,
        )
        return

    paths = safe_archive_paths_to_add(
        repo_root, task_name=task_name, modified_children=modified_children
    )
    if not paths:
        print("[OK] 没有任务变更需要提交。", file=sys.stderr)
        return

    success, _, err = safe_git_add(paths, repo_root)
    if not success:
        if err and "ignored by" in err.lower():
            print_gitignore_warning(paths)
        else:
            print(
                f"[警告] git add 失败：{err.strip() if err else '未知错误'}",
                file=sys.stderr,
            )
        return

    # 双重保障防止幽灵删除 bug：``safe_git_add`` 使用 ``git add``
    #（不带 -A）只暂存新增/修改。源任务目录已被 ``shutil.move``
    # 移走，因此其文件需要显式的 ``git rm --cached`` 才能在本次
    # 提交中暂存删除 — 否则它们会作为未提交的"幽灵删除"一直存在，
    # 直到后续某个操作将它们捡起。
    #
    # ``--ignore-unmatch`` 使其在任务从未被跟踪时成为空操作
    #（例如归档一个仅存在于工作树中的任务）。
    source_rel = f"{DIR_WORKFLOW}/{DIR_TASKS}/{task_name}"
    run_git(
        ["rm", "-r", "--cached", "--ignore-unmatch", "--", source_rel],
        cwd=repo_root,
    )

    rc, _, _ = run_git(
        ["diff", "--cached", "--quiet", "--", *paths, source_rel],
        cwd=repo_root,
    )
    if rc == 0:
        print("[OK] 没有任务变更需要提交。", file=sys.stderr)
        return

    commit_msg = f"chore(task): archive {task_name}"
    rc, _, err = run_git(["commit", "-m", commit_msg], cwd=repo_root)
    if rc == 0:
        print(f"[OK] 自动提交：{commit_msg}", file=sys.stderr)
    else:
        print(f"[警告] 自动提交失败：{err.strip()}", file=sys.stderr)


# =============================================================================
# 命令：add-subtask
# =============================================================================

def cmd_add_subtask(args: argparse.Namespace) -> int:
    """将子任务链接到父任务。"""
    repo_root = get_repo_root()

    parent_dir = resolve_task_dir(args.parent_dir, repo_root)
    child_dir = resolve_task_dir(args.child_dir, repo_root)

    parent_json_path = parent_dir / FILE_TASK_JSON
    child_json_path = child_dir / FILE_TASK_JSON

    if not parent_json_path.is_file():
        print(colored(f"错误：父任务 task.json 未找到：{args.parent_dir}", Colors.RED), file=sys.stderr)
        return 1

    if not child_json_path.is_file():
        print(colored(f"错误：子任务 task.json 未找到：{args.child_dir}", Colors.RED), file=sys.stderr)
        return 1

    parent_data = read_json(parent_json_path)
    child_data = read_json(child_json_path)

    if not parent_data or not child_data:
        print(colored("错误：读取 task.json 失败", Colors.RED), file=sys.stderr)
        return 1

    # 检查子任务是否已有父任务
    existing_parent = child_data.get("parent")
    if existing_parent:
        print(colored(f"错误：子任务已有父任务：{existing_parent}", Colors.RED), file=sys.stderr)
        return 1

    # 将子任务添加到父任务的 children 列表
    parent_children = parent_data.get("children", [])
    child_dir_name = child_dir.name
    if child_dir_name not in parent_children:
        parent_children.append(child_dir_name)
        parent_data["children"] = parent_children

    # 在子任务的 task.json 中设置 parent
    child_data["parent"] = parent_dir.name

    # 写入双方
    write_json(parent_json_path, parent_data)
    write_json(child_json_path, child_data)

    print(colored(f"已链接：{child_dir.name} -> {parent_dir.name}", Colors.GREEN), file=sys.stderr)
    return 0


# =============================================================================
# 命令：remove-subtask
# =============================================================================

def cmd_remove_subtask(args: argparse.Namespace) -> int:
    """取消子任务与父任务的链接。"""
    repo_root = get_repo_root()

    parent_dir = resolve_task_dir(args.parent_dir, repo_root)
    child_dir = resolve_task_dir(args.child_dir, repo_root)

    parent_json_path = parent_dir / FILE_TASK_JSON
    child_json_path = child_dir / FILE_TASK_JSON

    if not parent_json_path.is_file():
        print(colored(f"错误：父任务 task.json 未找到：{args.parent_dir}", Colors.RED), file=sys.stderr)
        return 1

    if not child_json_path.is_file():
        print(colored(f"错误：子任务 task.json 未找到：{args.child_dir}", Colors.RED), file=sys.stderr)
        return 1

    parent_data = read_json(parent_json_path)
    child_data = read_json(child_json_path)

    if not parent_data or not child_data:
        print(colored("错误：读取 task.json 失败", Colors.RED), file=sys.stderr)
        return 1

    # 从父任务的 children 列表中移除子任务
    parent_children = parent_data.get("children", [])
    child_dir_name = child_dir.name
    if child_dir_name in parent_children:
        parent_children.remove(child_dir_name)
        parent_data["children"] = parent_children

    # 清除子任务 task.json 中的 parent 字段
    child_data["parent"] = None

    # 写入双方
    write_json(parent_json_path, parent_data)
    write_json(child_json_path, child_data)

    print(colored(f"已取消链接：{child_dir.name} 与 {parent_dir.name}", Colors.GREEN), file=sys.stderr)
    return 0


# =============================================================================
# 命令：set-branch
# =============================================================================

def cmd_set_branch(args: argparse.Namespace) -> int:
    """设置任务的 git 分支（branch）。"""
    repo_root = get_repo_root()
    target_dir = resolve_task_dir(args.dir, repo_root)
    branch = args.branch

    if not branch:
        print(colored("错误：缺少参数", Colors.RED))
        print("用法：py -3 task.py set-branch <task-dir> <branch-name>")
        return 1

    task_json = target_dir / FILE_TASK_JSON
    if not task_json.is_file():
        print(colored(f"错误：{target_dir} 中未找到 task.json", Colors.RED))
        return 1

    data = read_json(task_json)
    if not data:
        return 1

    data["branch"] = branch
    write_json(task_json, data)

    print(colored(f"✓ 分支已设置为：{branch}", Colors.GREEN))
    return 0


# =============================================================================
# 命令：set-base-branch
# =============================================================================

def cmd_set_base_branch(args: argparse.Namespace) -> int:
    """设置任务的基础分支（PR 目标）。"""
    repo_root = get_repo_root()
    target_dir = resolve_task_dir(args.dir, repo_root)
    base_branch = args.base_branch

    if not base_branch:
        print(colored("错误：缺少参数", Colors.RED))
        print("用法：py -3 task.py set-base-branch <task-dir> <base-branch>")
        print("示例：py -3 task.py set-base-branch <dir> develop")
        print()
        print("设置 PR 的目标分支（你的 feature 分支将合并到的分支）。")
        return 1

    task_json = target_dir / FILE_TASK_JSON
    if not task_json.is_file():
        print(colored(f"错误：{target_dir} 中未找到 task.json", Colors.RED))
        return 1

    data = read_json(task_json)
    if not data:
        return 1

    data["base_branch"] = base_branch
    write_json(task_json, data)

    print(colored(f"✓ 基础分支已设置为：{base_branch}", Colors.GREEN))
    print(f"  PR 目标分支：{base_branch}")
    return 0


# =============================================================================
# 命令：set-scope
# =============================================================================

def cmd_set_scope(args: argparse.Namespace) -> int:
    """设置 PR 标题的范围（scope）。"""
    repo_root = get_repo_root()
    target_dir = resolve_task_dir(args.dir, repo_root)
    scope = args.scope

    if not scope:
        print(colored("错误：缺少参数", Colors.RED))
        print("用法：py -3 task.py set-scope <task-dir> <scope>")
        return 1

    task_json = target_dir / FILE_TASK_JSON
    if not task_json.is_file():
        print(colored(f"错误：{target_dir} 中未找到 task.json", Colors.RED))
        return 1

    data = read_json(task_json)
    if not data:
        return 1

    data["scope"] = scope
    write_json(task_json, data)

    print(colored(f"✓ 范围已设置为：{scope}", Colors.GREEN))
    return 0
