"""
Hermes Agent 适配器 — 通过进程检测 + SQLite/JSON 读取会话状态
"""

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

HERMES_STATE_DB = Path.home() / ".hermes" / "state.db"
HERMES_SESSIONS_DIR = Path.home() / ".hermes" / "sessions"

CACHE_SECONDS = 60


class HermesAdapter(AgentAdapter):
    """Hermes Agent 适配器"""

    name = "Hermes"
    agent_type = "hermes"

    def __init__(self, config: Optional[dict] = None) -> None:
        config = config or {}
        self._process_name: str = config.get("process_name", "hermes")
        self._db_path: str = config.get("db_path", str(HERMES_STATE_DB))
        self._cached_task: Optional[AgentTask] = None
        self._cached_at: Optional[datetime] = None

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

    # ── DB 读取 ──────────────────────────────────────────

    def _get_conn(self) -> Optional[sqlite3.Connection]:
        db_path = Path(self._db_path).expanduser()
        if not db_path.is_file():
            return None
        try:
            conn = sqlite3.connect(str(db_path), timeout=3)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error:
            return None

    def _get_user_message(self, conn: sqlite3.Connection, session_id: str) -> str:
        try:
            cur = conn.execute(
                "SELECT content FROM messages "
                "WHERE session_id = ? AND role = 'user' "
                "ORDER BY timestamp ASC LIMIT 1",
                (session_id,),
            )
            row = cur.fetchone()
            if row is not None:
                content = row["content"] or ""
                if len(content) > 200:
                    content = content[:200] + "..."
                return content
        except sqlite3.Error:
            pass
        return ""

    def _build_task_from_row(self, row: Dict[str, Any], conn: Optional[sqlite3.Connection] = None) -> Optional[AgentTask]:
        session_id = str(row.get("id", ""))
        if not session_id:
            return None

        description = ""
        if conn is not None:
            description = self._get_user_message(conn, session_id)
        if not description:
            description = str(row.get("title", "") or "")
        if not description:
            description = "Hermes 任务"

        started_at = datetime.now()
        raw_start = row.get("started_at")
        if raw_start:
            try:
                started_at = datetime.fromtimestamp(float(raw_start))
            except (ValueError, TypeError):
                pass

        ended_at = None
        raw_end = row.get("ended_at")
        if raw_end:
            try:
                ended_at = datetime.fromtimestamp(float(raw_end))
            except (ValueError, TypeError):
                pass

        message_count = row.get("message_count", 0) or 0
        if ended_at is None and message_count > 0:
            status = TaskStatus.RUNNING
        elif ended_at is not None:
            end_reason = str(row.get("end_reason", "") or "")
            if end_reason == "error":
                status = TaskStatus.FAILED
            else:
                status = TaskStatus.COMPLETED
        else:
            status = TaskStatus.UNKNOWN

        duration = None
        if ended_at is not None:
            duration = (ended_at - started_at).total_seconds()
        else:
            duration = (datetime.now() - started_at).total_seconds()
        duration = round(duration, 1)

        in_tokens = row.get("in_tokens", row.get("input_tokens", 0)) or 0
        out_tokens = row.get("out_tokens", row.get("output_tokens", 0)) or 0
        cost = row.get("cost", row.get("estimated_cost_usd", 0.0)) or 0.0
        model_name = str(row.get("model", "") or "")

        return AgentTask(
            agent_name=self.name, agent_type=self.agent_type,
            task_id=f"hermes_{session_id}_{int(started_at.timestamp())}",
            description=description,
            started_at=started_at, completed_at=ended_at,
            duration=duration, status=status,
            session_id=session_id, model_name=model_name,
            estimated_cost=float(cost),
            estimated_tokens=int(in_tokens) + int(out_tokens),
        )

    def _run_session_query(self, conn: sqlite3.Connection, where_clause: str) -> Optional[AgentTask]:
        try:
            cur = conn.execute(
                "SELECT s.*, "
                "COALESCE(u.api_call_count, 0) as api_count, "
                "COALESCE(u.input_tokens, s.input_tokens, 0) as in_tokens, "
                "COALESCE(u.output_tokens, s.output_tokens, 0) as out_tokens, "
                "COALESCE(u.estimated_cost_usd, s.estimated_cost_usd, 0.0) as cost "
                "FROM sessions s "
                "LEFT JOIN session_model_usage u ON u.session_id = s.id "
                f"WHERE s.started_at IS NOT NULL {where_clause} "
                "ORDER BY s.started_at DESC LIMIT 1"
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._build_task_from_row(dict(row), conn)
        except sqlite3.Error:
            return None

    def _get_current_session(self) -> Optional[AgentTask]:
        conn = self._get_conn()
        if conn is None:
            return None
        # 第一步：优先活跃 session（未结束、非 cron 源）
        task = self._run_session_query(conn,
            "AND s.ended_at IS NULL "
            "AND (s.source IS NULL OR s.source NOT IN ('cron'))"
        )
        if task is not None:
            conn.close()
            return task
        # 第二步：无活跃 session，回退最新已完成 session
        task = self._run_session_query(conn,
            "AND s.ended_at IS NOT NULL "
            "AND (s.source IS NULL OR s.source NOT IN ('cron'))"
        )
        conn.close()
        return task

    def _get_cached_or_new(self) -> Optional[AgentTask]:
        task = self._get_current_session()
        if task is not None:
            self._cached_task = task
            self._cached_at = datetime.now()
            return task
        if self._cached_task is not None and self._cached_at is not None:
            elapsed = (datetime.now() - self._cached_at).total_seconds()
            if elapsed < CACHE_SECONDS:
                return self._cached_task
        return None

    # ── 接口实现 ─────────────────────────────────────────

    def get_status(self) -> AgentStatus:
        try:
            procs = self._find_processes()
        except Exception as e:
            raise RuntimeError(f"检测 Hermes 进程失败: {e}")

        pid = None
        create_time = None
        if procs:
            pid = procs[0]["pid"]
            create_time = procs[0].get("create_time")

        current_task = self.get_current_task()
        last_seen = datetime.now()
        if current_task is not None and current_task.started_at:
            last_seen = current_task.started_at
        elif create_time:
            last_seen = datetime.fromtimestamp(create_time)

        if current_task is not None and current_task.status == TaskStatus.RUNNING:
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
        return self._get_cached_or_new()

    def get_recent_tasks(self, limit: int = 20) -> List[AgentTask]:
        conn = self._get_conn()
        if conn is None:
            return []
        try:
            cur = conn.execute(
                "SELECT s.*, "
                "COALESCE(u.api_call_count, 0) as api_count, "
                "COALESCE(u.input_tokens, s.input_tokens, 0) as in_tokens, "
                "COALESCE(u.output_tokens, s.output_tokens, 0) as out_tokens, "
                "COALESCE(u.estimated_cost_usd, s.estimated_cost_usd, 0.0) as cost "
                "FROM sessions s "
                "LEFT JOIN session_model_usage u ON u.session_id = s.id "
                "WHERE s.ended_at IS NOT NULL AND s.message_count > 0 "
                "ORDER BY s.ended_at DESC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()
            conn.close()
            tasks: List[AgentTask] = []
            for row in rows:
                task = self._build_task_from_row(dict(row))
                if task is not None:
                    tasks.append(task)
            return tasks
        except sqlite3.Error:
            try:
                conn.close()
            except Exception:
                pass
            return []
