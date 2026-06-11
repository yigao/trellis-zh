"""
多平台支持的 CLI 适配器。

抽象 Claude Code、OpenCode、Cursor、iFlow、Codex、Kilo、Kiro Code、Gemini CLI、Antigravity、Windsurf、Qoder、CodeBuddy、GitHub Copilot、Factory Droid 和 Pi Agent 接口之间的差异。

支持的平台:
- claude: Claude Code（默认）
- opencode: OpenCode
- cursor: Cursor IDE
- iflow: iFlow CLI
- codex: Codex CLI（基于技能/skills）
- kilo: Kilo CLI
- kiro: Kiro Code（基于技能/skills）
- gemini: Gemini CLI
- antigravity: Antigravity（基于工作流/workflow）
- windsurf: Windsurf（基于工作流/workflow）
- qoder: Qoder
- codebuddy: CodeBuddy
- copilot: GitHub Copilot（VS Code）
- droid: Factory Droid（基于命令/commands）
- pi: Pi Agent（扩展支持）

用法:
    from common.cli_adapter import CLIAdapter

    adapter = CLIAdapter("opencode")
    cmd = adapter.build_run_command(
        agent="dispatch",
        session_id="abc123",
        prompt="启动流水线"
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Literal

Platform = Literal[
    "claude",
    "opencode",
    "cursor",
    "iflow",
    "codex",
    "kilo",
    "kiro",
    "gemini",
    "antigravity",
    "windsurf",
    "qoder",
    "codebuddy",
    "copilot",
    "droid",
    "pi",
]


@dataclass
class CLIAdapter:
    """不同 AI 编程 CLI 工具的适配器。"""

    platform: Platform

    # =========================================================================
    # Agent 名称映射
    # =========================================================================

    # OpenCode 有内置 agent，无法覆盖
    # 参见: https://github.com/sst/opencode/issues/4271
    # 注意: 类级别常量，不是数据类字段
    _AGENT_NAME_MAP: ClassVar[dict[Platform, dict[str, str]]] = {
        "claude": {},  # 无需映射
        "opencode": {
            "plan": "trellis-plan",  # 'plan' 在 OpenCode 中是内置的
        },
    }

    def get_agent_name(self, agent: str) -> str:
        """获取平台特定的 agent 名称。

        参数:
            agent: 原始 agent 名称（例如 'plan'、'dispatch'）

        返回:
            平台特定的 agent 名称（例如 OpenCode 的 'trellis-plan'）
        """
        mapping = self._AGENT_NAME_MAP.get(self.platform, {})
        return mapping.get(agent, agent)

    # =========================================================================
    # Agent 路径
    # =========================================================================

    @property
    def config_dir_name(self) -> str:
        """获取平台特定的配置目录名。

        返回:
            目录名（'.claude'、'.opencode'、'.cursor'、'.iflow'、'.codex'、'.kilocode'、'.kiro'、'.gemini'、'.agent'、'.windsurf'、'.qoder'、'.codebuddy'、'.github/copilot'、'.factory' 或 '.pi'）
        """
        if self.platform == "opencode":
            return ".opencode"
        elif self.platform == "cursor":
            return ".cursor"
        elif self.platform == "iflow":
            return ".iflow"
        elif self.platform == "codex":
            return ".codex"
        elif self.platform == "kilo":
            return ".kilocode"
        elif self.platform == "kiro":
            return ".kiro"
        elif self.platform == "gemini":
            return ".gemini"
        elif self.platform == "antigravity":
            return ".agent"
        elif self.platform == "windsurf":
            return ".windsurf"
        elif self.platform == "qoder":
            return ".qoder"
        elif self.platform == "codebuddy":
            return ".codebuddy"
        elif self.platform == "copilot":
            return ".github/copilot"
        elif self.platform == "droid":
            return ".factory"
        elif self.platform == "pi":
            return ".pi"
        else:
            return ".claude"

    def get_config_dir(self, project_root: Path) -> Path:
        """获取平台特定的配置目录。

        参数:
            project_root: 项目根目录

        返回:
            配置目录路径（.claude、.opencode、.cursor、.iflow、.codex、.kilocode、.kiro、.gemini、.agent、.windsurf、.qoder、.codebuddy、.github/copilot、.factory 或 .pi）
        """
        return project_root / self.config_dir_name

    def get_agent_path(self, agent: str, project_root: Path) -> Path:
        """获取 agent 定义文件的路径。

        参数:
            agent: Agent 名称（原始名称，映射前）
            project_root: 项目根目录

        返回:
            Agent 定义文件路径（大多数平台使用 .md，Codex 使用 .toml）
        """
        mapped_name = self.get_agent_name(agent)
        if self.platform == "codex":
            return self.get_config_dir(project_root) / "agents" / f"{mapped_name}.toml"
        return self.get_config_dir(project_root) / "agents" / f"{mapped_name}.md"

    def get_commands_path(self, project_root: Path, *parts: str) -> Path:
        """获取命令（commands）目录或特定命令文件的路径。

        参数:
            project_root: 项目根目录
            *parts: 额外的路径部分（例如 'trellis'、'finish-work.md'）

        返回:
            命令目录或文件路径

        注意:
            Cursor 使用前缀命名: .cursor/commands/trellis-<name>.md
            Antigravity 使用工作流目录: .agent/workflows/<name>.md
            Windsurf 使用工作流目录: .windsurf/workflows/trellis-<name>.md
            Copilot 使用提示（prompt）文件: .github/prompts/<name>.prompt.md
            Pi 使用提示模板: .pi/prompts/trellis-<name>.md
            Claude/OpenCode 使用子目录: .claude/commands/trellis/<name>.md
        """
        if self.platform == "pi":
            prompts_dir = self.get_config_dir(project_root) / "prompts"
            if not parts:
                return prompts_dir
            if len(parts) >= 2 and parts[0] == "trellis":
                filename = parts[-1]
                if filename.endswith(".md"):
                    filename = filename[:-3]
                return prompts_dir / f"trellis-{filename}.md"
            return prompts_dir / Path(*parts)

        if self.platform == "windsurf":
            workflow_dir = self.get_config_dir(project_root) / "workflows"
            if not parts:
                return workflow_dir
            if len(parts) >= 2 and parts[0] == "trellis":
                filename = parts[-1]
                return workflow_dir / f"trellis-{filename}"
            return workflow_dir / Path(*parts)

        if self.platform in ("antigravity", "kilo"):
            workflow_dir = self.get_config_dir(project_root) / "workflows"
            if not parts:
                return workflow_dir
            if len(parts) >= 2 and parts[0] == "trellis":
                filename = parts[-1]
                return workflow_dir / filename
            return workflow_dir / Path(*parts)

        if self.platform == "copilot":
            prompts_dir = project_root / ".github" / "prompts"
            if not parts:
                return prompts_dir
            if len(parts) >= 2 and parts[0] == "trellis":
                filename = parts[-1]
                if filename.endswith(".md"):
                    filename = filename[:-3]
                return prompts_dir / f"{filename}.prompt.md"
            return prompts_dir / Path(*parts)

        if not parts:
            return self.get_config_dir(project_root) / "commands"

        # Cursor 使用前缀命名而非子目录
        if self.platform == "cursor" and len(parts) >= 2 and parts[0] == "trellis":
            # 将 trellis/<name>.md 转换为 trellis-<name>.md
            filename = parts[-1]
            return (
                self.get_config_dir(project_root) / "commands" / f"trellis-{filename}"
            )

        return self.get_config_dir(project_root) / "commands" / Path(*parts)

    def get_trellis_command_path(self, name: str) -> str:
        """获取 trellis 命令文件的相对路径。

        参数:
            name: 命令名称，不带扩展名（例如 'finish-work'、'check'）

        返回:
            用于 JSONL 条目的相对路径字符串

        注意:
            Cursor: .cursor/commands/trellis-<name>.md
            Codex: .agents/skills/trellis-<name>/SKILL.md
            Kiro: .kiro/skills/trellis-<name>/SKILL.md
            Gemini: .gemini/commands/trellis/<name>.toml
            Antigravity: .agent/workflows/<name>.md
            Windsurf: .windsurf/workflows/trellis-<name>.md
            Pi: .pi/prompts/trellis-<name>.md
            其他: .{platform}/commands/trellis/<name>.md
        """
        if self.platform == "cursor":
            return f".cursor/commands/trellis-{name}.md"
        elif self.platform == "codex":
            # 0.5.0-beta.0 将所有 skill 目录重命名为添加 `trellis-` 前缀
            # （参见该版本的清单中的 60+ 重命名条目）。
            return f".agents/skills/trellis-{name}/SKILL.md"
        elif self.platform == "kiro":
            return f".kiro/skills/trellis-{name}/SKILL.md"
        elif self.platform == "gemini":
            return f".gemini/commands/trellis/{name}.toml"
        elif self.platform == "antigravity":
            return f".agent/workflows/{name}.md"
        elif self.platform == "windsurf":
            return f".windsurf/workflows/trellis-{name}.md"
        elif self.platform == "kilo":
            return f".kilocode/workflows/{name}.md"
        elif self.platform == "copilot":
            return f".github/prompts/{name}.prompt.md"
        elif self.platform == "droid":
            return f".factory/commands/trellis/{name}.md"
        elif self.platform == "pi":
            return f".pi/prompts/trellis-{name}.md"
        else:
            return f"{self.config_dir_name}/commands/trellis/{name}.md"

    # =========================================================================
    # 环境变量
    # =========================================================================

    def get_non_interactive_env(self) -> dict[str, str]:
        """获取非交互模式的环境变量。

        返回:
            要设置的环境变量 dict
        """
        if self.platform == "opencode":
            return {"OPENCODE_NON_INTERACTIVE": "1"}
        elif self.platform == "iflow":
            return {"IFLOW_NON_INTERACTIVE": "1"}
        elif self.platform == "codex":
            return {"CODEX_NON_INTERACTIVE": "1"}
        elif self.platform == "kiro":
            return {"KIRO_NON_INTERACTIVE": "1"}
        elif self.platform == "gemini":
            return {}  # Gemini CLI 没有非交互式环境变量
        elif self.platform == "antigravity":
            return {}
        elif self.platform == "windsurf":
            return {}
        elif self.platform == "qoder":
            return {}
        elif self.platform == "codebuddy":
            return {}
        elif self.platform == "copilot":
            return {}
        elif self.platform == "droid":
            return {}
        elif self.platform == "pi":
            return {}
        else:
            return {"CLAUDE_NON_INTERACTIVE": "1"}

    # =========================================================================
    # CLI 命令构建
    # =========================================================================

    def build_run_command(
        self,
        agent: str,
        prompt: str,
        session_id: str | None = None,
        skip_permissions: bool = True,
        verbose: bool = True,
        json_output: bool = True,
    ) -> list[str]:
        """构建运行 agent 的 CLI 命令。

        参数:
            agent: Agent 名称（需要时会映射）
            prompt: 发送给 agent 的提示
            session_id: 可选的会话（session）ID（仅 Claude Code 创建时支持）
            skip_permissions: 是否跳过权限提示
            verbose: 是否启用详细输出
            json_output: 是否使用 JSON 输出格式

        返回:
            命令参数列表
        """
        mapped_agent = self.get_agent_name(agent)

        if self.platform == "opencode":
            cmd = ["opencode", "run"]
            cmd.extend(["--agent", mapped_agent])

            # 注意: OpenCode 'run' 模式默认是非交互式的
            # 没有等价于 Claude Code 的 --dangerously-skip-permissions 的选项
            # 参见: https://github.com/anomalyco/opencode/issues/9070

            if json_output:
                cmd.extend(["--format", "json"])

            if verbose:
                cmd.extend(["--log-level", "DEBUG", "--print-logs"])

            # 注意: OpenCode 不支持在创建时指定 --session-id
            # Session ID 必须在启动后从日志中提取

            cmd.append(prompt)

        elif self.platform == "iflow":
            cmd = ["iflow", "-y", "-p"]
            cmd.append(f"${mapped_agent} {prompt}")
        elif self.platform == "codex":
            cmd = ["codex", "exec"]
            cmd.append(prompt)
        elif self.platform == "kiro":
            cmd = ["kiro", "run", prompt]
        elif self.platform == "gemini":
            cmd = ["gemini"]
            cmd.append(prompt)
        elif self.platform == "antigravity":
            raise ValueError(
                "Antigravity 工作流是 UI 斜杠命令；不支持 CLI agent 运行。"
            )
        elif self.platform == "windsurf":
            raise ValueError(
                "Windsurf 工作流是 UI 斜杠命令；不支持 CLI agent 运行。"
            )
        elif self.platform == "qoder":
            cmd = ["qodercli", "-p", prompt]
        elif self.platform == "codebuddy":
            raise ValueError(
                "CodeBuddy 不支持非交互模式（无 CLI agent）"
            )
        elif self.platform == "copilot":
            raise ValueError(
                "GitHub Copilot 仅限 IDE；不支持 CLI agent 运行。"
            )
        elif self.platform == "droid":
            raise ValueError(
                "Factory Droid CLI agent 运行尚不支持。"
            )
        elif self.platform == "pi":
            cmd = ["pi", "-p", prompt]

        else:  # claude
            cmd = ["claude", "-p"]
            cmd.extend(["--agent", mapped_agent])

            if session_id:
                cmd.extend(["--session-id", session_id])

            if skip_permissions:
                cmd.append("--dangerously-skip-permissions")

            if json_output:
                cmd.extend(["--output-format", "stream-json"])

            if verbose:
                cmd.append("--verbose")

            cmd.append(prompt)

        return cmd

    def build_resume_command(self, session_id: str) -> list[str]:
        """构建恢复会话的 CLI 命令。

        参数:
            session_id: 要恢复的会话 ID（iFlow 忽略）

        返回:
            命令参数列表
        """
        if self.platform == "opencode":
            return ["opencode", "run", "--session", session_id]
        elif self.platform == "iflow":
            # iFlow 使用 -c 继续最近的对话
            # session_id 被忽略，因为 iFlow 不支持 session ID
            return ["iflow", "-c"]
        elif self.platform == "codex":
            return ["codex", "resume", session_id]
        elif self.platform == "kiro":
            return ["kiro", "resume", session_id]
        elif self.platform == "gemini":
            return ["gemini", "--resume", session_id]
        elif self.platform == "antigravity":
            raise ValueError(
                "Antigravity 工作流是 UI 斜杠命令；不支持 CLI 恢复。"
            )
        elif self.platform == "windsurf":
            raise ValueError(
                "Windsurf 工作流是 UI 斜杠命令；不支持 CLI 恢复。"
            )
        elif self.platform == "qoder":
            return ["qodercli", "--resume", session_id]
        elif self.platform == "codebuddy":
            raise ValueError(
                "CodeBuddy 不支持非交互模式（无 CLI agent）"
            )
        elif self.platform == "copilot":
            raise ValueError(
                "GitHub Copilot 仅限 IDE；不支持 CLI 恢复。"
            )
        elif self.platform == "droid":
            raise ValueError(
                "Factory Droid CLI 恢复尚不支持。"
            )
        elif self.platform == "pi":
            return ["pi", "-c", session_id]
        else:
            return ["claude", "--resume", session_id]

    def get_resume_command_str(self, session_id: str, cwd: str | None = None) -> str:
        """获取人类可读的恢复命令字符串。

        参数:
            session_id: 要恢复的会话 ID
            cwd: 可选的工作目录，用于 cd 进入

        返回:
            用于显示的命令字符串
        """
        cmd = self.build_resume_command(session_id)
        cmd_str = " ".join(cmd)

        if cwd:
            return f"cd {cwd} && {cmd_str}"
        return cmd_str

    # =========================================================================
    # 平台检测辅助方法
    # =========================================================================

    @property
    def is_opencode(self) -> bool:
        """检查平台是否为 OpenCode。"""
        return self.platform == "opencode"

    @property
    def is_claude(self) -> bool:
        """检查平台是否为 Claude Code。"""
        return self.platform == "claude"

    @property
    def is_cursor(self) -> bool:
        """检查平台是否为 Cursor。"""
        return self.platform == "cursor"

    @property
    def is_iflow(self) -> bool:
        """检查平台是否为 iFlow CLI。"""
        return self.platform == "iflow"

    @property
    def cli_name(self) -> str:
        """获取 CLI 可执行文件名。

        注意: Cursor 没有 CLI 工具，返回类似 None 的值。
        """
        if self.is_opencode:
            return "opencode"
        elif self.is_cursor:
            return "cursor"  # 注意: Cursor 仅限 IDE，无 CLI
        elif self.platform == "iflow":
            return "iflow"
        elif self.platform == "kiro":
            return "kiro"
        elif self.platform == "gemini":
            return "gemini"
        elif self.platform == "antigravity":
            return "agy"
        elif self.platform == "windsurf":
            return "windsurf"
        elif self.platform == "qoder":
            return "qodercli"
        elif self.platform == "codebuddy":
            return "codebuddy"
        elif self.platform == "copilot":
            return "copilot"
        elif self.platform == "droid":
            return "droid"
        elif self.platform == "pi":
            return "pi"
        else:
            return "claude"

    @property
    def supports_cli_agents(self) -> bool:
        """检查平台是否支持通过 CLI 运行 agent。

        Claude Code、OpenCode、iFlow 和 Codex 支持 CLI agent 执行。
        Cursor 仅限 IDE，不支持 CLI agent。
        """
        return self.platform in ("claude", "opencode", "iflow", "codex", "pi")

    @property
    def requires_agent_definition_file(self) -> bool:
        """检查平台是否需要 agent 定义文件（.md/.toml）才能运行。

        Claude Code、OpenCode、iFlow: 需要 agent .md 文件（--agent 标志）。
        Codex: 从 .codex/agents/*.toml 自动发现 agent，不需要 --agent 标志。
        """
        return self.platform in ("claude", "opencode", "iflow")

    # =========================================================================
    # Session ID 处理
    # =========================================================================

    @property
    def supports_session_id_on_create(self) -> bool:
        """检查平台是否支持在创建时指定 session ID。

        Claude Code: 支持（--session-id）
        OpenCode: 不支持（自动生成，从日志中提取）
        iFlow: 不支持（无 session ID 支持）
        """
        return self.platform == "claude"

    def extract_session_id_from_log(self, log_content: str) -> str | None:
        """从日志输出中提取 session ID（仅 OpenCode）。

        OpenCode 生成的 session ID 格式: ses_xxx

        参数:
            log_content: 日志文件内容

        返回:
            找到的 session ID，如果未找到则返回 None
        """
        import re

        # OpenCode session ID 正则模式
        match = re.search(r"ses_[a-zA-Z0-9]+", log_content)
        if match:
            return match.group(0)
        return None


# =============================================================================
# 工厂函数
# =============================================================================


def get_cli_adapter(platform: str = "claude") -> CLIAdapter:
    """获取指定平台的 CLI 适配器。

    参数:
        platform: 平台名称（'claude'、'opencode'、'cursor'、'iflow'、'codex'、'kilo'、'kiro'、'gemini'、'antigravity'、'windsurf'、'qoder'、'codebuddy'、'copilot'、'droid' 或 'pi'）

    返回:
        CLIAdapter 实例

    抛出:
        ValueError: 如果平台不受支持
    """
    if platform not in (
        "claude",
        "opencode",
        "cursor",
        "iflow",
        "codex",
        "kilo",
        "kiro",
        "gemini",
        "antigravity",
        "windsurf",
        "qoder",
        "codebuddy",
        "copilot",
        "droid",
        "pi",
    ):
        raise ValueError(
            f"不支持的平台: {platform}（必须是 'claude'、'opencode'、'cursor'、'iflow'、'codex'、'kilo'、'kiro'、'gemini'、'antigravity'、'windsurf'、'qoder'、'codebuddy'、'copilot'、'droid' 或 'pi'）"
        )

    return CLIAdapter(platform=platform)  # type: ignore


_ALL_PLATFORM_CONFIG_DIRS = (
    ".claude",
    ".cursor",
    ".iflow",
    ".opencode",
    ".codex",
    ".kilocode",
    ".kiro",
    ".gemini",
    ".agent",
    ".windsurf",
    ".qoder",
    ".codebuddy",
    ".github/copilot",
    ".factory",
    ".pi",
)
"""由 detect_platform 排除检查使用的平台特定配置目录名。
`.agents/skills/` 未在此列出：它是共享的跨平台层
（由 Codex 写入，也通过 agentskills.io 标准被 Amp/Cline/Warp 等消费），
不是单一平台信号。它的存在不应阻止 Kiro、Antigravity、Windsurf
或其他平台的检测。"""


def _has_other_platform_dir(project_root: Path, exclude: set[str]) -> bool:
    """检查除了 *exclude* 中的目录外，是否存在任何平台配置目录。"""
    return any(
        (project_root / d).is_dir()
        for d in _ALL_PLATFORM_CONFIG_DIRS
        if d not in exclude
    )


def detect_platform(project_root: Path) -> Platform:
    """基于现有配置目录自动检测平台。

    检测顺序:
    1. TRELLIS_PLATFORM 环境变量（如果设置）
    2. .opencode 目录存在 → opencode
    3. .iflow 目录存在 → iflow
    4. .cursor 目录存在（无 .claude）→ cursor
    5. .codex 存在且无其他平台目录 → codex
    6. .kilocode 目录存在 → kilo
    7. .kiro/skills 存在且无其他平台目录 → kiro
    8. .gemini 目录存在 → gemini
    9. .agent/workflows 存在且无其他平台目录 → antigravity
    10. .windsurf/workflows 存在且无其他平台目录 → windsurf
    11. .codebuddy 目录存在 → codebuddy
    12. .qoder 目录存在 → qoder
    13. .pi 目录存在 → pi
    14. 默认 → claude

    参数:
        project_root: 项目根目录

    返回:
        检测到的平台（'claude'、'opencode'、'cursor'、'iflow'、'codex'、'kilo'、'kiro'、'gemini'、'antigravity'、'windsurf'、'qoder'、'codebuddy'、'copilot'、'droid'、'pi' 或默认 'claude'）
    """
    import os

    # 首先检查环境变量
    env_platform = os.environ.get("TRELLIS_PLATFORM", "").lower()
    if env_platform in (
        "claude",
        "opencode",
        "cursor",
        "iflow",
        "codex",
        "kilo",
        "kiro",
        "gemini",
        "antigravity",
        "windsurf",
        "qoder",
        "codebuddy",
        "copilot",
        "droid",
        "pi",
    ):
        return env_platform  # type: ignore

    # 检查 .opencode 目录（OpenCode 专用）
    if (project_root / ".opencode").is_dir():
        return "opencode"

    # 检查 .iflow 目录（iFlow 专用）
    if (project_root / ".iflow").is_dir():
        return "iflow"

    # 检查 .cursor 目录（Cursor 专用）
    # 仅当 .claude 不存在时才检测为 cursor（避免混淆）
    if (project_root / ".cursor").is_dir() and not (project_root / ".claude").is_dir():
        return "cursor"

    # 检查 .gemini 目录（Gemini CLI 专用）
    if (project_root / ".gemini").is_dir():
        return "gemini"

    # 检查 .codex 目录（Codex 专用）
    # 仅 .agents/skills/ 不会触发 codex 检测（它是共享标准）
    if (project_root / ".codex").is_dir() and not _has_other_platform_dir(
        project_root, {".codex", ".agents"}
    ):
        return "codex"

    # 检查 .kilocode 目录（Kilo 专用）
    if (project_root / ".kilocode").is_dir():
        return "kilo"

    # 仅当没有其他平台配置存在时才检查 Kiro skills 目录
    if (project_root / ".kiro" / "skills").is_dir() and not _has_other_platform_dir(
        project_root, {".kiro"}
    ):
        return "kiro"

    # 仅当没有其他平台配置存在时才检查 Antigravity 工作流目录
    if (
        project_root / ".agent" / "workflows"
    ).is_dir() and not _has_other_platform_dir(
        project_root, {".agent", ".gemini"}
    ):
        return "antigravity"

    # 仅当没有其他平台配置存在时才检查 Windsurf 工作流目录
    if (
        project_root / ".windsurf" / "workflows"
    ).is_dir() and not _has_other_platform_dir(
        project_root, {".windsurf"}
    ):
        return "windsurf"

    # 检查 .codebuddy 目录（CodeBuddy 专用）
    if (project_root / ".codebuddy").is_dir():
        return "codebuddy"

    # 检查 .qoder 目录（Qoder 专用）
    if (project_root / ".qoder").is_dir():
        return "qoder"

    # 检查 .github/copilot 目录（GitHub Copilot 专用）
    if (project_root / ".github" / "copilot").is_dir():
        return "copilot"

    # 检查 .factory 目录（Factory Droid 专用）
    if (project_root / ".factory").is_dir():
        return "droid"

    # 检查 .pi 目录（Pi Agent 专用）
    if (project_root / ".pi").is_dir():
        return "pi"

    # 回退：checkout 只有 Codex 共享 skills 层
    # （.agents/skills/trellis-* 目录）且没有显式平台配置目录。
    # 发生在全新 clone 上，其中 .codex/ 被 gitignore/不存在，
    # 但共享 skills 被提交到 git。必须防止 .claude/ 或任何其他
    # 平台目录也同时存在的情况 — .agents/skills/
    # 可以作为共享消费层与任何平台合法共存，
    # 供 Amp/Cline/Warp 等使用。
    agents_skills = project_root / ".agents" / "skills"
    if agents_skills.is_dir() and not _has_other_platform_dir(
        project_root, set()
    ):
        try:
            for entry in agents_skills.iterdir():
                if entry.is_dir() and entry.name.startswith("trellis-"):
                    return "codex"
        except OSError:
            pass

    return "claude"


def get_cli_adapter_auto(project_root: Path) -> CLIAdapter:
    """获取自动检测平台的 CLI 适配器。

    参数:
        project_root: 项目根目录

    返回:
        检测到平台的 CLIAdapter 实例
    """
    platform = detect_platform(project_root)
    return CLIAdapter(platform=platform)
