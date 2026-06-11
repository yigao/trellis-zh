"""
Git 命令执行工具。

所有 Trellis 脚本运行 git 命令的单一可信来源。
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def run_git(args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """运行 git 命令并返回 (returncode, stdout, stderr)。

    使用 UTF-8 编码和 -c i18n.logOutputEncoding=UTF-8 参数，
    确保跨所有平台（Windows、macOS、Linux）的输出一致。
    """
    try:
        git_args = ["git", "-c", "i18n.logOutputEncoding=UTF-8"] + args
        result = subprocess.run(
            git_args,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)
