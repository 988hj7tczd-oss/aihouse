"""
分析引擎 — 卡住检测、异常检测、费用分析、趋势汇总
"""

from datetime import datetime, timedelta
from statistics import mean
from typing import Any, Dict, List, Optional

from aihouse.core.models import AgentActivity, AgentStatus, TaskStatus
from aihouse.core.storage import Storage


class Analyzer:
    """
    分析引擎

    负责：
    - 卡住检测（check_stuck）
    - 异常检测（check_anomaly）
    - 费用分析（check_budget）
    - 今日汇总（get_today_summary）
    """

    def __init__(self, storage: Storage, config: dict) -> None:
        """
        初始化分析引擎

        Args:
            storage: Storage 数据库实例
            config: 完整配置字典
        """
        self._storage: Storage = storage
        self._config: dict = config

    # ── 卡住检测 ────────────────────────────────────────────

    def check_stuck(self, status: AgentStatus,
                    threshold: int = 300) -> bool:
        """
        卡住检测

        判断逻辑：
        1. Agent 状态必须是 ACTIVE
        2. 检查当前任务的 started_at
        3. 如果已运行超过 threshold 秒

        Args:
            status: Agent 当前状态
            threshold: 卡住阈值（秒），默认 300 秒（5 分钟）

        Returns:
            True 表示疑似卡住
        """
        if status.activity != AgentActivity.ACTIVE:
            return False

        task = status.current_task
        if task is None:
            return False

        elapsed = (datetime.now() - task.started_at).total_seconds()
        return elapsed > threshold

    # ── 异常检测 ────────────────────────────────────────────

    def check_anomaly(self, agent_type: str) -> List[str]:
        """
        异常检测

        检查该 Agent 最近的任务：
        - 连续失败超过 3 次
        - 任务耗时比平时多 5 倍以上

        Args:
            agent_type: Agent 类型标识

        Returns:
            异常描述列表，无异常则返回空列表
        """
        anomalies: List[str] = []

        recent_tasks = self._storage.get_recent_tasks(
            agent_type=agent_type, limit=20
        )
        if not recent_tasks:
            return anomalies

        # ── 连续失败检测 ──
        consecutive_failures = 0
        for task in recent_tasks:
            if task.status == TaskStatus.FAILED:
                consecutive_failures += 1
            elif task.status in (TaskStatus.COMPLETED, TaskStatus.RUNNING):
                break

        if consecutive_failures >= 3:
            anomalies.append(
                f"{agent_type} 连续失败 {consecutive_failures} 次"
            )

        # ── 耗时异常检测 ──
        completed_tasks = [
            t for t in recent_tasks
            if t.status == TaskStatus.COMPLETED and t.duration is not None
        ]
        if len(completed_tasks) >= 5:
            durations = [t.duration for t in completed_tasks if t.duration]
            if durations:
                avg_duration = mean(durations)

                for task in completed_tasks[:3]:
                    if task.duration and task.duration > avg_duration * 5:
                        anomalies.append(
                            f"任务 '{task.description}' 耗时 "
                            f"{task.duration:.0f}秒，"
                            f"是平均 {avg_duration:.0f}秒 的 "
                            f"{task.duration / avg_duration:.1f} 倍"
                        )

        return anomalies

    # ── 今日汇总 ────────────────────────────────────────────

    def get_today_summary(self) -> Dict[str, Any]:
        """
        获取今日汇总信息

        Returns:
            dict: 包含总任务数、完成/失败/卡住数、费用、各 Agent 状态
        """
        stats = self._storage.get_task_stats_today()

        # 按 Agent 汇总费用
        today_tasks = self._storage.get_tasks_today()
        cost_by_agent: Dict[str, float] = {}
        for task in today_tasks:
            cost = task.estimated_cost or 0
            cost_by_agent[task.agent_name] = (
                cost_by_agent.get(task.agent_name, 0) + cost
            )

        return {
            "total_tasks": stats["total"],
            "completed": stats["completed"],
            "failed": stats["failed"],
            "stuck": stats["stuck"],
            "total_cost": stats["total_cost"],
            "cost_by_agent": cost_by_agent,
        }

    # ── 预算检查 ────────────────────────────────────────────

    def check_budget(self, cost: float, budget: float) -> bool:
        """
        检查是否超出预算

        Args:
            cost: 当前费用
            budget: 预算上限

        Returns:
            True 表示超出预算
        """
        if budget <= 0:
            return False
        return cost > budget
