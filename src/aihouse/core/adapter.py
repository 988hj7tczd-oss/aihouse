"""
Agent 适配器基类 — 所有 Agent 检测适配器必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from aihouse.core.models import AgentStatus, AgentTask


class AgentAdapter(ABC):
    """所有 Agent 适配器必须实现的抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent 显示名称，如 'Claude Code'"""
        ...

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Agent 类型标识，如 'claude_code'"""
        ...

    @abstractmethod
    def detect(self) -> bool:
        """
        检测本机是否安装了此 Agent

        Returns:
            True 表示已安装，False 表示未安装
        """
        ...

    @abstractmethod
    def get_status(self) -> AgentStatus:
        """
        获取 Agent 当前状态

        Returns:
            AgentStatus 对象

        Raises:
            RuntimeError: Agent 未运行或检测失败时抛出
        """
        ...

    def get_current_task(self) -> Optional[AgentTask]:
        """
        获取当前正在运行的任务（可选实现）

        Returns:
            AgentTask 对象，无运行任务则返回 None
        """
        return None

    def get_recent_tasks(self, limit: int = 20) -> List[AgentTask]:
        """
        获取最近任务列表（可选实现）

        Args:
            limit: 返回条数上限

        Returns:
            任务对象列表
        """
        return []
