import platform
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

from aihouse.core.adapter import AgentAdapter
from aihouse.core.models import AgentActivity, AgentStatus, AgentTask, TaskStatus

IS_WINDOWS = platform.system() == "Windows"

CLAUDE_LOG_DIR = Path.home() / ".claude" / "logs"


class ClaudeCodeAdapter(AgentAdapter):

    name = "Claude Code"
    agent_type = "claude_code"

    def __init__(self, config: Optional[dict] = None) -> None:
        config = config or {}
        self._process_name: str = config.get("process_name", "claude")

    def detect(self) -> bool:
        if shutil.which("claude") is not None:
            return True
        if Path.home().joinpath(".claude").is_dir():
            return True
        return bool(self._find_processes())

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

    def _get_latest_log(self) -> Optional[Path]:
        if not CLAUDE_LOG_DIR.is_dir():
            return None
        log_files = sorted(
            [f for f in CLAUDE_LOG_DIR.iterdir() if f.is_file() and f.suffix in (".log", ".txt", ".json", "")],
            key=lambda f: f.stat().st_mtime, reverse=True,
        )
        return log_files[0] if log_files else None

    def get_status(self) -> AgentStatus:
        try:
            procs = self._find_processes()
        except Exception as e:
            raise RuntimeError(f"检测 {self.name} 进程失败: {e}")

        pid = None
        create_time = None
        last_seen = datetime.now()

        if procs:
            pid = procs[0]["pid"]
            create_time = procs[0].get("create_time")
            if create_time:
                last_seen = datetime.fromtimestamp(create_time)

        log_path = self._get_latest_log()
        if log_path is not None:
            log_mtime = datetime.fromtimestamp(log_path.stat().st_mtime)
            if log_mtime > last_seen:
                last_seen = log_mtime

        current_task = self.get_current_task()
        if current_task is not None:
            activity = AgentActivity.ACTIVE
        elif procs:
            activity = AgentActivity.IDLE
        else:
            activity = AgentActivity.NOT_RUNNING

        return AgentStatus(
            agent_name=self.name, agent_type=self.agent_type,
            activity=activity, current_task=current_task,
            last_seen=last_seen, tasks_today=0, total_cost_today=0.0, pid=pid,
        )

    def get_current_task(self) -> Optional[AgentTask]:
        log_path = self._get_latest_log()
        if log_path is not None:
            try:
                content = log_path.read_text(encoding="utf-8", errors="ignore")
                description = content.strip()[:200] or "Claude Code 任务"
                mtime = datetime.fromtimestamp(log_path.stat().st_mtime)
                return AgentTask(
                    agent_name=self.name, agent_type=self.agent_type,
                    task_id=f"claude_{log_path.name}_{int(mtime.timestamp())}",
                    description=description, started_at=mtime,
                    status=TaskStatus.RUNNING, session_id=log_path.name,
                )
            except OSError:
                pass

        if self._find_processes():
            return AgentTask(
                agent_name=self.name, agent_type=self.agent_type,
                task_id=f"claude_{int(datetime.now().timestamp())}",
                description="Claude Code 正在运行",
                started_at=datetime.now(), status=TaskStatus.RUNNING,
            )

        return None
