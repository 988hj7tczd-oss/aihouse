"""
数据模型定义 — Agent 任务、状态、活动类型等核心数据结构
"""

from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional


class TaskStatus(Enum):
    """任务运行状态"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STUCK = "stuck"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class AgentActivity(Enum):
    """Agent 当前活动状态"""
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    NOT_RUNNING = "not_running"


@dataclass
class AgentTask:
    """
    一个 Agent 任务记录

    Attributes:
        agent_name: Agent 显示名称
        agent_type: Agent 类型标识 (claude_code / cursor / ...)
        task_id: 唯一任务 ID
        description: 任务描述
        project: 项目路径
        started_at: 任务开始时间
        completed_at: 任务完成时间
        duration: 任务持续秒数
        status: 任务状态
        output_summary: 输出摘要
        files_changed: 变更的文件列表
        error_message: 错误信息
        estimated_cost: 估算费用 (USD)
        estimated_tokens: 估算 Token 数
        context_window: 当前上下文窗口使用量
        model_name: 使用的模型名
        tags: 任务标签
        api_calls: API 调用次数
        session_id: 会话 ID
    """
    agent_name: str
    agent_type: str
    task_id: str
    description: str
    project: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    status: TaskStatus = TaskStatus.RUNNING
    output_summary: str = ""
    files_changed: list[str] = field(default_factory=list)
    error_message: str = ""
    estimated_cost: Optional[float] = None
    estimated_tokens: Optional[int] = None
    context_window: Optional[int] = None
    model_name: str = ""
    tags: list[str] = field(default_factory=list)
    api_calls: int = 0
    session_id: str = ""


@dataclass
class AgentStatus:
    """
    Agent 当前状态快照

    Attributes:
        agent_name: Agent 显示名称
        agent_type: Agent 类型标识
        activity: 当前活动状态
        current_task: 当前正在执行的任务
        last_task: 上一个已完成的任务
        last_seen: 最后活跃时间
        tasks_today: 今日任务数
        tasks_this_week: 本周任务数
        total_cost_today: 今日总费用
        pid: 进程 ID
        memory_mb: 内存占用 (MB)
        cpu_percent: CPU 占用百分比
        version: Agent 版本号
    """
    agent_name: str
    agent_type: str
    activity: AgentActivity
    current_task: Optional[AgentTask] = None
    last_task: Optional[AgentTask] = None
    last_seen: Optional[datetime] = None
    tasks_today: int = 0
    tasks_this_week: int = 0
    total_cost_today: float = 0.0
    pid: Optional[int] = None
    memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    version: str = ""
