#!/usr/bin/env python3
"""
Trellis 配置读取器。

从 .trellis/config.yaml 读取配置，提供合理的默认值。
"""

from __future__ import annotations

import sys
from pathlib import Path

from .paths import DIR_WORKFLOW, get_repo_root


# =============================================================================
# YAML 简易解析器（无外部依赖）
# =============================================================================


def _unquote(s: str) -> str:
    """移除恰好一层匹配的包围引号。

    与 str.strip('"') 不同，此函数仅移除最外层的一对引号，
    保留值内部的嵌套引号。

    示例:
        _unquote('"hello"')        -> 'hello'
        _unquote("'hello'")        -> 'hello'
        _unquote('"echo \\'hi\\'"')  -> "echo 'hi'"
        _unquote('hello')          -> 'hello'
        _unquote('"hello\\'')       -> '"hello\\''  （不匹配，保持不变）
    """
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


def _strip_inline_comment(value: str) -> str:
    """移除 ` # …` 行内注释，同时保留引号字符串内的 `#`。

    YAML 将 ` #`（空格-井号）视为注释开始符；token 内部的裸 `#`
    属于值的一部分。引号字符串不受影响。

    与 :func:`common.trellis_config._strip_inline_comment` 镜像，
    确保两个解析器对 ``key: value  # comment`` 的处理一致。
    """
    in_quote: str | None = None
    for idx, ch in enumerate(value):
        if in_quote:
            if ch == in_quote:
                in_quote = None
            continue
        if ch in ('"', "'"):
            in_quote = ch
            continue
        if ch == "#" and (idx == 0 or value[idx - 1].isspace()):
            return value[:idx]
    return value


def parse_simple_yaml(content: str) -> dict:
    """解析简单 YAML，支持嵌套 dict（无外部依赖）。

    支持:
        - key: value (字符串)
        - key: (后跟列表项)
            - item1
            - item2
        - key: (后跟嵌套 dict)
            nested_key: value
            nested_key2:
              - item

    使用缩进检测嵌套（比父级多 2+ 空格 = 子级）。

    参数:
        content: YAML 内容字符串。

    返回:
        解析后的 dict（值可以是 str、list[str] 或 dict）。
    """
    lines = content.splitlines()
    result: dict = {}
    _parse_yaml_block(lines, 0, 0, result)
    return result


def _parse_yaml_block(
    lines: list[str], start: int, min_indent: int, target: dict
) -> int:
    """解析 YAML 块到目标 dict，返回下一行索引。"""
    i = start
    current_list: list | None = None

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 跳过空行和注释
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        # 计算缩进
        indent = len(line) - len(line.lstrip())

        # 如果缩进小于我们块的最小缩进，说明已经结束
        if indent < min_indent:
            break

        if stripped.startswith("- "):
            if current_list is not None:
                current_list.append(_unquote(stripped[2:].strip()))
            i += 1
        elif ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = _strip_inline_comment(value).strip()
            value = _unquote(value)
            current_list = None

            if value:
                # key: value
                target[key] = value
                i += 1
            else:
                # key: (无值) — 向前查看以判断是列表还是嵌套 dict
                next_i, next_line = _next_content_line(lines, i + 1)
                if next_i >= len(lines):
                    target[key] = {}
                    i = next_i
                elif next_line.strip().startswith("- "):
                    # 是列表
                    current_list = []
                    target[key] = current_list
                    i += 1
                else:
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent > indent:
                        # 是嵌套 dict
                        nested: dict = {}
                        target[key] = nested
                        i = _parse_yaml_block(lines, i + 1, next_indent, nested)
                    else:
                        # 空值，后续行缩进相同或更小
                        target[key] = {}
                        i += 1
        else:
            i += 1

    return i


def _next_content_line(lines: list[str], start: int) -> tuple[int, str]:
    """查找下一个非空、非注释行。"""
    i = start
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped and not stripped.startswith("#"):
            return i, lines[i]
        i += 1
    return i, ""


# 默认值
DEFAULT_SESSION_COMMIT_MESSAGE = "chore: record journal"
DEFAULT_MAX_JOURNAL_LINES = 2000
DEFAULT_SESSION_AUTO_COMMIT = True

CONFIG_FILE = "config.yaml"


def _is_true_config_value(value: object) -> bool:
    """当配置值表示启用标志时返回 True。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return False


def _get_config_path(repo_root: Path | None = None) -> Path:
    """获取 config.yaml 的路径。"""
    root = repo_root or get_repo_root()
    return root / DIR_WORKFLOW / CONFIG_FILE


def _load_config(repo_root: Path | None = None) -> dict:
    """加载并解析 config.yaml。遇到任何错误返回空 dict。"""
    config_file = _get_config_path(repo_root)
    try:
        content = config_file.read_text(encoding="utf-8")
        return parse_simple_yaml(content)
    except (OSError, IOError):
        return {}


def get_session_commit_message(repo_root: Path | None = None) -> str:
    """获取用于自动提交会话（session）记录的提交信息。"""
    config = _load_config(repo_root)
    return config.get("session_commit_message", DEFAULT_SESSION_COMMIT_MESSAGE)


def get_max_journal_lines(repo_root: Path | None = None) -> int:
    """获取每个日志（journal）文件的最大行数。"""
    config = _load_config(repo_root)
    value = config.get("max_journal_lines", DEFAULT_MAX_JOURNAL_LINES)
    try:
        return int(value)
    except (ValueError, TypeError):
        return DEFAULT_MAX_JOURNAL_LINES


def get_session_auto_commit(repo_root: Path | None = None) -> bool:
    """脚本是否应自动暂存并自动提交会话/任务变更。

    同时控制 ``add_session.py:_auto_commit_workspace`` 和
    ``task_store.py:_auto_commit_archive``。

    默认值: ``True``（现有行为 — 自动暂存并自动提交）。
    在 ``.trellis/config.yaml`` 中设置 ``session_auto_commit: false`` 可完全跳过
    自动暂存；日志/归档文件仍写入磁盘，但用户自行管理 ``git add`` / ``git commit``。

    接受原生 YAML 布尔值（``true`` / ``false``）以及字符串
    别名 ``true / false / yes / no / 1 / 0 / on / off``（不区分大小写）。
    无效值会回退到 ``True`` 并在 stderr 打印警告。
    """
    config = _load_config(repo_root)
    raw = config.get("session_auto_commit", DEFAULT_SESSION_AUTO_COMMIT)
    if isinstance(raw, bool):
        return raw
    s = str(raw).strip().lower()
    if s in ("true", "yes", "1", "on"):
        return True
    if s in ("false", "no", "0", "off"):
        return False
    print(
        f"[WARN] 无效的 session_auto_commit 值: {raw!r}; 使用 true（默认值）",
        file=sys.stderr,
    )
    return DEFAULT_SESSION_AUTO_COMMIT


def get_hooks(event: str, repo_root: Path | None = None) -> list[str]:
    """获取生命周期（lifecycle）事件的钩子（hook）命令。

    参数:
        event: 事件名称（例如 "after_create"、"after_archive"）。
        repo_root: 仓库根目录路径。

    返回:
        要执行的 shell 命令列表，如果未配置则返回空列表。
    """
    config = _load_config(repo_root)
    hooks = config.get("hooks")
    if not isinstance(hooks, dict):
        return []
    commands = hooks.get(event)
    if isinstance(commands, list):
        return [str(c) for c in commands]
    return []


# =============================================================================
# 多仓库（Monorepo）/ 包（Packages）
# =============================================================================


def get_packages(repo_root: Path | None = None) -> dict[str, dict] | None:
    """获取多仓库包声明。

    返回:
        将包名映射到其配置（路径、类型等）的 dict，
        如果未配置则返回 None（单仓库模式）。

    示例返回:
        {"cli": {"path": "packages/cli"}, "docs-site": {"path": "docs-site", "type": "submodule"}}
    """
    config = _load_config(repo_root)
    packages = config.get("packages")
    if not isinstance(packages, dict):
        return None
    # 确保每个值都是 dict（过滤掉标量条目）
    filtered = {k: v for k, v in packages.items() if isinstance(v, dict)}
    if not filtered:
        return None
    return filtered


def get_default_package(repo_root: Path | None = None) -> str | None:
    """从配置中获取默认包名。

    返回:
        包名字符串，如果未配置则返回 None。
    """
    config = _load_config(repo_root)
    value = config.get("default_package")
    return str(value) if value else None


def get_submodule_packages(repo_root: Path | None = None) -> dict[str, str]:
    """获取作为 git 子模块的包。

    返回:
        将包名映射到其路径的 dict，仅适用于子模块类型的包。
        如果未配置则返回空 dict。

    示例返回:
        {"docs-site": "docs-site"}
    """
    packages = get_packages(repo_root)
    if packages is None:
        return {}
    return {
        name: cfg.get("path", name)
        for name, cfg in packages.items()
        if cfg.get("type") == "submodule"
    }


def get_git_packages(repo_root: Path | None = None) -> dict[str, str]:
    """获取拥有独立 git 仓库的包。

    这些是拥有自己的 .git 的子目录（非子模块），
    在 config.yaml 中标记为 ``git: true``。

    返回:
        将包名映射到其路径的 dict，仅适用于 git-repo 类型的包。
        如果未配置则返回空 dict。

    示例配置::

        packages:
          backend:
            path: iqs
            git: true

    示例返回::

        {"backend": "iqs"}
    """
    packages = get_packages(repo_root)
    if packages is None:
        return {}
    return {
        name: cfg.get("path", name)
        for name, cfg in packages.items()
        if _is_true_config_value(cfg.get("git"))
    }


def is_monorepo(repo_root: Path | None = None) -> bool:
    """检查项目是否配置为多仓库（config 中是否有 packages）。"""
    return get_packages(repo_root) is not None


def get_spec_base(package: str | None = None, repo_root: Path | None = None) -> str:
    """获取规范（spec）目录相对于 .trellis/ 的基础路径。

    单仓库: 返回 "spec"
    带包的多仓库: 返回 "spec/<package>"
    无包的多仓库: 返回 "spec"（调用者应指定包）
    """
    if package and is_monorepo(repo_root):
        return f"spec/{package}"
    return "spec"


def validate_package(package: str, repo_root: Path | None = None) -> bool:
    """检查包名在当前项目中是否有效。

    单仓库（未配置包）: 始终返回 True。
    多仓库: 仅当包存在于 config.yaml 的 packages 中时返回 True。
    """
    packages = get_packages(repo_root)
    if packages is None:
        return True  # 单仓库，无需验证
    return package in packages


def resolve_package(
    task_package: str | None = None,
    repo_root: Path | None = None,
) -> str | None:
    """从推断来源解析包名并验证。

    按顺序检查: task_package → default_package。
    无效的推断值会向 stderr 打印警告并跳过。

    返回:
        解析后的包名，如果找不到有效包则返回 None。

    注意:
        CLI 的 --package 应由调用者单独验证
        （出错时快速失败并列出可用包）。
    """
    packages = get_packages(repo_root)
    if packages is None:
        return None  # 单仓库，不需要包

    # 尝试 task_package（防御格式错误的 JSON 中的非字符串值）
    if task_package and isinstance(task_package, str):
        if task_package in packages:
            return task_package
        print(
            f"警告: task.json 包 '{task_package}' 未在 config 中找到，跳过",
            file=sys.stderr,
        )

    # 尝试 default_package
    default = get_default_package(repo_root)
    if default:
        if default in packages:
            return default
        print(
            f"警告: default_package '{default}' 未在 config 中找到，跳过",
            file=sys.stderr,
        )

    return None


def get_spec_scope(repo_root: Path | None = None) -> list[str] | str | None:
    """获取 session.spec_scope 配置。

    返回:
        list[str]: 要纳入规范（spec）扫描的包名列表。
        str: "active_task" 表示使用当前任务的包。
        None: 未配置范围（扫描所有包）。
    """
    config = _load_config(repo_root)
    session = config.get("session")
    if not isinstance(session, dict):
        return None

    scope = session.get("spec_scope")
    if scope is None:
        return None
    if isinstance(scope, str):
        return scope  # 例如 "active_task"
    if isinstance(scope, list):
        return [str(s) for s in scope]
    return None
