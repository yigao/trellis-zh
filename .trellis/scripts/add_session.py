#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向日志文件添加新会话并更新 index.md。

用法：
    py -3 add_session.py --title "标题" --commit "哈希" --summary "摘要" [--package cli]
    py -3 add_session.py --title "标题" --branch "feat/my-branch"

    # 通过 stdin 管道传入详细内容（使用 --stdin 显式启用）：
    cat << 'EOF' | py -3 add_session.py --stdin --title "标题" --summary "摘要"
    <会话内容在此>
    EOF

分支解析顺序：
    1. --branch 命令行参数（显式指定）
    2. task.json 的 branch 字段（来自活动任务）
    3. git branch --show-current（自动检测）
    4. None（优雅地省略）
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

from common.paths import (
    FILE_JOURNAL_PREFIX,
    get_repo_root,
    get_current_task,
    get_developer,
    get_workspace_dir,
)
from common.developer import ensure_developer
from common.git import run_git
from common.safe_commit import (
    print_gitignore_warning,
    safe_git_add,
    safe_trellis_paths_to_add,
)
from common.tasks import load_task
from common.config import (
    get_packages,
    get_session_auto_commit,
    get_session_commit_message,
    get_max_journal_lines,
    is_monorepo,
    resolve_package,
    validate_package,
)


# =============================================================================
# 辅助函数
# =============================================================================

def get_latest_journal_info(dev_dir: Path) -> tuple[Path | None, int, int]:
    """获取最新日志文件信息。

    返回：
        元组 (文件路径, 文件编号, 行数)。
    """
    latest_file: Path | None = None
    latest_num = -1

    for f in dev_dir.glob(f"{FILE_JOURNAL_PREFIX}*.md"):
        if not f.is_file():
            continue

        match = re.search(r"(\d+)$", f.stem)
        if match:
            num = int(match.group(1))
            if num > latest_num:
                latest_num = num
                latest_file = f

    if latest_file:
        lines = len(latest_file.read_text(encoding="utf-8").splitlines())
        return latest_file, latest_num, lines

    return None, 0, 0


def get_current_session(index_file: Path) -> int:
    """从 index.md 获取当前会话编号。"""
    if not index_file.is_file():
        return 0

    content = index_file.read_text(encoding="utf-8")
    for line in content.splitlines():
        if "Total Sessions" in line:
            match = re.search(r":\s*(\d+)", line)
            if match:
                return int(match.group(1))
    return 0


def _extract_journal_num(filename: str) -> int:
    """从文件名中提取日志编号用于排序。"""
    match = re.search(r"(\d+)", filename)
    return int(match.group(1)) if match else 0


def count_journal_files(dev_dir: Path, active_num: int) -> str:
    """统计日志文件并返回表格行。"""
    active_file = f"{FILE_JOURNAL_PREFIX}{active_num}.md"
    result_lines = []

    files = sorted(
        [f for f in dev_dir.glob(f"{FILE_JOURNAL_PREFIX}*.md") if f.is_file()],
        key=lambda f: _extract_journal_num(f.stem),
        reverse=True
    )

    for f in files:
        filename = f.name
        lines = len(f.read_text(encoding="utf-8").splitlines())
        status = "活动" if filename == active_file else "已归档"
        result_lines.append(f"| `{filename}` | ~{lines} | {status} |")

    return "\n".join(result_lines)


def create_new_journal_file(
    dev_dir: Path, num: int, developer: str, today: str, max_lines: int = 2000,
) -> Path:
    """创建新的日志文件。"""
    prev_num = num - 1
    new_file = dev_dir / f"{FILE_JOURNAL_PREFIX}{num}.md"

    content = f"""# 日志 - {developer}（第 {num} 部分）

> 接续自 `{FILE_JOURNAL_PREFIX}{prev_num}.md`（在约 {max_lines} 行时归档）
> 开始日期：{today}

---

"""
    new_file.write_text(content, encoding="utf-8")
    return new_file


def generate_session_content(
    session_num: int,
    title: str,
    commit: str,
    summary: str,
    extra_content: str,
    today: str,
    package: str | None = None,
    branch: str | None = None,
) -> str:
    """生成会话内容。"""
    if commit and commit != "-":
        commit_table = """| 哈希 | 消息 |
|------|------|"""
        for c in commit.split(","):
            c = c.strip()
            commit_table += f"\n| `{c}` | (参见 git log) |"
    else:
        commit_table = "（无提交 - 规划会话）"

    package_line = f"\n**软件包**：{package}" if package else ""
    branch_line = f"\n**分支**：`{branch}`" if branch else ""

    return f"""

## 会话 {session_num}：{title}

**日期**：{today}
**任务**：{title}{package_line}{branch_line}

### 摘要

{summary}

### 主要变更

{extra_content}

### Git 提交

{commit_table}

### 测试

- [OK]（添加测试结果）

### 状态

[OK] **已完成**

### 后续步骤

- 无 - 任务已完成
"""


def update_index(
    index_file: Path,
    dev_dir: Path,
    title: str,
    commit: str,
    new_session: int,
    active_file: str,
    today: str,
    branch: str | None = None,
) -> bool:
    """使用新会话信息更新 index.md。"""
    # 格式化提交信息用于展示
    commit_display = "-"
    if commit and commit != "-":
        commit_display = re.sub(r"([a-f0-9]{7,})", r"`\1`", commit.replace(",", ", "))

    # 从 active_file 名称中获取文件编号
    match = re.search(r"(\d+)", active_file)
    active_num = int(match.group(1)) if match else 0
    files_table = count_journal_files(dev_dir, active_num)

    print(f"正在为会话 {new_session} 更新 index.md...")
    print(f"  标题：{title}")
    print(f"  提交：{commit_display}")
    print(f"  活动文件：{active_file}")
    print()

    content = index_file.read_text(encoding="utf-8")

    if "@@@auto:current-status" not in content:
        print("错误：在 index.md 中未找到标记。请确保标记存在。", file=sys.stderr)
        return False

    # 处理各个区块
    lines = content.splitlines()
    new_lines = []

    in_current_status = False
    in_active_documents = False
    in_session_history = False
    header_written = False

    for line in lines:
        if "@@@auto:current-status" in line:
            new_lines.append(line)
            in_current_status = True
            new_lines.append(f"- **活动文件**：`{active_file}`")
            new_lines.append(f"- **会话总数**：{new_session}")
            new_lines.append(f"- **最近活动**：{today}")
            continue

        if "@@@/auto:current-status" in line:
            in_current_status = False
            new_lines.append(line)
            continue

        if "@@@auto:active-documents" in line:
            new_lines.append(line)
            in_active_documents = True
            new_lines.append("| 文件 | 行数 | 状态 |")
            new_lines.append("|------|------|------|")
            new_lines.append(files_table)
            continue

        if "@@@/auto:active-documents" in line:
            in_active_documents = False
            new_lines.append(line)
            continue

        if "@@@auto:session-history" in line:
            new_lines.append(line)
            in_session_history = True
            header_written = False
            continue

        if "@@@/auto:session-history" in line:
            in_session_history = False
            new_lines.append(line)
            continue

        if in_current_status:
            continue

        if in_active_documents:
            continue

        if in_session_history:
            # 将旧的 4/6 列表头迁移到仅包含分支的 5 列历史记录。
            if re.match(
                r"^\|\s*#\s*\|\s*Date\s*\|\s*Title\s*\|\s*Commits\s*\|\s*Branch\s*\|\s*Base Branch\s*\|\s*$",
                line,
            ):
                new_lines.append("| # | 日期 | 标题 | 提交 | 分支 |")
                continue
            if re.match(r"^\|\s*#\s*\|\s*Date\s*\|\s*Title\s*\|\s*Commits\s*\|\s*Branch\s*\|\s*$", line):
                new_lines.append("| # | 日期 | 标题 | 提交 | 分支 |")
                continue
            if re.match(r"^\|\s*#\s*\|\s*Date\s*\|\s*Title\s*\|\s*Commits\s*\|\s*$", line):
                new_lines.append("| # | 日期 | 标题 | 提交 | 分支 |")
                continue
            if re.match(r"^\|[-| ]+\|\s*$", line) and not header_written:
                new_lines.append("|---|------|------|------|------|")
                new_lines.append(f"| {new_session} | {today} | {title} | {commit_display} | `{branch or '-'}` |")
                header_written = True
                continue
            new_lines.append(line)
            continue

        new_lines.append(line)

    index_file.write_text("\n".join(new_lines), encoding="utf-8")
    print("[OK] index.md 更新成功！")
    return True


# =============================================================================
# 主函数
# =============================================================================

def _auto_commit_workspace(repo_root: Path) -> None:
    """暂存 Trellis 所属的工作区 + 任务路径并提交。

    路径范围限定为特定产物（日志文件、index.md、
    活动任务目录、归档子树）。我们绝不会对整个
    `.trellis/` 目录树执行 `git add`，如果 `.gitignore` 阻止了特定路径，
    我们会警告并跳过 — 绝不会使用 ``-f`` 重试。

    遵循 ``.trellis/config.yaml`` 中的 ``session_auto_commit`` 设置：当设置为
    ``false`` 时，此函数立即返回而不操作 git
    （调用方仍然会将日志/index 文件写入磁盘）。
    """
    if not get_session_auto_commit(repo_root):
        print(
            "[OK] session_auto_commit: false — 跳过 git 暂存/提交。",
            file=sys.stderr,
        )
        return

    commit_msg = get_session_commit_message(repo_root)
    paths = safe_trellis_paths_to_add(repo_root)
    if not paths:
        print("[OK] 没有工作区变更需要提交。", file=sys.stderr)
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

    # 检查我们刚暂存的路径是否有暂存变更。
    rc, _, _ = run_git(
        ["diff", "--cached", "--quiet", "--", *paths], cwd=repo_root
    )
    if rc == 0:
        print("[OK] 没有工作区变更需要提交。", file=sys.stderr)
        return

    rc, _, commit_err = run_git(["commit", "-m", commit_msg], cwd=repo_root)
    if rc == 0:
        print(f"[OK] 自动提交：{commit_msg}", file=sys.stderr)
    else:
        print(
            f"[警告] 自动提交失败：{commit_err.strip()}",
            file=sys.stderr,
        )


def add_session(
    title: str,
    commit: str = "-",
    summary: str = "（添加摘要）",
    extra_content: str = "（添加详情）",
    auto_commit: bool = True,
    package: str | None = None,
    branch: str | None = None,
) -> int:
    """添加新会话。"""
    repo_root = get_repo_root()
    ensure_developer(repo_root)

    developer = get_developer(repo_root)
    if not developer:
        print("错误：开发者未初始化", file=sys.stderr)
        return 1

    dev_dir = get_workspace_dir(repo_root)
    if not dev_dir:
        print("错误：未找到工作区目录", file=sys.stderr)
        return 1

    max_lines = get_max_journal_lines(repo_root)

    index_file = dev_dir / "index.md"
    today = datetime.now().strftime("%Y-%m-%d")

    journal_file, current_num, current_lines = get_latest_journal_info(dev_dir)
    current_session = get_current_session(index_file)
    new_session = current_session + 1

    session_content = generate_session_content(
        new_session, title, commit, summary, extra_content, today, package,
        branch,
    )
    content_lines = len(session_content.splitlines())

    print("========================================", file=sys.stderr)
    print("添加会话", file=sys.stderr)
    print("========================================", file=sys.stderr)
    print("", file=sys.stderr)
    print(f"会话：{new_session}", file=sys.stderr)
    print(f"标题：{title}", file=sys.stderr)
    print(f"提交：{commit}", file=sys.stderr)
    print("", file=sys.stderr)
    print(f"当前日志文件：{FILE_JOURNAL_PREFIX}{current_num}.md", file=sys.stderr)
    print(f"当前行数：{current_lines}", file=sys.stderr)
    print(f"新内容行数：{content_lines}", file=sys.stderr)
    print(f"追加后总计：{current_lines + content_lines}", file=sys.stderr)
    print("", file=sys.stderr)

    target_file = journal_file
    target_num = current_num

    if current_lines + content_lines > max_lines:
        target_num = current_num + 1
        print(f"[!] 超过 {max_lines} 行，正在创建 {FILE_JOURNAL_PREFIX}{target_num}.md", file=sys.stderr)
        target_file = create_new_journal_file(dev_dir, target_num, developer, today, max_lines)
        print(f"已创建：{target_file}", file=sys.stderr)

    # 追加会话内容
    if target_file:
        with target_file.open("a", encoding="utf-8") as f:
            f.write(session_content)
        print(f"[OK] 会话已追加到 {target_file.name}", file=sys.stderr)

    print("", file=sys.stderr)

    # 更新 index.md
    active_file = f"{FILE_JOURNAL_PREFIX}{target_num}.md"
    if not update_index(
        index_file,
        dev_dir,
        title,
        commit,
        new_session,
        active_file,
        today,
        branch,
    ):
        return 1

    print("", file=sys.stderr)
    print("========================================", file=sys.stderr)
    print(f"[OK] 会话 {new_session} 添加成功！", file=sys.stderr)
    print("========================================", file=sys.stderr)
    print("", file=sys.stderr)
    print("已更新文件：", file=sys.stderr)
    print(f"  - {target_file.name if target_file else '日志'}", file=sys.stderr)
    print("  - index.md", file=sys.stderr)

    # 自动提交工作区变更
    if auto_commit:
        print("", file=sys.stderr)
        _auto_commit_workspace(repo_root)

    return 0


# =============================================================================
# 主入口
# =============================================================================

def main() -> int:
    """命令行接口入口点。"""
    parser = argparse.ArgumentParser(
        description="向日志文件添加新会话并更新 index.md"
    )
    parser.add_argument("--title", required=True, help="会话标题")
    parser.add_argument("--commit", default="-", help="逗号分隔的提交哈希")
    parser.add_argument("--summary", default="（添加摘要）", help="简要摘要")
    parser.add_argument("--content-file", help="包含详细内容的文件路径")
    parser.add_argument("--package", help="软件包名称标签（如 cli、docs-site）")
    parser.add_argument("--branch", help="分支名称（如省略则自动检测）")
    parser.add_argument("--no-commit", action="store_true",
                        help="跳过工作区变更的自动提交")
    parser.add_argument("--stdin", action="store_true",
                        help="从 stdin 读取额外内容（需显式启用）")

    args = parser.parse_args()

    extra_content = "（添加详情）"
    if args.content_file:
        content_path = Path(args.content_file)
        if content_path.is_file():
            extra_content = content_path.read_text(encoding="utf-8")
    elif args.stdin:
        extra_content = sys.stdin.read()

    # 加载一次活动任务 — 供软件包和分支解析共用
    repo_root = get_repo_root()
    current = get_current_task(repo_root)
    task_data = load_task(repo_root / current) if current else None

    package = args.package
    if package:
        # 命令行指定：单仓库项目快速失败，单仓库忽略
        if not is_monorepo(repo_root):
            print("警告：--package 在单仓库项目中被忽略", file=sys.stderr)
            package = None
        elif not validate_package(package, repo_root):
            packages = get_packages(repo_root)
            available = ", ".join(sorted(packages.keys())) if packages else "（无）"
            print(f"错误：未知软件包 '{package}'。可用的软件包：{available}", file=sys.stderr)
            return 1
    else:
        # 推断：活动任务的 task.json.package → default_package → None
        task_package = task_data.package if task_data else None
        package = resolve_package(task_package, repo_root)

    # 解析分支：命令行 → task.json → git 自动检测 → None
    branch = args.branch

    if not branch:
        if task_data and task_data.raw.get("branch"):
            branch = task_data.raw["branch"]
        else:
            _, branch_out, _ = run_git(["branch", "--show-current"], cwd=repo_root)
            detected = branch_out.strip()
            if detected:
                branch = detected

    return add_session(
        args.title, args.commit, args.summary, extra_content,
        auto_commit=not args.no_commit,
        package=package,
        branch=branch,
    )


if __name__ == "__main__":
    sys.exit(main())
