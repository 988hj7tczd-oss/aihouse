import os
import platform
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

from aihouse.core.adapter import AgentAdapter
from aihouse.core.models import AgentActivity, AgentStatus, AgentTask, TaskStatus

IS_WINDOWS = platform.system() == "Windows"
LOCAL_APP_DATA = Path(os.environ.get("LOCALAPPDATA", "")) if IS_WINDOWS else Path()


class CursorAdapter(AgentAdapter):

    name = "Cursor"
    agent_type = "cursor"

    def __init__(self, config: Optional[dict] = None) -> None:
        config = config or {}
        self._process_name: str = config.get("process_name", "cursor")

    def detect(self) -> bool:
        if shutil.which("cursor") is not None:
            return True
        if IS_WINDOWS:
            cursor_exe = LOCAL_APP_DATA / "Programs" / "Cursor" / "Cursor.exe"
            if cursor_exe.exists():
                return True
        else:
            if Path("/Applications/Cursor.app").exists():
                return True
        return False

    def _find_processes(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        keywords = ["cursor"]
        if IS_WINDOWS:
            keywords.append("cursor.exe")
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

        return AgentStatus(
            agent_name=self.name, agent_type=self.agent_type,
            activity=AgentActivity.IDLE,
            last_seen=last_seen, tasks_today=0, total_cost_today=0.0, pid=pid,
        )

    def get_current_task(self) -> Optional[AgentTask]:
        return None
