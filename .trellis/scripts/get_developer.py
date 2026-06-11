#!/usr/bin/env python3
"""
获取当前开发者名称。

这是使用 common/paths.py 的包装器。
"""

from __future__ import annotations

import sys

from common.paths import get_developer


def main() -> None:
    """命令行接口入口点。"""
    developer = get_developer()
    if developer:
        print(developer)
    else:
        print("开发者未初始化", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
