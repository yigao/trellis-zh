#!/usr/bin/env python3
"""Trellis 每轮面包屑（breadcrumb）钩子（hook）（等价于 UserPromptSubmit / BeforeAgent）。

每次用户输入提示词时运行。通过 Trellis 的会话（session）感知的活动任务
（active task）解析器解析活动任务，并输出一个简短的 <workflow-state>
块，提醒主 AI 当前活动任务及其预期工作流（workflow）。

输出的 ``hookEventName`` 字段是平台感知的：大多数宿主期望
``UserPromptSubmit``（Claude Code 命名，也被 Cursor / Qoder /
CodeBuddy / Droid / Codex / Copilot 的接线所接受），但 Gemini CLI 0.40.x
将其每轮事件重命名为 ``BeforeAgent``，其 schema 验证器会拒绝旧名称。
``_detect_platform`` 在运行时选择合适的值。
面包屑文本完全从 workflow.md 的
[workflow-state:STATUS] 标签块中提取 — workflow.md 是唯一真相来源。
本脚本中没有回退字典：当 workflow.md 缺失或标签不存在时，面包屑会降级为
通用的 "请参阅 workflow.md 了解当前步骤。" 行，让用户看到（并修复）
损坏的状态，而不是让 hook 静默掩盖问题。

在所有支持 hook 的平台上共享（Claude、Cursor、Codex、Qoder、
CodeBuddy、Droid、Gemini、Copilot）。Kiro 未接入（没有每轮
hook 入口点）。在初始化时通过 writeSharedHooks() 写入各平台的
hooks 目录。

静默退出 0 的情况（无输出）：
  - 未找到 .trellis/ 目录（非 Trellis 项目）
  - task.json 格式错误或缺少 status
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# 在 Windows 上强制 stdin/stdout/stderr 使用 UTF-8。默认编码页是
# cp936 / cp1252 等 — 非 ASCII 内容（中文任务名、prd 片段）
# 在 stdin（来自宿主 CLI 的 hook 负载）和 stdout（我们输出的块）
# 上都会引发 UnicodeDecodeError / UnicodeEncodeError。等价于 `python -X utf8`
# 但按流逐一应用，这样就不依赖宿主 CLI 的命令接线方式。
if sys.platform.startswith("win"):
    import io as _io
    for _stream_name in ("stdin", "stdout", "stderr"):
        _stream = getattr(sys, _stream_name, None)
        if _stream is None:
            continue
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
            except Exception:
                pass
        elif hasattr(_stream, "detach"):
            try:
                setattr(sys, _stream_name, _io.TextIOWrapper(_stream.detach(), encoding="utf-8", errors="replace"))
            except Exception:
                pass
from typing import Optional


CODEX_SUB_AGENT_NOTICE = """<sub-agent-notice>
子智能体通知 — 如果通过 spawn_agent 派生，请先阅读

如果你的父会话（session）通过 spawn_agent 派生你，并附带了显式的任务
消息（在此 hook 输出上方），那条消息就是你唯一的工作。
- 严格按照父消息的内容执行，然后返回。
- 忽略此通知下方的所有 Trellis 工作流指引。
- 不要调用 task.py start、task.py add-context 或 task.py archive。
- 不要调用 wait_agent 或 spawn_agent。
- 不要修改 .trellis/tasks/* 或任何其他文件，除非父消息
  明确要求这样做。

如果你是主交互式 Codex 会话，且用户正在终端输入（无父智能体），
则正常使用下方的工作流指引。
</sub-agent-notice>"""


# Codex 无活动任务时的引导（bootstrap）通知。替代了重量级的
# SessionStart 上下文注入（context injection）— 不直接推送 9.5 KB 的
# 工作流文本，而是轻轻提醒 AI 去读取一次 `trellis-start` skill。
# 当 status == "no_task" 时此提醒会持续显示（文本量小，AI 读一次后
# 不会再重复读取）。一旦创建任务，面包屑状态会翻转，此通知自动消失。
# 子智能体通过上方的 <sub-agent-notice> 和下文的显式豁免被排除。
CODEX_NO_TASK_BOOTSTRAP_NOTICE = """<trellis-bootstrap>
你正在 Trellis 管理的 Codex 会话中运行，当前没有活动任务。
如果你在本会话中尚未加载 Trellis 上下文，请先读取一次 `trellis-start` skill：

  $trellis-start

（等价于读取 `.agents/skills/trellis-start/SKILL.md` 并执行其步骤 1-3）

该 skill 带你了解 workflow.md、开发者（developer）资料、git 状态、活动任务和 spec
索引。然后按照下方的 <workflow-state> A/B/C 规则处理用户请求。

子智能体豁免：如果你是子智能体（通过 spawn_agent 派生，带有父任务
消息），请不要读取 `$trellis-start`。按上方的
<sub-agent-notice> 指示直接执行父消息。
</trellis-bootstrap>"""


# ---------------------------------------------------------------------------
# CWD 健壮的 Trellis 根目录发现（修复本 hook 的 hook 路径健壮性）
# ---------------------------------------------------------------------------

def find_trellis_root(start: Path) -> Optional[Path]:
    """从 start 向上遍历，找到包含 .trellis/ 的目录。

    处理 CWD 偏移：子目录启动、monorepo 软件包等场景。
    未找到 .trellis/ 则返回 None（静默无操作）。
    """
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / ".trellis").is_dir():
            return cur
        cur = cur.parent
    return None


# ---------------------------------------------------------------------------
# 活动任务发现
# ---------------------------------------------------------------------------

def _detect_platform(input_data: dict) -> str | None:
    if isinstance(input_data.get("cursor_version"), str):
        return "cursor"
    env_map = {
        "CLAUDE_PROJECT_DIR": "claude",
        "CURSOR_PROJECT_DIR": "cursor",
        "CODEBUDDY_PROJECT_DIR": "codebuddy",
        "FACTORY_PROJECT_DIR": "droid",
        "GEMINI_PROJECT_DIR": "gemini",
        "QODER_PROJECT_DIR": "qoder",
        "KIRO_PROJECT_DIR": "kiro",
        "COPILOT_PROJECT_DIR": "copilot",
    }
    for env_name, platform in env_map.items():
        if os.environ.get(env_name):
            return platform
    script_parts = set(Path(sys.argv[0]).parts)
    if ".claude" in script_parts:
        return "claude"
    if ".cursor" in script_parts:
        return "cursor"
    if ".codex" in script_parts:
        return "codex"
    if ".gemini" in script_parts:
        return "gemini"
    if ".qoder" in script_parts:
        return "qoder"
    if ".codebuddy" in script_parts:
        return "codebuddy"
    if ".factory" in script_parts:
        return "droid"
    if ".kiro" in script_parts:
        return "kiro"
    return None


def _resolve_active_task(root: Path, input_data: dict):
    scripts_dir = root / ".trellis" / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from common.active_task import resolve_active_task  # type: ignore[import-not-found]

    return resolve_active_task(root, input_data, platform=_detect_platform(input_data))


def get_active_task(root: Path, input_data: dict) -> Optional[tuple[str, str, str]]:
    """从当前活动任务返回 (task_id, status, source)。"""
    active = _resolve_active_task(root, input_data)
    if not active.task_path:
        return None

    task_dir = Path(active.task_path)
    if not task_dir.is_absolute():
        task_dir = root / task_dir
    if active.stale:
        return task_dir.name, f"stale_{active.source_type}", active.source

    task_json = task_dir / "task.json"
    if not task_json.is_file():
        return None
    try:
        data = json.loads(task_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    task_id = data.get("id") or task_dir.name
    status = data.get("status", "")
    if not isinstance(status, str) or not status:
        return None
    return task_id, status, active.source


# ---------------------------------------------------------------------------
# 面包屑加载：解析 workflow.md
# ---------------------------------------------------------------------------

# 支持包含字母、数字、下划线、连字符的 STATUS 值
# （所以 "in-review" / "blocked-by-team" 可以和 "in_progress" 一起使用）。
_TAG_RE = re.compile(
    r"\[workflow-state:([A-Za-z0-9_-]+)\]\s*\n(.*?)\n\s*\[/workflow-state:\1\]",
    re.DOTALL,
)

def load_breadcrumbs(root: Path) -> dict[str, str]:
    """解析 workflow.md 中的 [workflow-state:STATUS] 块。

    返回值 {status: body_text}。workflow.md 是唯一真相来源 —
    本脚本中没有回退字典。缺失标签（或 workflow.md 缺失/不可读）
    会在 build_breadcrumb 中回退为通用行，让用户看到损坏的状态并修复
    workflow.md，而不是让 hook 静默掩盖问题。
    """
    workflow = root / ".trellis" / "workflow.md"
    if not workflow.is_file():
        return {}
    try:
        content = workflow.read_text(encoding="utf-8")
    except OSError:
        return {}

    result: dict[str, str] = {}
    for match in _TAG_RE.finditer(content):
        status = match.group(1)
        body = match.group(2).strip()
        if body:
            result[status] = body
    return result


def _read_trellis_config(root: Path) -> dict:
    """通过内置的 trellis_config 助手加载 .trellis/config.yaml。

    助手位于 .trellis/scripts/common；本 hook 位于 scripts 树之外，
    因此我们在导入前扩展 sys.path。
    """
    scripts_dir = root / ".trellis" / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from common.trellis_config import read_trellis_config  # type: ignore[import-not-found]
    except Exception:
        return {}
    try:
        return read_trellis_config(root)
    except Exception:
        return {}


def _codex_mode_banner(config: dict) -> str:
    """为 additionalContext 负载生成 `<codex-mode>` 横幅。

    从 .trellis/config.yaml 读取 `codex.dispatch_mode`；缺失或无效时
    默认值为 `inline`，因为 Codex 子智能体以 ``fork_turns="none"`` 隔离
    运行，无法继承父会话的任务上下文。横幅使 Codex AI 每轮都能明确
    当前模式，与按状态划分的 workflow-state 正文互补。
    模式告诉 AI 遵循哪种调度协议；workflow-state 告诉 AI 处于哪一步。
    """
    mode = "inline"
    if isinstance(config, dict):
        codex_cfg = config.get("codex")
        if isinstance(codex_cfg, dict):
            cfg_mode = codex_cfg.get("dispatch_mode")
            if cfg_mode in ("inline", "sub-agent"):
                mode = cfg_mode
    return f"<codex-mode>{mode}</codex-mode>"


def resolve_breadcrumb_key(
    status: str, platform: str | None, config: dict
) -> str:
    """基于 Codex dispatch_mode 选择面包屑标签键。

    Codex 默认使用 ``inline``，因为子智能体以 ``fork_turns="none"`` 隔离
    运行，无法继承父会话的任务上下文。用户可以在 ``.trellis/config.yaml``
    中通过 ``codex.dispatch_mode: sub-agent`` 选择使用并行的
    ``<status>-inline`` 标签 → ``<status>`` 翻转。无效或缺失的值回退到 inline。

    非 Codex 平台直接返回原始 status。
    """
    if platform == "codex":
        mode = "inline"
        if isinstance(config, dict):
            codex_cfg = config.get("codex")
            if isinstance(codex_cfg, dict):
                cfg_mode = codex_cfg.get("dispatch_mode")
                if cfg_mode in ("inline", "sub-agent"):
                    mode = cfg_mode
        return f"{status}-inline" if mode == "inline" else status
    return status


def build_breadcrumb(
    task_id: Optional[str],
    status: str,
    templates: dict[str, str],
    source: str | None = None,
    breadcrumb_key: str | None = None,
) -> str:
    """构建 <workflow-state>...</workflow-state> 块。

    - 已知状态（workflow.md 中存在标签）→ 详细模板正文
    - 未知状态（无标签，或 workflow.md 缺失）→ 通用
      "请参阅 workflow.md 了解当前步骤。" 行
    - `no_task` 伪状态（task_id 为 None）→ 标题省略任务信息
    """
    lookup_key = breadcrumb_key or status
    body = templates.get(lookup_key)
    if body is None and lookup_key != status:
        body = templates.get(status)
    if body is None:
        body = "请参阅 workflow.md 了解当前步骤。"
    header = f"状态: {status}" if task_id is None else f"任务: {task_id} ({status})"
    if source:
        header = f"{header}\n来源: {source}"
    return f"<workflow-state>\n{header}\n{body}\n</workflow-state>"


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main() -> int:
    if os.environ.get("TRELLIS_HOOKS") == "0" or os.environ.get("TRELLIS_DISABLE_HOOKS") == "1":
        return 0

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        data = {}

    cwd_str = data.get("cwd") or os.getcwd()
    cwd = Path(cwd_str)

    root = find_trellis_root(cwd)
    if root is None:
        return 0  # 非 Trellis 项目

    templates = load_breadcrumbs(root)
    platform = _detect_platform(data)
    config = _read_trellis_config(root)
    task = get_active_task(root, data)
    if task is None:
        # 无活动任务 — 仍然输出面包屑，提示 AI 在用户描述实际工作时
        # 使用 trellis-brainstorm + task.py create。
        no_task_key = resolve_breadcrumb_key("no_task", platform, config)
        breadcrumb = build_breadcrumb(
            None, "no_task", templates, breadcrumb_key=no_task_key
        )
    else:
        task_id, status, source = task
        status_key = resolve_breadcrumb_key(status, platform, config)
        breadcrumb = build_breadcrumb(
            task_id, status, templates, source, breadcrumb_key=status_key
        )
    if platform == "codex":
        parts: list[str] = [CODEX_SUB_AGENT_NOTICE]
        if task is None:
            parts.append(CODEX_NO_TASK_BOOTSTRAP_NOTICE)
        parts.append(_codex_mode_banner(config))
        parts.append(breadcrumb)
        breadcrumb = "\n\n".join(parts)

    # Gemini CLI 0.40.x 拒绝 "UserPromptSubmit" — 其每轮事件命名为
    # "BeforeAgent"。其他平台（Claude/Cursor/Qoder/CodeBuddy/
    # Droid/Codex/Copilot）接受原始的 Claude 风格命名。
    hook_event_name = (
        "BeforeAgent" if platform == "gemini" else "UserPromptSubmit"
    )

    output = {
        "hookSpecificOutput": {
            "hookEventName": hook_event_name,
            "additionalContext": breadcrumb,
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
