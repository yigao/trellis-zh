#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话启动钩子（Session Start Hook）- 注入结构化上下文
"""
from __future__ import annotations

# 重要：在最开始就抑制所有警告
import warnings
warnings.filterwarnings("ignore")

import json
import os
import re
import shlex
import subprocess
import sys
from io import StringIO
from pathlib import Path


def _normalize_windows_shell_path(path_str: str) -> str:
    """将 Unix 风格 shell 路径规范化为实际 Windows 路径。

    在 Windows 上，Git Bash / MSYS2 / Cygwin 等 shell 可能报告类似
    `/d/Users/...` 或 `/cygdrive/d/Users/...` 的路径。`Path.resolve()` 会
    将其误解析为驱动器 D: 上的 `D:/d/Users...`（或类似），从而破坏仓库根目录
    检测。

    此函数有意保持保守：仅重写明确表示驱动器字母挂载的模式。
    """
    if not isinstance(path_str, str) or not path_str:
        return path_str

    # 仅与 Windows 相关；其他平台保持不变。
    if not sys.platform.startswith("win"):
        return path_str

    p = path_str.strip()

    # 已经是 Windows 驱动器路径（C:\... 或 C:/...）
    if re.match(r"^[A-Za-z]:[\/]", p):
        return p

    # MSYS/Git-Bash 风格：/c/Users/... 或 /d/Work/...
    m = re.match(r"^/([A-Za-z])/(.*)", p)
    if m:
        drive, rest = m.group(1).upper(), m.group(2)
        rest = rest.replace('/', '\\')
        return f"{drive}:\\{rest}"

    # Cygwin 风格：/cygdrive/c/Users/...
    m = re.match(r"^/cygdrive/([A-Za-z])/(.*)", p)
    if m:
        drive, rest = m.group(1).upper(), m.group(2)
        rest = rest.replace('/', '\\')
        return f"{drive}:\\{rest}"

    # WSL 挂载的驱动器（有时泄露到环境变量中）：/mnt/c/Users/...
    m = re.match(r"^/mnt/([A-Za-z])/(.*)", p)
    if m:
        drive, rest = m.group(1).upper(), m.group(2)
        rest = rest.replace('/', '\\')
        return f"{drive}:\\{rest}"

    return path_str


FIRST_REPLY_NOTICE = """<first-reply-notice>
在本会话的首次可见助手回复中，请以恰好一句简短的中文开头：
Trellis SessionStart 已注入：workflow、当前任务状态、开发者身份、git 状态、active tasks、spec 索引已加载。
然后直接继续处理用户请求。此通知仅一次生效：同会话中首次助手回复后不再重复。
</first-reply-notice>"""

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



def _has_curated_jsonl_entry(jsonl_path: Path) -> bool:
    """当 JSONL 至少有一行包含 ``file`` 字段时返回 True。

    新创建的种子 JSONL 仅包含一行 ``{"_example": ...}``（无 ``file``
    键）— 这不算"就绪"。就绪要求至少有一个已整理的条目。
    与 hook-inject 和基于拉取的子智能体上下文加载器使用的约定一致。
    """
    try:
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("file"):
                return True
    except (OSError, UnicodeDecodeError):
        return False
    return False


def should_skip_injection() -> bool:
    """检查是否有任何平台的非交互式标志被设置，或 Trellis hooks
    是否通过 TRELLIS_HOOKS=0 / TRELLIS_DISABLE_HOOKS=1 被显式禁用。
    """
    if os.environ.get("TRELLIS_HOOKS") == "0":
        return True
    if os.environ.get("TRELLIS_DISABLE_HOOKS") == "1":
        return True
    non_interactive_vars = [
        "CLAUDE_NON_INTERACTIVE",
        "QODER_NON_INTERACTIVE",
        "CODEBUDDY_NON_INTERACTIVE",
        "FACTORY_NON_INTERACTIVE",
        "CURSOR_NON_INTERACTIVE",
        "GEMINI_NON_INTERACTIVE",
        "KIRO_NON_INTERACTIVE",
        "COPILOT_NON_INTERACTIVE",
    ]
    return any(os.environ.get(var) == "1" for var in non_interactive_vars)


def read_file(path: Path, fallback: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError):
        return fallback


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


def _resolve_context_key(trellis_dir: Path, input_data: dict) -> str | None:
    scripts_dir = trellis_dir / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from common.active_task import resolve_context_key  # type: ignore[import-not-found]

    return resolve_context_key(input_data, platform=_detect_platform(input_data))


def _persist_context_key_for_bash(context_key: str | None) -> None:
    """将 Trellis 会话身份暴露给后续的 Claude Code Bash 命令。

    Claude Code 的 SessionStart hook 可以向 CLAUDE_ENV_FILE 追加导出语句；
    这些环境变量随后在同一对话中的 Bash 工具中可用。没有这个桥接，
    `task.py start` 在 SessionStart 期间有 hook stdin，但在 AI 稍后以
    普通 shell 命令运行它时却没有会话身份。
    """
    if not context_key:
        return
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if not env_file:
        return
    try:
        with open(env_file, "a", encoding="utf-8") as handle:
            handle.write(f"export TRELLIS_CONTEXT_ID={shlex.quote(context_key)}\n")
    except OSError:
        pass


def _resolve_active_task(trellis_dir: Path, input_data: dict):
    scripts_dir = trellis_dir / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from common.active_task import resolve_active_task  # type: ignore[import-not-found]

    return resolve_active_task(
        trellis_dir.parent,
        input_data,
        platform=_detect_platform(input_data),
    )


def run_script(script_path: Path, context_key: str | None = None) -> str:
    try:
        if script_path.suffix == ".py":
            # 添加 PYTHONIOENCODING 强制子进程使用 UTF-8
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            if context_key:
                env["TRELLIS_CONTEXT_ID"] = context_key
            cmd = [sys.executable, "-W", "ignore", str(script_path)]
        else:
            env = os.environ.copy()
            if context_key:
                env["TRELLIS_CONTEXT_ID"] = context_key
            cmd = [str(script_path)]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            cwd=script_path.parent.parent.parent,
            env=env,
        )
        return result.stdout if result.returncode == 0 else "无可用上下文"
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        return "无可用上下文"


def _normalize_task_ref(task_ref: str) -> str:
    normalized = task_ref.strip()
    if not normalized:
        return ""

    path_obj = Path(normalized)
    if path_obj.is_absolute():
        return str(path_obj)

    normalized = normalized.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]

    if normalized.startswith("tasks/"):
        return f".trellis/{normalized}"

    return normalized


def _resolve_task_dir(trellis_dir: Path, task_ref: str) -> Path:
    normalized = _normalize_task_ref(task_ref)
    path_obj = Path(normalized)
    if path_obj.is_absolute():
        return path_obj
    if normalized.startswith(".trellis/"):
        return trellis_dir.parent / path_obj
    return trellis_dir / "tasks" / path_obj


def _get_task_status(trellis_dir: Path, input_data: dict) -> str:
    """检查当前任务状态并返回结构化的状态字符串，包含明确的下一步操作。

    返回一个包含三个字段的块：
    - Status: 当前状态
    - Task: 任务标识符（如适用）
    - Next-Action: AI 应调用的显式 skill/command/tool 操作
    """
    active = _resolve_active_task(trellis_dir, input_data)

    # 情况 1：没有活动任务 — 等待用户描述意图
    if not active.task_path:
        return (
            "Status: NO ACTIVE TASK\n"
            f"Source: {active.source}\n"
            "Next-Action: 用户描述意图后，加载 skill `trellis-brainstorm` "
            "明确需求，并通过 `py -3 ./.trellis/scripts/task.py create` 创建任务。\n"
            "研究提醒：对于研究密集型任务（工具对比、阅读外部文档、"
            "跨平台调研），通过 Task 工具派生 `trellis-research` 子智能体 — "
            "它们将发现持久化到 `{TASK_DIR}/research/*.md`，保持主上下文干净。"
            "不要在主线对话中执行 10 次以上的 WebFetch/WebSearch。\n"
            "用户覆盖（每轮逃生舱）：如果用户的首条消息明确表示跳过工作流"
            "（\"跳过 trellis\" / \"别走流程\" / \"小修一下\" / \"直接改\" / "
            "\"skip trellis\" / \"no task\" / \"just do it\"），本轮遵从 — "
            "简要确认后直接处理，不创建任务。仅本轮有效。"
        )

    # 情况 2：过期指针 — 任务目录已被删除
    task_ref = active.task_path
    task_dir = _resolve_task_dir(trellis_dir, task_ref)
    if active.stale or not task_dir.is_dir():
        return (
            f"Status: STALE POINTER\nTask: {task_ref}\n"
            f"Source: {active.source}\n"
            f"Next-Action: 运行 `py -3 ./.trellis/scripts/task.py finish` 清除过期指针，"
            "然后询问用户接下来要做什么。"
        )

    # 读取 task.json
    task_json_path = task_dir / "task.json"
    task_data = {}
    if task_json_path.is_file():
        try:
            task_data = json.loads(task_json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, PermissionError):
            pass

    task_title = task_data.get("title", task_ref)
    task_status = task_data.get("status", "unknown")

    # 情况 3：任务已完成 — 需要归档
    if task_status == "completed":
        return (
            f"Status: COMPLETED\nTask: {task_title}\n"
            f"Source: {active.source}\n"
            f"Next-Action: 加载 skill `trellis-update-spec` 捕获经验教训，"
            f"然后通过 `py -3 ./.trellis/scripts/task.py archive {task_dir.name}` 归档。"
        )

    has_prd = (task_dir / "prd.md").is_file()

    # 情况 4：没有 PRD — 仍处于规划（Plan）阶段
    if not has_prd:
        return (
            f"Status: PLANNING\nTask: {task_title}\n"
            f"Source: {active.source}\n"
            "Next-Action: 加载 skill `trellis-brainstorm` 与用户明确需求，"
            "并在任务目录中生成 prd.md。\n"
            "研究提醒：当任务需要外部研究时（工具对比、文档、"
            "约定调研），派生 `trellis-research` 子智能体 — 不要在主线会话中"
            "内联调用 WebFetch/WebSearch。发现结果写入 `{task_dir}/research/*.md`；PRD 仅链接到它们。"
        )

    # 情况 4b：PRD 存在但 implement.jsonl 只有种子数据（无整理条目）— 阶段 1.3 门槛
    implement_jsonl = task_dir / "implement.jsonl"
    if implement_jsonl.is_file() and not _has_curated_jsonl_entry(implement_jsonl):
        return (
            f"Status: PLANNING (Phase 1.3)\nTask: {task_title}\n"
            f"Source: {active.source}\n"
            "Next-Action: 整理 `implement.jsonl` 和 `check.jsonl`，填入阶段 2 子智能体"
            "需要的 spec 和研究文件。仅限 spec 路径（`.trellis/spec/**/*.md`）和研究"
            "文件（`{TASK_DIR}/research/*.md`）— 不包含代码路径。运行"
            "`py -3 ./.trellis/scripts/get_context.py --mode packages` 列出可用 spec，"
            "然后编辑 jsonl 文件或使用 `py -3 ./.trellis/scripts/task.py add-context`。"
            "详见 `.trellis/workflow.md` 阶段 1.3。"
        )

    # 情况 5：PRD + 已整理的 jsonl（或无 jsonl 的无智能体平台）— 进入执行（Execute）阶段
    return (
        f"Status: READY\nTask: {task_title}\n"
        f"Source: {active.source}\n"
        "Next required action: 按阶段 2.1 调度 `trellis-implement`。"
        "对于支持智能体的平台，默认不在主线会话中编辑代码。"
        "实现完成后，按阶段 2.2 调度 `trellis-check`，再报告完成。\n"
        "子智能体列表：`trellis-implement`（编写代码）、`trellis-check`（验证 + 自修复）、"
        "`trellis-research`（将发现持久化到 `research/*.md` — 当需要多次内联"
        "WebFetch/WebSearch 时使用）。\n"
        "子智能体自我豁免：如果你作为 `trellis-implement` 或"
        "`trellis-check` 子智能体（你的角色 / 智能体名称反映了这一点）正在阅读此内容，"
        "则此调度指令对你不适用 — 你已经是已调度的子智能体。"
        "直接实现/检查，不要再次派生同类型的子智能体。\n"
        "用户覆盖（每轮逃生舱）：如果用户当前消息明确要求主线会话直接处理"
        "（\"你直接改\" / \"别派 sub-agent\" / \"main session 写就行\" / "
        "\"do it inline\" / \"不用 sub-agent\"），本轮遵从并直接编辑代码。"
        "仅本轮有效；不要编造用户没有说过的覆盖指令。"
    )


def _load_trellis_config(trellis_dir: Path, input_data: dict) -> tuple:
    """加载 Trellis 配置用于会话启动决策。

    返回值：
        (is_mono, packages_dict, spec_scope, task_pkg, default_pkg)
    """
    scripts_dir = trellis_dir / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    try:
        from common.config import get_default_package, get_packages, get_spec_scope, is_monorepo  # type: ignore[import-not-found]
        from common.paths import get_current_task  # type: ignore[import-not-found]

        repo_root = trellis_dir.parent
        is_mono = is_monorepo(repo_root)
        packages = get_packages(repo_root) or {}
        scope = get_spec_scope(repo_root)

        # 获取活动任务的 package
        task_pkg = None
        current = get_current_task(
            repo_root,
            input_data,
            platform=_detect_platform(input_data),
        )
        if current:
            task_json = repo_root / current / "task.json"
            if task_json.is_file():
                try:
                    data = json.loads(task_json.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        tp = data.get("package")
                        if isinstance(tp, str) and tp:
                            task_pkg = tp
                except (json.JSONDecodeError, OSError):
                    pass

        default_pkg = get_default_package(repo_root)
        return is_mono, packages, scope, task_pkg, default_pkg
    except Exception:
        return False, {}, None, None, None


def _check_legacy_spec(trellis_dir: Path, is_mono: bool, packages: dict) -> str | None:
    """检查 monorepo 中是否存在旧版 spec 目录结构。

    如果检测到旧版结构则返回警告消息，否则返回 None。
    """
    if not is_mono or not packages:
        return None

    spec_dir = trellis_dir / "spec"
    if not spec_dir.is_dir():
        return None

    # 检查旧版扁平 spec 目录（spec/backend/、spec/frontend/ 含 index.md）
    has_legacy = False
    for legacy_name in ("backend", "frontend"):
        legacy_dir = spec_dir / legacy_name
        if legacy_dir.is_dir() and (legacy_dir / "index.md").is_file():
            has_legacy = True
            break

    if not has_legacy:
        return None

    # 检查哪些 package 缺少 spec/<pkg>/ 目录
    missing = [
        name for name in sorted(packages.keys())
        if not (spec_dir / name).is_dir()
    ]

    if not missing:
        return None  # 所有 package 都有 spec 目录

    if len(missing) == len(packages):
        return (
            f"[!] 检测到旧版 spec 结构：找到 `spec/backend/` 或 `spec/frontend/` "
            f"但没有以 package 为作用域的 `spec/<package>/` 目录。\n"
            f"Monorepo packages: {', '.join(sorted(packages.keys()))}\n"
            f"请重组：`spec/backend/` -> `spec/<package>/backend/`"
        )
    return (
        f"[!] 检测到部分 spec 迁移：packages {', '.join(missing)} "
        f"仍然缺少 `spec/<pkg>/` 目录。\n"
        f"请完成所有 package 的迁移。"
    )


def _resolve_spec_scope(
    is_mono: bool,
    packages: dict,
    scope,
    task_pkg: str | None,
    default_pkg: str | None,
) -> set | None:
    """解析哪些 package 的 spec 应被注入。

    返回值：
        要包含的 package 名称集合，或 None 表示全量扫描。
    """
    if not is_mono or not packages:
        return None  # 单仓库：全量扫描

    if scope is None:
        return None  # 未配置作用域：全量扫描

    if isinstance(scope, str) and scope == "active_task":
        if task_pkg and task_pkg in packages:
            return {task_pkg}
        if default_pkg and default_pkg in packages:
            return {default_pkg}
        return None  # 回退到全量扫描

    if isinstance(scope, list):
        valid = set()
        for entry in scope:
            if entry in packages:
                valid.add(entry)
            else:
                print(
                    f"警告: spec_scope 包含未知 package: {entry}，已忽略",
                    file=sys.stderr,
                )

        if valid:
            # 如果活动任务不在作用域内则警告
            if task_pkg and task_pkg not in valid:
                print(
                    f"警告: 活动任务 package '{task_pkg}' 不在配置的 spec_scope 范围内",
                    file=sys.stderr,
                )
            return valid

        # 所有条目无效：回退链
        print(
            "警告: 所有 spec_scope 条目无效，回退到 task/default/full",
            file=sys.stderr,
        )
        if task_pkg and task_pkg in packages:
            return {task_pkg}
        if default_pkg and default_pkg in packages:
            return {default_pkg}
        return None  # 全量扫描

    return None  # 未知作用域类型：全量扫描


def _extract_range(content: str, start_header: str, end_header: str) -> str:
    """从 `## start_header` 开始提取行，直到（但不包括）`## end_header`。

    两个参数都是不含 `## ` 前缀的完整标题行（例如 "Phase Index"）。
    如果找不到起始标题则返回空字符串。
    结束标题缺失 → 提取到文件末尾。
    """
    lines = content.splitlines()
    start: int | None = None
    end: int = len(lines)
    start_match = f"## {start_header}"
    end_match = f"## {end_header}"
    for i, line in enumerate(lines):
        stripped = line.strip()
        if start is None and stripped == start_match:
            start = i
            continue
        if start is not None and stripped == end_match:
            end = i
            break
    if start is None:
        return ""
    return "\n".join(lines[start:end]).rstrip()


_BREADCRUMB_TAG_RE = re.compile(
    r"\[workflow-state:([A-Za-z0-9_-]+)\]\s*\n.*?\n\s*\[/workflow-state:\1\]",
    re.DOTALL,
)


def _strip_breadcrumb_tag_blocks(content: str) -> str:
    """移除 `[workflow-state:STATUS]...[/workflow-state:STATUS]` 块。

    标签块位于 `## Phase Index` 内部（自 v0.5.0-rc.0 起，它们与阶段摘要
    放在一起），由 UserPromptSubmit hook（`inject-workflow-state.py`）消费。
    会话启动负载已覆盖完整的步骤正文，所以此处再内联面包屑只会重复上下文。
    """
    return _BREADCRUMB_TAG_RE.sub("", content)


def _build_workflow_overview(workflow_path: Path) -> str:
    """为会话注入工作流指南。

    内容：
      1. 章节索引（所有 `## ` 标题 — 导航）
      2. Phase Index 章节（规则、skill 路由表、反合理化表）
      3. 阶段 1/2/3 步骤级详情（每个步骤的实际操作指南）

    元章节（Core Principles / Trellis System / Customizing
    Trellis）不会被注入 — Core Principles 是简短散文，AI 可以按需
    Read；Trellis System 列出了已在步骤正文中重复的参考命令；
    Customizing Trellis 是给 fork 用户看的。工作流状态面包屑标签块
    （自 v0.5.0-rc.0 起位于 Phase Index 内部）从提取范围中剥离 —
    它们由 UserPromptSubmit hook 消费，而非会话启动前言。

    总预算：Phase Index ~2 KB + 阶段 1/2/3 ~7 KB = ~9 KB。
    """
    content = read_file(workflow_path)
    if not content:
        return "未找到 workflow.md"

    out_lines = [
        "# 开发工作流 — 章节索引",
        "完整指南: .trellis/workflow.md  （按需读取）",
        "",
        "## 目录",
    ]
    for line in content.splitlines():
        if line.startswith("## "):
            out_lines.append(line)
    out_lines += ["", "---", ""]

    # 提取 Phase Index 到阶段 3 末尾（在 "Customizing Trellis（for forks）"
    # 之前 — v0.5.0-rc.0 中新增的 fork 用户文档页脚）。
    # 由于章节按 Phase Index → Phase 1 → Phase 2 → Phase 3 →
    # Customizing Trellis 的顺序出现，一次范围抓取即可捕获全部四个。
    # 嵌入 Phase Index 内部的面包屑标签块被剥离，以免与每轮
    # UserPromptSubmit 注入重复。
    phases = _extract_range(
        content, "Phase Index", "Customizing Trellis (for forks)"
    )
    if phases:
        out_lines.append(_strip_breadcrumb_tag_blocks(phases).rstrip())

    return "\n".join(out_lines).rstrip()


def main():
    if should_skip_injection():
        sys.exit(0)

    try:
        hook_input = json.loads(sys.stdin.read())
        if not isinstance(hook_input, dict):
            hook_input = {}
    except (json.JSONDecodeError, ValueError):
        hook_input = {}

    # 尝试平台特定的环境变量、hook cwd，回退到当前工作目录
    project_dir_env_vars = [
        "CLAUDE_PROJECT_DIR",
        "QODER_PROJECT_DIR",
        "CODEBUDDY_PROJECT_DIR",
        "FACTORY_PROJECT_DIR",
        "CURSOR_PROJECT_DIR",
        "GEMINI_PROJECT_DIR",
        "KIRO_PROJECT_DIR",
        "COPILOT_PROJECT_DIR",
    ]
    project_dir = None
    for var in project_dir_env_vars:
        val = os.environ.get(var)
        if val:
            project_dir = Path(_normalize_windows_shell_path(val)).resolve()
            break
    if project_dir is None:
        project_dir = Path(_normalize_windows_shell_path(hook_input.get("cwd", "."))).resolve()

    trellis_dir = project_dir / ".trellis"
    context_key = _resolve_context_key(trellis_dir, hook_input)
    _persist_context_key_for_bash(context_key)

    # 加载配置用于作用域过滤和旧版检测
    is_mono, packages, scope_config, task_pkg, default_pkg = _load_trellis_config(
        trellis_dir,
        hook_input,
    )
    allowed_pkgs = _resolve_spec_scope(is_mono, packages, scope_config, task_pkg, default_pkg)

    output = StringIO()

    output.write("""<session-context>
你正在 Trellis 管理的项目中启动一个新会话。
请仔细阅读并遵循以下所有说明。
</session-context>

""")
    output.write(FIRST_REPLY_NOTICE)
    output.write("\n\n")

    # 旧版迁移警告
    legacy_warning = _check_legacy_spec(trellis_dir, is_mono, packages)
    if legacy_warning:
        output.write(f"<migration-warning>\n{legacy_warning}\n</migration-warning>\n\n")

    output.write("<current-state>\n")
    context_script = trellis_dir / "scripts" / "get_context.py"
    output.write(run_script(context_script, context_key))
    output.write("\n</current-state>\n\n")

    output.write("<workflow>\n")
    output.write(_build_workflow_overview(trellis_dir / "workflow.md"))
    output.write("\n</workflow>\n\n")

    output.write("<guidelines>\n")
    output.write(
        "项目 spec 索引按路径列在下方。每个索引包含一个 "
        "**开发前检查清单（Pre-Development Checklist）**，列出编写代码前需要阅读的"
        "具体指南文件。\n\n"
        "- 如果你要派生 implement/check 子智能体，上下文会通过子智能体"
        "的 `{task}/implement.jsonl` / `check.jsonl` 注入或加载。"
        "你不需要自己读取这些索引。\n"
        "- 对于支持智能体的平台，默认调度 "
        "`trellis-implement` 和 `trellis-check`（让 JSONL 上下文由子智能体加载），"
        "而不是在主线会话中编辑代码。"
        "仅在用户当前消息明确退出时才遵从每轮用户覆盖"
        "（覆盖短语见下方 <task-status>）。\n"
        "- 子智能体自我豁免：如果你作为 `trellis-implement` "
        "或 `trellis-check` 子智能体正在阅读此内容，上方的「调度 trellis-implement / trellis-check」"
        "规则对你不适用 — 你已经是已调度的子智能体。"
        "不要再次派生同类型的子智能体；直接实现/检查。\n\n"
    )

    # guides/ 是跨 package 的思考指南 — 始终内联（内容少，广泛适用）
    guides_index = trellis_dir / "spec" / "guides" / "index.md"
    if guides_index.is_file():
        output.write("## guides（已内联 — 跨 package 思考指南）\n")
        output.write(read_file(guides_index))
        output.write("\n\n")

    # 其他 spec 索引 — 仅路径（主智能体按需读取；
    # 子智能体通过 jsonl 注入获取其特定 spec）
    paths: list[str] = []
    spec_dir = trellis_dir / "spec"
    if spec_dir.is_dir():
        for sub in sorted(spec_dir.iterdir()):
            if not sub.is_dir() or sub.name.startswith("."):
                continue
            if sub.name == "guides":
                continue  # 上面已内联

            index_file = sub / "index.md"
            if index_file.is_file():
                # 扁平 spec 目录（单仓库层级，如 spec/backend/）
                paths.append(f".trellis/spec/{sub.name}/index.md")
            else:
                # 嵌套 package 目录（monorepo: spec/<pkg>/<layer>/index.md）
                # 应用作用域过滤
                if allowed_pkgs is not None and sub.name not in allowed_pkgs:
                    continue
                for nested in sorted(sub.iterdir()):
                    if not nested.is_dir():
                        continue
                    nested_index = nested / "index.md"
                    if nested_index.is_file():
                        paths.append(
                            f".trellis/spec/{sub.name}/{nested.name}/index.md"
                        )

    if paths:
        output.write("## 可用的 spec 索引（按需读取）\n")
        for p in paths:
            output.write(f"- {p}\n")
        output.write("\n")

    output.write(
        "发现更多："
        "`py -3 ./.trellis/scripts/get_context.py --mode packages`\n"
    )
    output.write("</guidelines>\n\n")

    # 检查任务状态并注入结构化标签
    task_status = _get_task_status(trellis_dir, hook_input)
    output.write(f"<task-status>\n{task_status}\n</task-status>\n\n")

    output.write("""<ready>
上下文已加载。工作流索引、项目状态和指南已在上方注入 — 不要重新读取。
当用户发送首条消息时，遵循 <task-status> 和工作流指南。
如果任务处于 READY 状态，无需询问是否继续，直接执行其 Next required action。
</ready>""")

    context_text = output.getvalue()
    result = {
        # Claude Code / Qoder / CodeBuddy / Droid / Gemini / Copilot 格式
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context_text,
        },
        # Cursor sessionStart 格式（顶层 snake_case，遵循 Cursor 文档）
        "additional_context": context_text,
    }

    # 输出 JSON — stdout 已配置为 UTF-8
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
