import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

from aihouse.core.adapter import AgentAdapter
from aihouse.core.models import AgentActivity, AgentStatus, AgentTask, TaskStatus

OPENCLAW_DIRS = [
    Path.home() / ".openclaw",
    Path.home() / ".clawdbot",
]
CONFIG_NAMES = ["openclaw.json", "config.json"]


class OpenClawAdapter(AgentAdapter):

    name = "OpenClaw"
    agent_type = "openclaw"

    def __init__(self, config: Optional[dict] = None) -> None:
        config = config or {}
        self._process_name: str = config.get("process_name", "openclaw")

    def _find_config_dir(self) -> Optional[Path]:
        for d in OPENCLAW_DIRS:
            if d.is_dir():
                return d
        return None

    def _find_config(self) -> Optional[Path]:
        cfg_dir = self._find_config_dir()
        if cfg_dir is None:
            return None
        for name in CONFIG_NAMES:
            p = cfg_dir / name
            if p.is_file():
                return p
        return None

    def _read_config(self) -> Optional[Dict[str, Any]]:
        cfg_path = self._find_config()
        if cfg_path is None:
            return None
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def detect(self) -> bool:
        if shutil.which("openclaw") is not None:
            return True
        return self._find_config_dir() is not None

    def _find_processes(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        keyword = self._process_name.lower()
        for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
            try:
                info = proc.info
                name = (info.get("name") or "").lower()
                cmdline = " ".join(info.get("cmdline") or []).lower()
                if keyword in name or keyword in cmdline:
                    results.append({
                        "pid": info["pid"],
                        "create_time": info.get("create_time"),
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return results

    def _read_db_session(self, db_path: Path) -> Optional[Dict[str, Any]]:
        if not db_path.is_file():
            return None
        try:
            conn = sqlite3.connect(str(db_path), timeout=1)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id, title, model, status, created_at, updated_at "
                "FROM sessions ORDER BY created_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
            conn.close()
            if row is None:
                return None
            return dict(row)
        except (sqlite3.Error, OSError):
            return None

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
        cfg = self._read_config()
        if cfg is not None:
            session_id = str(cfg.get("session_id", cfg.get("currentSessionId", "")))
            description = cfg.get("description", cfg.get("task", ""))

            db_path_str = cfg.get("dbPath", cfg.get("databasePath", ""))
            if db_path_str:
                db_path = Path(db_path_str).expanduser()
                db_session = self._read_db_session(db_path)
                if db_session is not None:
                    description = description or str(db_session.get("title", ""))
                    session_id = session_id or str(db_session.get("id", ""))
                    model_name = str(db_session.get("model", ""))
                    time_created = db_session.get("created_at")
                    started_at = datetime.now()
                    if time_created:
                        try:
                            started_at = datetime.fromtimestamp(time_created / 1000.0)
                        except (ValueError, TypeError):
                            pass
                    return AgentTask(
                        agent_name=self.name, agent_type=self.agent_type,
                        task_id=f"openclaw_{session_id or 'db'}_{int(started_at.timestamp())}",
                        description=(description or "OpenClaw 任务")[:200],
                        started_at=started_at, status=TaskStatus.RUNNING,
                        session_id=session_id, model_name=model_name,
                    )

            if description:
                return AgentTask(
                    agent_name=self.name, agent_type=self.agent_type,
                    task_id=f"openclaw_cfg_{int(datetime.now().timestamp())}",
                    description=description[:200],
                    started_at=datetime.now(), status=TaskStatus.RUNNING,
                    session_id=session_id,
                )

        return None
