"""
JSON 文件 I/O 工具。

提供 read_json 和 write_json 作为所有 Trellis 脚本中
JSON 文件操作的唯一来源。
"""

from __future__ import annotations

import json
from pathlib import Path


def read_json(path: Path) -> dict | None:
    """读取并解析 JSON 文件。

    如果文件不存在、JSON 无效或无法读取，返回 None。
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def write_json(path: Path, data: dict) -> bool:
    """将 dict 写入 JSON 文件，使用美化格式。

    成功返回 True，出错返回 False。
    """
    try:
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return True
    except (OSError, IOError):
        return False
