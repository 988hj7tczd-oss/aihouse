import platform
import shutil
from datetime import datetime
from typing import Optional

from aihouse.core.adapter import AgentAdapter
from aihouse.core.models import AgentActivity, AgentStatus, AgentTask, TaskStatus

IS_WINDOWS = platform.system() == "Windows"


class PiAdapter(AgentAdapter):

    name = "Pi"
    agent_type = "pi"

    def detect(self) -> bool:
        if shutil.which("pi") is not None:
            return True
        return False

    def _find_processes(self) -> bool:
        keywords = ["pi"]
        if IS_WINDOWS:
            keywords.append("pi.exe")
        import psutil
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                name = (proc.info.get("name") or "").lower()
                cmdline = " ".join(proc.info.get("cmdline") or []).lower()
                if any(kw in name or kw in cmdline for kw in keywords):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def get_status(self) -> AgentStatus:
        if not self.detect():
            return AgentStatus(
                agent_name=self.name, agent_type=self.agent_type,
                activity=AgentActivity.NOT_RUNNING, last_seen=datetime.now(),
                tasks_today=0, total_cost_today=0.0, pid=None,
            )

        current_task = self.get_current_task()
        if current_task is not None:
            activity = AgentActivity.ACTIVE
        else:
            activity = AgentActivity.IDLE

        return AgentStatus(
            agent_name=self.name, agent_type=self.agent_type,
            activity=activity, current_task=current_task,
            last_seen=datetime.now(), tasks_today=0, total_cost_today=0.0, pid=None,
        )

    def get_current_task(self) -> Optional[AgentTask]:
        if self.detect():
            return AgentTask(
                agent_name=self.name, agent_type=self.agent_type,
                task_id=f"pi_{int(datetime.now().timestamp())}",
                description="Pi 正在运行",
                started_at=datetime.now(), status=TaskStatus.RUNNING,
            )
        return None
