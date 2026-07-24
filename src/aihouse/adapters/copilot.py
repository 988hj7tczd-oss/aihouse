import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

from aihouse.core.adapter import AgentAdapter
from aihouse.core.models import AgentActivity, AgentStatus, AgentTask, TaskStatus

COPILOT_EXT_PATHS = [
    Path.home() / ".vscode" / "extensions" / "github.copilot",
    Path.home() / ".vscode" / "extensions" / "github.copilot-chat",
    Path.home() / ".vscode-insiders" / "extensions" / "github.copilot",
    Path.home() / ".vscode-insiders" / "extensions" / "github.copilot-chat",
]


class CopilotAdapter(AgentAdapter):

    name = "GitHub Copilot"
    agent_type = "copilot"

    def __init__(self, config: Optional[dict] = None) -> None:
        config = config or {}
        self._process_name: str = config.get("process_name", "github-copilot")

    def _find_extensions(self) -> bool:
        for ext_path in COPILOT_EXT_PATHS:
            if ext_path.is_dir():
                return True
        return False

    def detect(self) -> bool:
        if self._find_extensions():
            return True
        if shutil.which("github-copilot") is not None:
            return True
        return bool(self._find_processes())

    def _find_processes(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        keywords = ["github-copilot", "copilot", "github copilot"]
        for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
            try:
                info = proc.info
                name = (info.get("name") or "").lower()
                cmdline = " ".join(info.get("cmdline") or []).lower()
                if any(kw in name or kw in cmdline for kw in keywords):
                    results.append({
                        "pid": info["pid"],
                        "create_time": info.get("create_time"),
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return results

    def get_status(self) -> AgentStatus:
        try:
            procs = self._find_processes()
        except Exception as e:
            raise RuntimeError(f"检测 {self.name} 进程失败: {e}")

        if not procs:
            return AgentStatus(
                agent_name=self.name, agent_type=self.agent_type,
                activity=AgentActivity.NOT_RUNNING, last_seen=datetime.now(),
                tasks_today=0, total_cost_today=0.0, pid=None,
            )

        proc = procs[0]
        pid = proc["pid"]
        create_time = proc.get("create_time")
        last_seen = datetime.fromtimestamp(create_time) if create_time else datetime.now()
        current_task = self.get_current_task()
        activity = AgentActivity.ACTIVE if current_task else AgentActivity.IDLE

        return AgentStatus(
            agent_name=self.name, agent_type=self.agent_type,
            activity=activity, current_task=current_task,
            last_seen=last_seen, tasks_today=0, total_cost_today=0.0, pid=pid,
        )

    def get_current_task(self) -> Optional[AgentTask]:
        return None
