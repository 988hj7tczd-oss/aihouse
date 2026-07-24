"""
SQLite 本地存储模块 — 任务记录、快照、通知记录的持久化
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from aihouse.config import CONFIG_DIR
from aihouse.core.models import AgentTask, TaskStatus


class Storage:
    """
    SQLite 数据库封装

    负责 Agent 任务记录、状态快照、通知记录的存取。
    数据库文件默认位于 ~/.aihouse/aihouse.db。
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """
        初始化数据库连接，自动创建数据库文件和表结构

        Args:
            db_path: 数据库文件路径，默认 ~/.aihouse/aihouse.db
        """
        if db_path is None:
            db_path = str(CONFIG_DIR / "aihouse.db")

        self._db_path: str = db_path

        # 确保父目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self._conn: sqlite3.Connection = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    # ── 建表 ─────────────────────────────────────────────────

    def _create_tables(self) -> None:
        """创建所需的数据库表（如不存在）"""
        with self._conn:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS agent_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_name TEXT NOT NULL,
                    agent_type TEXT NOT NULL,
                    task_id TEXT NOT NULL UNIQUE,
                    description TEXT,
                    project TEXT,
                    status TEXT NOT NULL DEFAULT 'running',
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    duration_seconds REAL,
                    output_summary TEXT,
                    files_changed TEXT,
                    error_message TEXT,
                    estimated_cost REAL,
                    estimated_tokens INTEGER,
                    api_calls INTEGER DEFAULT 0,
                    session_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS agent_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_name TEXT NOT NULL,
                    agent_type TEXT NOT NULL,
                    activity TEXT NOT NULL,
                    pid INTEGER,
                    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT,
                    related_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_agent ON agent_tasks(agent_type, started_at);
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON agent_tasks(status);
                CREATE INDEX IF NOT EXISTS idx_snapshots_time ON agent_snapshots(captured_at);
            """)

    # ── Agent 任务 ────────────────────────────────────────────

    def save_task(self, task: AgentTask) -> int:
        """
        保存一条任务记录

        使用 INSERT OR REPLACE，task_id 重复时自动覆盖。

        Args:
            task: 待保存的任务对象

        Returns:
            数据库记录 ID
        """
        with self._conn:
            cursor = self._conn.execute("""
                INSERT OR REPLACE INTO agent_tasks
                    (agent_name, agent_type, task_id, description, project,
                     status, started_at, completed_at, duration_seconds,
                     output_summary, files_changed, error_message,
                     estimated_cost, estimated_tokens, api_calls, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.agent_name,
                task.agent_type,
                task.task_id,
                task.description,
                task.project,
                task.status.value,
                task.started_at.isoformat(),
                task.completed_at.isoformat() if task.completed_at else None,
                task.duration,
                task.output_summary,
                json.dumps(task.files_changed, ensure_ascii=False),
                task.error_message,
                task.estimated_cost,
                task.estimated_tokens,
                task.api_calls,
                task.session_id,
            ))
            return cursor.lastrowid or 0

    def get_task(self, task_id: str) -> Optional[AgentTask]:
        """
        按 task_id 查询任务

        Args:
            task_id: 任务唯一标识

        Returns:
            任务对象，不存在则返回 None
        """
        row = self._conn.execute(
            "SELECT * FROM agent_tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
        return self._row_to_task(row) if row else None

    def get_recent_tasks(self, agent_type: Optional[str] = None,
                         limit: int = 20) -> List[AgentTask]:
        """
        查询最近的任务，按时间倒序

        Args:
            agent_type: Agent 类型筛选（可选）
            limit: 返回条数上限

        Returns:
            任务对象列表
        """
        if agent_type:
            rows = self._conn.execute(
                "SELECT * FROM agent_tasks WHERE agent_type = ? "
                "ORDER BY started_at DESC LIMIT ?",
                (agent_type, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM agent_tasks ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_task(r) for r in rows]

    def get_tasks_today(self, agent_type: Optional[str] = None) -> List[AgentTask]:
        """
        查询今天的任务

        Args:
            agent_type: Agent 类型筛选（可选）

        Returns:
            今日任务对象列表
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if agent_type:
            rows = self._conn.execute(
                "SELECT * FROM agent_tasks WHERE agent_type = ? AND started_at >= ? "
                "ORDER BY started_at DESC",
                (agent_type, today_start.isoformat()),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM agent_tasks WHERE started_at >= ? "
                "ORDER BY started_at DESC",
                (today_start.isoformat(),),
            ).fetchall()
        return [self._row_to_task(r) for r in rows]

    def get_task_stats_today(self) -> Dict[str, Any]:
        """
        获取今日任务统计

        Returns:
            dict: 包含 total / completed / failed / stuck / total_cost
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        row = self._conn.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
                SUM(CASE WHEN status = 'stuck' THEN 1 ELSE 0 END) AS stuck,
                COALESCE(SUM(estimated_cost), 0) AS total_cost
            FROM agent_tasks
            WHERE started_at >= ?
        """, (today_start.isoformat(),)).fetchone()

        return {
            "total": row["total"] or 0,
            "completed": row["completed"] or 0,
            "failed": row["failed"] or 0,
            "stuck": row["stuck"] or 0,
            "total_cost": float(row["total_cost"] or 0),
        }

    # ── Agent 快照 ────────────────────────────────────────────

    def save_snapshot(self, agent_name: str, agent_type: str,
                      activity: str, pid: Optional[int] = None) -> None:
        """
        保存 Agent 当前状态快照（用于历史趋势分析）

        Args:
            agent_name: Agent 名称
            agent_type: Agent 类型
            activity: 活动状态
            pid: 进程 ID
        """
        with self._conn:
            self._conn.execute("""
                INSERT INTO agent_snapshots (agent_name, agent_type, activity, pid)
                VALUES (?, ?, ?, ?)
            """, (agent_name, agent_type, activity, pid))

    # ── 通知记录 ──────────────────────────────────────────────

    def save_notification(self, event_type: str, title: str,
                          message: str = "",
                          related_agent: Optional[str] = None) -> None:
        """
        记录一条通知（用于去重，避免重复推送同一条告警）

        Args:
            event_type: 事件类型
            title: 通知标题
            message: 通知内容
            related_agent: 相关 Agent 名称
        """
        with self._conn:
            self._conn.execute("""
                INSERT INTO notifications (type, title, message, related_agent)
                VALUES (?, ?, ?, ?)
            """, (event_type, title, message, related_agent))

    def get_recent_notifications(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取最近的通知记录

        Args:
            limit: 返回条数上限

        Returns:
            通知记录字典列表
        """
        rows = self._conn.execute(
            "SELECT * FROM notifications ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── 数据库维护 ────────────────────────────────────────────

    def cleanup_old_data(self, retention_days: int = 30) -> None:
        """
        清理超过 retention_days 的旧数据，避免数据库无限膨胀

        Args:
            retention_days: 保留天数
        """
        cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()
        with self._conn:
            self._conn.execute(
                "DELETE FROM agent_tasks WHERE started_at < ?", (cutoff,)
            )
            self._conn.execute(
                "DELETE FROM agent_snapshots WHERE captured_at < ?", (cutoff,)
            )
            self._conn.execute(
                "DELETE FROM notifications WHERE created_at < ?", (cutoff,)
            )

    def close(self) -> None:
        """关闭数据库连接"""
        self._conn.close()

    # ── 内部工具 ──────────────────────────────────────────────

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> AgentTask:
        """
        将数据库行转换为 AgentTask 对象

        Args:
            row: sqlite3.Row 对象

        Returns:
            AgentTask 实例
        """
        return AgentTask(
            agent_name=row["agent_name"],
            agent_type=row["agent_type"],
            task_id=row["task_id"],
            description=row["description"] or "",
            project=row["project"] or "",
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"])
                if row["completed_at"] else None,
            duration=row["duration_seconds"],
            status=TaskStatus(row["status"]),
            output_summary=row["output_summary"] or "",
            files_changed=json.loads(row["files_changed"])
                if row["files_changed"] else [],
            error_message=row["error_message"] or "",
            estimated_cost=row["estimated_cost"],
            estimated_tokens=row["estimated_tokens"],
            api_calls=row["api_calls"] or 0,
            session_id=row["session_id"] or "",
        )
