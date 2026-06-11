#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务管理脚本。

用法：
    py -3 task.py create "<标题>" [--slug <名称>] [--assignee <开发者>] [--priority P0|P1|P2|P3] [--parent <目录>] [--package <软件包>]
    py -3 task.py add-context <目录> <文件> <路径> [原因]   # 添加 JSONL 条目
    py -3 task.py validate <目录>                              # 校验 JSONL 文件
    py -3 task.py list-context <目录>                          # 列出 JSONL 条目
    py -3 task.py start <目录>                                 # 设置活动任务
    py -3 task.py current [--source]                           # 显示活动任务
    py -3 task.py finish                                       # 清除活动任务
    py -3 task.py set-branch <目录> <分支>                     # 设置 git 分支
    py -3 task.py set-base-branch <目录> <分支>                # 设置拉取请求目标分支
    py -3 task.py set-scope <目录> <范围>                      # 设置拉取请求标题范围
    py -3 task.py archive <任务目录>                           # 归档已完成任务
    py -3 task.py list                                         # 列出活动任务
    py -3 task.py list-archive [月份]                          # 列出已归档任务
    py -3 task.py add-subtask <父目录> <子目录>                 # 将子任务关联到父任务
    py -3 task.py remove-subtask <父目录> <子目录>              # 取消子任务与父任务的关联
"""

from __future__ import annotations

import argparse
import sys

from common.log import Colors, colored
from common.paths import (
    DIR_WORKFLOW,
    DIR_TASKS,
    FILE_TASK_JSON,
    get_repo_root,
    get_developer,
    get_tasks_dir,
    get_current_task,
)
from common.active_task import (
    clear_active_task,
    resolve_active_task,
    resolve_context_key,
    set_active_task,
)
from common.io import read_json, write_json
from common.task_utils import resolve_task_dir, run_task_hooks
from common.tasks import iter_active_tasks, children_progress

# 从拆分模块导入命令处理函数（同时重新导出以兼容 plan.py）
from common.task_store import (
    cmd_create,
    cmd_archive,
    cmd_set_branch,
    cmd_set_base_branch,
    cmd_set_scope,
    cmd_add_subtask,
    cmd_remove_subtask,
)
from common.task_context import (
    cmd_add_context,
    cmd_validate,
    cmd_list_context,
)


# =============================================================================
# 命令：start / finish
# =============================================================================

def cmd_start(args: argparse.Namespace) -> int:
    """设置活动任务。"""
    repo_root = get_repo_root()
    task_input = args.dir

    if not task_input:
        print(colored("错误：需要提供任务目录或名称", Colors.RED))
        return 1

    # 解析任务目录（支持任务名称、相对路径或绝对路径）
    full_path = resolve_task_dir(task_input, repo_root)

    if not full_path.is_dir():
        print(colored(f"错误：未找到任务：{task_input}", Colors.RED))
        print("提示：使用任务名称（如 'my-task'）或完整路径（如 '.trellis/tasks/01-31-my-task'）")
        return 1

    # 转换为相对路径用于存储
    try:
        task_dir = full_path.relative_to(repo_root).as_posix()
    except ValueError:
        task_dir = str(full_path)

    task_json_path = full_path / FILE_TASK_JSON

    if not resolve_context_key():
        # 降级模式：无法获取会话身份信息。
        # 钩子未注入 TRELLIS_CONTEXT_ID（常见于 Windows + Claude Code、
        # --continue 恢复路径、fork 分发、钩子已禁用等情况）。跳过
        # 按会话写入指针；智能体将基于对话上下文继续工作。
        print(colored(
            "ℹ 会话身份信息不可用；活动任务指针未在本会话中持久化（降级模式）。"
            "智能体将基于对话上下文继续工作。",
            Colors.YELLOW,
        ))
        print(colored(
            "提示：请在支持会话身份的 AI IDE/会话中运行，"
            "或在运行 task.py start 之前设置 TRELLIS_CONTEXT_ID。",
            Colors.YELLOW,
        ))

        # 仍然切换 task.json 状态：planning → in_progress，以便下游阶段继续进行。
        if task_json_path.is_file():
            data = read_json(task_json_path)
            if data and data.get("status") == "planning":
                data["status"] = "in_progress"
                if write_json(task_json_path, data):
                    print(colored("✓ 状态：planning → in_progress（降级模式）", Colors.GREEN))
            run_task_hooks("after_start", task_json_path, repo_root)
        return 0

    active = set_active_task(task_dir, repo_root)
    if active:
        print(colored(f"✓ 当前任务已设置为：{task_dir}", Colors.GREEN))
        print(f"来源：{active.source}")

        if task_json_path.is_file():
            data = read_json(task_json_path)
            if data and data.get("status") == "planning":
                data["status"] = "in_progress"
                if write_json(task_json_path, data):
                    print(colored("✓ 状态：planning → in_progress", Colors.GREEN))

        print()
        print(colored("钩子现在将从该任务的 JSONL 文件注入上下文。", Colors.BLUE))

        run_task_hooks("after_start", task_json_path, repo_root)
        return 0
    else:
        print(colored("错误：设置当前任务失败", Colors.RED))
        return 1


def cmd_finish(args: argparse.Namespace) -> int:
    """清除活动任务。"""
    repo_root = get_repo_root()
    active = clear_active_task(repo_root)
    current = active.task_path

    if not current:
        print(colored("未设置当前任务", Colors.YELLOW))
        return 0

    # 在清除之前解析 task.json 路径
    task_json_path = repo_root / current / FILE_TASK_JSON

    print(colored(f"✓ 已清除当前任务（原任务：{current}）", Colors.GREEN))
    print(f"来源：{active.source}")

    if task_json_path.is_file():
        run_task_hooks("after_finish", task_json_path, repo_root)
    return 0


def cmd_current(args: argparse.Namespace) -> int:
    """显示活动任务。"""
    repo_root = get_repo_root()
    active = resolve_active_task(repo_root)

    if args.source:
        print(f"当前任务：{active.task_path or '(无)'}")
        print(f"来源：{active.source}")
        if active.stale:
            print("状态：stale")
        return 0 if active.task_path else 1

    if active.task_path:
        print(active.task_path)
        return 0

    return 1


# =============================================================================
# 命令：list
# =============================================================================

def cmd_list(args: argparse.Namespace) -> int:
    """列出活动任务。"""
    repo_root = get_repo_root()
    tasks_dir = get_tasks_dir(repo_root)
    current_task = get_current_task(repo_root)
    developer = get_developer(repo_root)
    filter_mine = args.mine
    filter_status = args.status

    if filter_mine:
        if not developer:
            print(colored("错误：未设置开发者。请先运行 init_developer.py", Colors.RED), file=sys.stderr)
            return 1
        print(colored(f"我的任务（指派人：{developer}）：", Colors.BLUE))
    else:
        print(colored("所有活动任务：", Colors.BLUE))
    print()

    # 单次遍历：通过共享迭代器收集所有任务
    all_tasks = {t.dir_name: t for t in iter_active_tasks(tasks_dir)}
    all_statuses = {name: t.status for name, t in all_tasks.items()}

    # 按层级展示任务
    count = 0

    def _print_task(dir_name: str, indent: int = 0) -> None:
        nonlocal count
        t = all_tasks[dir_name]

        # 应用 --mine 过滤器
        if filter_mine and (t.assignee or "-") != developer:
            return

        # 应用 --status 过滤器
        if filter_status and t.status != filter_status:
            return

        relative_path = f"{DIR_WORKFLOW}/{DIR_TASKS}/{dir_name}"
        marker = ""
        if relative_path == current_task:
            marker = f" {colored('<- 当前', Colors.GREEN)}"

        # 子任务进度
        progress = children_progress(t.children, all_statuses)

        # 软件包标签
        pkg_tag = f" @{t.package}" if t.package else ""

        prefix = "  " * indent + "  - "

        if filter_mine:
            print(f"{prefix}{dir_name}/ ({t.status}){pkg_tag}{progress}{marker}")
        else:
            print(f"{prefix}{dir_name}/ ({t.status}){pkg_tag}{progress} [{colored(t.assignee or '-', Colors.CYAN)}]{marker}")
        count += 1

        # 缩进打印子任务
        for child_name in t.children:
            if child_name in all_tasks:
                _print_task(child_name, indent + 1)

    # 只展示顶级任务（没有父任务的任务）
    for dir_name in sorted(all_tasks.keys()):
        if not all_tasks[dir_name].parent:
            _print_task(dir_name)

    if count == 0:
        if filter_mine:
            print("  （没有分配给您的任务）")
        else:
            print("  （没有活动任务）")

    print()
    print(f"总计：{count} 个任务")
    return 0


# =============================================================================
# 命令：list-archive
# =============================================================================

def cmd_list_archive(args: argparse.Namespace) -> int:
    """列出已归档任务。"""
    repo_root = get_repo_root()
    tasks_dir = get_tasks_dir(repo_root)
    archive_dir = tasks_dir / "archive"
    month = args.month

    print(colored("已归档任务：", Colors.BLUE))
    print()

    if month:
        month_dir = archive_dir / month
        if month_dir.is_dir():
            print(f"[{month}]")
            for d in sorted(month_dir.iterdir()):
                if d.is_dir():
                    print(f"  - {d.name}/")
        else:
            print(f"  {month} 没有归档任务")
    else:
        if archive_dir.is_dir():
            for month_dir in sorted(archive_dir.iterdir()):
                if month_dir.is_dir():
                    month_name = month_dir.name
                    # 在归档目录中没有文件夹时统计条目
                    count = sum(1 for d in month_dir.iterdir() if d.is_dir())
                    print(f"[{month_name}] - {count} 个任务")

    return 0


# =============================================================================
# 帮助
# =============================================================================

def show_usage() -> None:
    """显示使用帮助。"""
    print("""任务管理脚本

用法：
  py -3 task.py create <标题>                       创建新任务目录
  py -3 task.py create <标题> --package <软件包>    为指定软件包创建任务
  py -3 task.py create <标题> --parent <目录>       创建子任务
  py -3 task.py add-context <目录> <jsonl> <路径> [原因]  向 JSONL 添加条目
  py -3 task.py validate <目录>                     校验 JSONL 文件
  py -3 task.py list-context <目录>                 列出 JSONL 条目
  py -3 task.py start <目录>                        设置活动任务
  py -3 task.py current [--source]                  显示活动任务
  py -3 task.py finish                              清除活动任务
  py -3 task.py set-branch <目录> <分支>             设置 git 分支
  py -3 task.py set-base-branch <目录> <分支>        设置拉取请求目标分支
  py -3 task.py set-scope <目录> <范围>              设置拉取请求标题范围
  py -3 task.py archive <任务目录>                   归档已完成任务
  py -3 task.py add-subtask <父任务> <子任务>        将子任务关联到父任务
  py -3 task.py remove-subtask <父任务> <子任务>     取消子任务与父任务的关联
  py -3 task.py list [--mine] [--status <状态>]     列出任务
  py -3 task.py list-archive [YYYY-MM]               列出已归档任务

单仓库选项：
  --package <软件包>       软件包名称（根据 config.yaml 中的软件包列表校验）

列表选项：
  --mine, -m           仅显示指派给当前开发者的任务
  --status, -s <状态>  按状态过滤（planning、in_progress、review、completed）

示例：
  py -3 task.py create "添加登录功能" --slug add-login
  py -3 task.py create "添加登录功能" --slug add-login --package cli
  py -3 task.py create "子任务" --slug child --parent .trellis/tasks/01-21-parent
  py -3 task.py add-context <目录> implement .trellis/spec/cli/backend/auth.md "认证指南"
  py -3 task.py set-branch <目录> task/add-login
  py -3 task.py start .trellis/tasks/01-21-add-login
  py -3 task.py current --source
  py -3 task.py finish
  py -3 task.py archive add-login
  py -3 task.py add-subtask parent-task child-task  # 关联已有任务
  py -3 task.py remove-subtask parent-task child-task
  py -3 task.py list                               # 列出所有活动任务
  py -3 task.py list --mine                        # 仅列出我的任务
  py -3 task.py list --mine --status in_progress   # 列出我进行中的任务
""")


# =============================================================================
# 主入口
# =============================================================================

def main() -> int:
    """命令行接口入口点。"""
    # 废弃警告：`init-context` 在 v0.5.0-beta.12 中已移除。
    # 尽早检测，避免 argparse 用通用的 "invalid choice" 错误掩盖真实原因。
    if len(sys.argv) >= 2 and sys.argv[1] == "init-context":
        print(
            colored(
                "错误：`task.py init-context` 在 v0.5.0-beta.12 中已移除。",
                Colors.RED,
            ),
            file=sys.stderr,
        )
        print(
            "implement.jsonl / check.jsonl 现在在 `task.py create` 时自动生成，",
            file=sys.stderr,
        )
        print(
            "适用于支持子智能体的平台，并在阶段 1.3 由 AI 维护。",
            file=sys.stderr,
        )
        print("请参阅 .trellis/workflow.md 阶段 1.3 或运行：", file=sys.stderr)
        print(
            "  py -3 ./.trellis/scripts/get_context.py --mode phase --step 1.3",
            file=sys.stderr,
        )
        print(
            "使用 `task.py add-context <目录> implement|check <路径> <原因>` 追加条目。",
            file=sys.stderr,
        )
        return 2

    parser = argparse.ArgumentParser(
        description="任务管理脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="命令")

    # create
    p_create = subparsers.add_parser("create", help="创建新任务")
    p_create.add_argument("title", help="任务标题")
    p_create.add_argument("--slug", "-s", help="任务标识")
    p_create.add_argument("--assignee", "-a", help="指派人（开发者）")
    p_create.add_argument("--priority", "-p", default="P2", help="优先级（P0-P3）")
    p_create.add_argument("--description", "-d", help="任务描述")
    p_create.add_argument("--parent", help="父任务目录（建立子任务关联）")
    p_create.add_argument("--package", help="单仓库项目的软件包名称")

    # add-context
    p_add = subparsers.add_parser("add-context", help="添加上下文条目")
    p_add.add_argument("dir", help="任务目录")
    p_add.add_argument("file", help="JSONL 文件（implement|check）")
    p_add.add_argument("path", help="要添加的文件路径")
    p_add.add_argument("reason", nargs="?", help="添加原因")

    # validate
    p_validate = subparsers.add_parser("validate", help="校验上下文文件")
    p_validate.add_argument("dir", help="任务目录")

    # list-context
    p_listctx = subparsers.add_parser("list-context", help="列出上下文条目")
    p_listctx.add_argument("dir", help="任务目录")

    # start
    p_start = subparsers.add_parser("start", help="设置活动任务")
    p_start.add_argument("dir", help="任务目录")

    # current
    p_current = subparsers.add_parser("current", help="显示活动任务")
    p_current.add_argument("--source", action="store_true",
                           help="显示活动任务来源")

    # finish
    subparsers.add_parser("finish", help="清除活动任务")

    # set-branch
    p_branch = subparsers.add_parser("set-branch", help="设置 git 分支")
    p_branch.add_argument("dir", help="任务目录")
    p_branch.add_argument("branch", help="分支名称")

    # set-base-branch
    p_base = subparsers.add_parser("set-base-branch", help="设置拉取请求目标分支")
    p_base.add_argument("dir", help="任务目录")
    p_base.add_argument("base_branch", help="目标分支名称（拉取请求目标）")

    # set-scope
    p_scope = subparsers.add_parser("set-scope", help="设置范围")
    p_scope.add_argument("dir", help="任务目录")
    p_scope.add_argument("scope", help="范围名称")

    # archive
    p_archive = subparsers.add_parser("archive", help="归档任务")
    p_archive.add_argument("name", help="任务目录或名称")
    p_archive.add_argument("--no-commit", action="store_true", help="归档后跳过自动 git 提交")

    # list
    p_list = subparsers.add_parser("list", help="列出任务")
    p_list.add_argument("--mine", "-m", action="store_true", help="仅显示我的任务")
    p_list.add_argument("--status", "-s", help="按状态过滤")

    # add-subtask
    p_addsub = subparsers.add_parser("add-subtask", help="将子任务关联到父任务")
    p_addsub.add_argument("parent_dir", help="父任务目录")
    p_addsub.add_argument("child_dir", help="子任务目录")

    # remove-subtask
    p_rmsub = subparsers.add_parser("remove-subtask", help="取消子任务与父任务的关联")
    p_rmsub.add_argument("parent_dir", help="父任务目录")
    p_rmsub.add_argument("child_dir", help="子任务目录")

    # list-archive
    p_listarch = subparsers.add_parser("list-archive", help="列出已归档任务")
    p_listarch.add_argument("month", nargs="?", help="月份（YYYY-MM）")

    args = parser.parse_args()

    if not args.command:
        show_usage()
        return 1

    commands = {
        "create": cmd_create,
        "add-context": cmd_add_context,
        "validate": cmd_validate,
        "list-context": cmd_list_context,
        "start": cmd_start,
        "current": cmd_current,
        "finish": cmd_finish,
        "set-branch": cmd_set_branch,
        "set-base-branch": cmd_set_base_branch,
        "set-scope": cmd_set_scope,
        "archive": cmd_archive,
        "add-subtask": cmd_add_subtask,
        "remove-subtask": cmd_remove_subtask,
        "list": cmd_list,
        "list-archive": cmd_list_archive,
    }

    if args.command in commands:
        return commands[args.command](args)
    else:
        show_usage()
        return 1


if __name__ == "__main__":
    sys.exit(main())
