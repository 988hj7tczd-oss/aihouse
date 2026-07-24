import platform
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional

import psutil

from aihouse.core.adapter import AgentAdapter
from aihouse.core.models import AgentActivity, AgentStatus, AgentTask, TaskStatus

IS_WINDOWS = platform.system() == "Windows"


class CodexAdapter(AgentAdapter):

    name = "Codex CLI"
    agent_type = "codex"

    def __init__(self, config: Optional[dict] = None) -> None:
        config = config or {}
        self._process_name: str = config.get("process_name", "codex")

    def detect(self) -> bool:
        return shutil.which("codex") is not None

    def _find_processes(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        keywords = [self._process_name.lower()]
        if IS_WINDOWS:
            keywords.append(f"{self._process_name.lower()}.exe")
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
        procs = self._find_processes()
        if not procs:
            return None
        create_time = procs[0].get("create_time")
        started_at = datetime.fromtimestamp(create_time) if create_time else datetime.now()
        return AgentTask(
            agent_name=self.name, agent_type=self.agent_type,
            task_id=f"codex_{procs[0]['pid']}_{int(started_at.timestamp())}",
            description="Codex CLI 正在运行",
            started_at=started_at, status=TaskStatus.RUNNING,
            session_id=f"pid_{procs[0]['pid']}",
        )
