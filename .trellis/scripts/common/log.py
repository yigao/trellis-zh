"""
终端输出工具：颜色和结构化日志。

所有 Trellis 脚本中使用的 Colors 和 log_* 函数的唯一来源。
"""

from __future__ import annotations


class Colors:
    """终端输出的 ANSI 颜色代码。"""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    DIM = "\033[2m"
    NC = "\033[0m"  # 无颜色 / 重置


def colored(text: str, color: str) -> str:
    """将 ANSI 颜色应用于文本。"""
    return f"{color}{text}{Colors.NC}"


def log_info(msg: str) -> None:
    """打印带有 [INFO] 前缀的信息级别消息。"""
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")


def log_success(msg: str) -> None:
    """打印带有 [SUCCESS] 前缀的成功消息。"""
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {msg}")


def log_warn(msg: str) -> None:
    """打印带有 [WARN] 前缀的警告消息。"""
    print(f"{Colors.YELLOW}[WARN]{Colors.NC} {msg}")


def log_error(msg: str) -> None:
    """打印带有 [ERROR] 前缀的错误消息。"""
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}")
