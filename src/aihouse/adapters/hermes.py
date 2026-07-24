"""
Hermes Agent 适配器 — 通过进程检测 + SQLite/JSON 读取会话状态
"""

import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

from aihouse.core.adapter import AgentAdapter
from aihouse.core.models import AgentActivity, AgentStatus, AgentTask, TaskStatus

HERMES_STATE_DB = Path.home() / ".hermes" / "state.db"
HERMES_SESSIONS_DIR = Path.home() / ".hermes" / "sessions"


class HermesAdapter(AgentAdapter):
    """Hermes Agent 适配器"""

    name = "Hermes"
    agent_type = "hermes"

    def __init__(self, config: Optional[dict] = None) -> None:
        config = config or {}
        self._process_name: str = config.get("process_name", "hermes")
        self._db_path: str = config.get("db_path", str(HERMES_STATE_DB))

    def detect(self) -> bool:
        if shutil.which("hermes") is not None:
            return True
        if HERMES_STATE_DB.is_file():
            return True
        if HERMES_SESSIONS_DIR.is_dir():
            return True
        return bool(self._find_processes())

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

    def _read_db_session(self) -> Optional[Dict[str, Any]]:
        """从 Hermes SQLite state.db 读取当前会话"""
        db_path = Path(self._db_path).expanduser()
        if not db_path.is_file():
            return None
        try:
            conn = sqlite3.connect(str(db_path), timeout=1)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id, model, system_prompt, started_at "
                "FROM sessions WHERE started_at IS NOT NULL "
                "ORDER BY started_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
            conn.close()
            if row is None:
                return None
            return dict(row)
        except (sqlite3.Error, OSError):
            return None

    def _read_json_session(self) -> Optional[Dict[str, Any]]:
        """兜底：从 ~/.hermes/sessions/session_*.json 读取最新会话"""
        sessions_dir = HERMES_SESSIONS_DIR.expanduser()
        if not sessions_dir.is_dir():
            return None
        json_files = sorted(
            [f for f in sessions_dir.iterdir() if f.name.startswith("session_") and f.suffix == ".json"],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if not json_files:
            return None
        try:
            with open(json_files[0], "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def _get_session(self) -> Optional[Dict[str, Any]]:
        """读取当前会话，先试 state.db，再试 JSON 文件"""
        session = self._read_db_session()
        if session is not None:
            return session
        return self._read_json_session()

    def get_status(self) -> AgentStatus:
        try:
            procs = self._find_processes()
        except Exception as e:
            raise RuntimeError(f"检测 Hermes 进程失败: {e}")

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
        session = self._get_session()
        if session is None:
            return None

        # state.db 字段
        description = (
            session.get("system_prompt", "")
            or session.get("context", "")
            or session.get("prompt", "")
            or "Hermes 任务"
        )

        # JSON 文件字段
        if not description:
            description = (
                session.get("description", "")
                or session.get("goal", "")
                or "Hermes 任务"
            )

        status_map = {
            "running": TaskStatus.RUNNING,
            "completed": TaskStatus.COMPLETED,
            "failed": TaskStatus.FAILED,
        }
        status = status_map.get(session.get("status", ""), TaskStatus.RUNNING)

        started_at_str = session.get("started_at") or session.get("created_at")
        started_at = datetime.now()
        if started_at_str:
            try:
                started_at = datetime.fromisoformat(started_at_str)
            except (ValueError, TypeError):
                pass

        session_id = str(session.get("id", session.get("session_id", "")))
        return AgentTask(
            agent_name=self.name, agent_type=self.agent_type,
            task_id=f"hermes_{session_id or 'unknown'}_{int(started_at.timestamp())}",
            description=description[:200],
            started_at=started_at, status=status,
            session_id=session_id,
        )
