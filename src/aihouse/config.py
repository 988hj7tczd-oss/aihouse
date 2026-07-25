import os
import platform
import shutil
from pathlib import Path
from typing import Any, Dict, List

import psutil
import yaml

CONFIG_DIR: Path = Path.home() / ".aihouse"
CONFIG_FILE: Path = CONFIG_DIR / "config.yaml"
ENV_FILE: Path = CONFIG_DIR / ".env"

AGENT_TYPE_MAP: Dict[str, str] = {
    "Claude Code": "claude_code",
    "Cursor": "cursor",
    "Codex CLI": "codex",
    "Codex++": "codex",
    "OpenCode": "opencode",
    "Hermes": "hermes",
    "Kilo Code": "kilo_code",
    "OpenClaw": "openclaw",
    "Cline": "cline",
    "Pi": "pi",
    "GitHub Copilot": "copilot",
    "通义灵码": "tongyi",
}

KNOWN_AGENTS: List[Dict[str, Any]] = [
    {"name": "Hermes", "keywords": ["hermes"], "dirs": ["~/.hermes"], "category": "编码"},
    {"name": "Claude Code", "keywords": ["claude"], "dirs": ["~/.claude"], "category": "编码"},
    {"name": "Cursor", "keywords": ["cursor"], "dirs": ["/Applications/Cursor.app", "%LOCALAPPDATA%\\Programs\\Cursor\\Cursor.exe"], "category": "编码"},
    {"name": "Codex CLI", "keywords": ["codex"], "dirs": ["~/.codex"], "category": "编码"},
    {"name": "OpenCode", "keywords": ["opencode", "opc"], "dirs": ["~/.local/share/opencode", "%APPDATA%\\opencode"], "category": "编码"},
    {"name": "Pi", "keywords": ["pi"], "dirs": [], "category": "通用"},
    {"name": "OpenClaw", "keywords": ["openclaw"], "dirs": [], "category": "编码"},
    {"name": "Kilo Code", "keywords": ["kilo"], "dirs": ["~/.vscode/extensions"], "category": "编码"},
    {"name": "Cline", "keywords": ["cline"], "dirs": ["~/.vscode/extensions"], "category": "编码"},
]


def _expand_path(d: str) -> Path:
    p = os.path.expandvars(d)
    return Path(p).expanduser().resolve()


def _check_directory(dirs: List[str]) -> bool:
    for d in dirs:
        p = _expand_path(d)
        if p.exists():
            return True
    return False


def _scan_processes(keywords: List[str]) -> bool:
    keywords_lower = [kw.lower() for kw in keywords]
    try:
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                name = (proc.info.get("name") or "").lower()
                cmdline = " ".join(proc.info.get("cmdline") or []).lower()
                combined = f"{name} {cmdline}"
                if any(kw in combined for kw in keywords_lower):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
    return False


def _is_agent_installed(agent: Dict[str, Any]) -> bool:
    if _check_directory(agent.get("dirs", [])):
        return True
    if _scan_processes(agent.get("keywords", [])):
        return True
    return False


def init_config(force: bool = False) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        raise PermissionError(f"没有权限创建目录: {CONFIG_DIR}")
    except OSError as e:
        raise OSError(f"创建配置目录失败: {e}")

    if CONFIG_FILE.exists() and not force:
        return

    detected = detect_agents()
    enabled_agents = []
    for a in detected:
        if a["installed"]:
            entry = {"name": a["name"], "type": a["type"], "enabled": True}
            if "process_name" in a:
                entry["process_name"] = a["process_name"]
            enabled_agents.append(entry)

    if not enabled_agents:
        enabled_agents = [
            {"name": "通用模式", "type": "generic", "enabled": True},
        ]

    config: Dict[str, Any] = {
        "project": "AIHouse",
        "version": 2,
        "agents": enabled_agents,
        "notifications": [
            {
                "type": "pushplus",
                "token": "${PUSHPLUS_TOKEN}",
                "events": ["task_failed", "agent_stuck"],
            },
        ],
        "settings": {
            "poll_interval": 10,
            "history_retention_days": 30,
            "auto_start": False,
        },
    }

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    except OSError as e:
        raise OSError(f"写入配置文件失败: {e}")

    if not ENV_FILE.exists() or force:
        try:
            ENV_FILE.touch(exist_ok=True)
        except OSError as e:
            raise OSError(f"创建 .env 文件失败: {e}")


def load_config() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"配置文件不存在: {CONFIG_FILE}")

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config: Dict[str, Any] = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"配置文件格式错误: {e}")
    except PermissionError:
        raise PermissionError(f"没有权限读取配置文件: {CONFIG_FILE}")
    except OSError as e:
        raise OSError(f"读取配置文件失败: {e}")

    return config


def get_config_path() -> Path:
    return CONFIG_FILE


def detect_agents() -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    seen_names: set = set()

    for agent in KNOWN_AGENTS:
        installed = _is_agent_installed(agent)
        agent_type = AGENT_TYPE_MAP.get(agent["name"], "generic")

        entry: Dict[str, Any] = {
            "name": agent["name"],
            "type": agent_type,
            "category": agent["category"],
            "installed": installed,
        }
        if installed:
            entry["process_name"] = agent["keywords"][0]

        results.append(entry)
        if installed:
            seen_names.add(agent["name"])

    return results


def _get_template_path(filename: str) -> Path:
    local_path = Path(__file__).parent / filename
    if local_path.exists():
        return local_path
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / filename


def _copy_if_not_exists(source: Path, target: Path, force: bool = False) -> None:
    if target.exists() and not force:
        return
    if not source.exists():
        raise FileNotFoundError(f"模板文件不存在: {source}")
    try:
        shutil.copy2(source, target)
    except OSError as e:
        raise OSError(f"复制模板文件失败: {e}")
