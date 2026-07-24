import json
import platform
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

from aihouse.core.adapter import AgentAdapter
from aihouse.core.models import AgentActivity, AgentStatus, AgentTask, TaskStatus

IS_WINDOWS = platform.system() == "Windows"

OPENCODE_DB = Path.home() / ".local" / "share" / "opencode" / "opencode.db"


class OpenCodeAdapter(AgentAdapter):

    name = "OpenCode"
    agent_type = "opencode"

    def __init__(self, config: Optional[dict] = None) -> None:
        config = config or {}
        self._process_names: list = config.get("processes", ["opencode", "opc"])
        self._db_path: str = config.get("db_path", str(OPENCODE_DB))

    def detect(self) -> bool:
        if shutil.which("opencode") is not None:
            return True
        if shutil.which("opc") is not None:
            return True
        if OPENCODE_DB.is_file():
            return True
        return bool(self._find_processes())

    def _find_processes(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        keywords = [kw.lower() for kw in self._process_names]
        if IS_WINDOWS:
            keywords.extend(f"{kw.lower()}.exe" for kw in self._process_names)
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

    def _read_db_session(self) -> Optional[Dict[str, Any]]:
        db_path = Path(self._db_path).expanduser()
        if not db_path.is_file():
            return None
        try:
            conn = sqlite3.connect(str(db_path), timeout=1)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id, title, model, agent, time_created, time_updated, "
                "cost, tokens_input, tokens_output "
                "FROM session ORDER BY time_created DESC LIMIT 1"
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
        session = self._read_db_session()
        if session is None:
            return None

        description = session.get("title", "") or "OpenCode 任务"

        model_name = ""
        model_raw = session.get("model")
        if model_raw:
            try:
                model_data = json.loads(model_raw) if isinstance(model_raw, str) else model_raw
                model_name = model_data.get("id", "") if isinstance(model_data, dict) else str(model_data)
            except (json.JSONDecodeError, TypeError):
                model_name = str(model_raw)

        time_created_ms = session.get("time_created")
        started_at = datetime.now()
        if time_created_ms:
            try:
                started_at = datetime.fromtimestamp(time_created_ms / 1000.0)
            except (ValueError, TypeError):
                pass

        session_id = str(session.get("id", ""))
        task_id = f"opencode_{session_id or 'unknown'}_{int(started_at.timestamp())}"

        cost = session.get("cost")
        tokens_input = session.get("tokens_input")
        tokens_output = session.get("tokens_output")

        return AgentTask(
            agent_name=self.name, agent_type=self.agent_type,
            task_id=task_id, description=description[:200],
            started_at=started_at, status=TaskStatus.RUNNING,
            session_id=session_id, model_name=model_name,
            estimated_cost=cost, estimated_tokens=(tokens_input or 0) + (tokens_output or 0),
        )
