#!/usr/bin/env python3
"""
独立的 .trellis/config.yaml 读取器。

镜像 common.config 的最小子集，使调用者（hooks、workflow_phase）
可以在不导入完整任务/仓库辅助函数的情况下读取配置。
在缺少/格式错误的文件上返回空 dict，保持调用者简洁。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


CONFIG_REL_PATH = ".trellis/config.yaml"


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def _strip_inline_comment(value: str) -> str:
    """移除 ` # …` 行内注释，同时保留引号字符串内的 `#`。

    YAML 将 ` #`（空格-井号）视为注释开始符；token 内部的裸 `#`
    属于值的一部分。引号字符串不受影响。
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


def _next_content_line(lines: list[str], start: int) -> tuple[int, str]:
    i = start
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped and not stripped.startswith("#"):
            return i, lines[i]
        i += 1
    return i, ""


def _parse_yaml_block(
    lines: list[str], start: int, min_indent: int, target: dict
) -> int:
    i = start
    current_list: list | None = None

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        indent = len(line) - len(line.lstrip())
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
                target[key] = value
                i += 1
            else:
                next_i, next_line = _next_content_line(lines, i + 1)
                if next_i >= len(lines):
                    target[key] = {}
                    i = next_i
                elif next_line.strip().startswith("- "):
                    current_list = []
                    target[key] = current_list
                    i += 1
                else:
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent > indent:
                        nested: dict = {}
                        target[key] = nested
                        i = _parse_yaml_block(lines, i + 1, next_indent, nested)
                    else:
                        target[key] = {}
                        i += 1
        else:
            i += 1

    return i


def parse_simple_yaml(content: str) -> dict:
    """解析 YAML 的一个小子集。完整文档见 common.config。"""
    lines = content.splitlines()
    result: dict = {}
    _parse_yaml_block(lines, 0, 0, result)
    return result


def read_trellis_config(repo_root: Optional[Path] = None) -> dict:
    """读取 .trellis/config.yaml。文件缺失或格式错误时返回 {}。"""
    root = repo_root or Path.cwd()
    config_file = root / CONFIG_REL_PATH
    try:
        content = config_file.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return {}
    try:
        parsed = parse_simple_yaml(content)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}
