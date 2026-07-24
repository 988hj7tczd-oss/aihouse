import shutil
from datetime import datetime
from typing import Optional

import psutil

from aihouse.core.adapter import AgentAdapter
from aihouse.core.models import AgentActivity, AgentStatus, AgentTask, TaskStatus


class PiAdapter(AgentAdapter):

    name = "Pi"
    agent_type = "pi"

    def detect(self) -> bool:
        if shutil.which("pi") is not None:
            return True
        return False

    def get_status(self) -> AgentStatus:
        if not self.detect():
            return AgentStatus(
                agent_name=self.name, agent_type=self.agent_type,
                activity=AgentActivity.NOT_RUNNING, last_seen=datetime.now(),
                tasks_today=0, total_cost_today=0.0, pid=None,
            )

        return AgentStatus(
            agent_name=self.name, agent_type=self.agent_type,
            activity=AgentActivity.IDLE,
            last_seen=datetime.now(), tasks_today=0, total_cost_today=0.0, pid=None,
        )

    def get_current_task(self) -> Optional[AgentTask]:
        return None
