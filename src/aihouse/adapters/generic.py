"""
通用 Agent 适配器 — 通过进程和文件系统信息推断 Agent 状态

适用于任何 AI Agent，不依赖具体日志格式。
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

from aihouse.core.adapter import AgentAdapter
from aihouse.core.models import AgentActivity, AgentStatus, AgentTask, TaskStatus

# ── 忽略的目录名 ─────────────────────────────────────────────
IGNORED_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".DS_Store"}


def find_process(process_name: str) -> List[Dict[str, Any]]:
    """
    查找进程中包含指定名称的进程

    使用 psutil.process_iter() 遍历进程，不区分大小写匹配
    进程名或命令行。

    Args:
        process_name: 要匹配的进程名关键字

    Returns:
        匹配到的进程列表，每项含 pid / name / create_time / cmdline
    """
    results: List[Dict[str, Any]] = []
    keyword_lower = process_name.lower()

    for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            info = proc.info
            name = (info.get("name") or "").lower()
            cmdline = " ".join(info.get("cmdline") or []).lower()

            if keyword_lower in name or keyword_lower in cmdline:
                results.append({
                    "pid": info["pid"],
                    "name": info.get("name") or "",
                    "create_time": info.get("create_time"),
                    "cmdline": info.get("cmdline") or [],
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return results


def check_recent_file_changes(directory: str,
                              threshold_seconds: int = 300) -> bool:
    """
    检查指定目录下是否有最近被修改的文件

    递归检查所有子目录，自动跳过 .git / node_modules / __pycache__ 等。

    Args:
        directory: 要检查的目录路径
        threshold_seconds: 时间阈值（秒），文件修改时间在此范围内算"最近"

    Returns:
        True 表示最近有文件变化（Agent 在工作）
        False 表示最近没有文件变化
    """
    dir_path = Path(directory).expanduser().resolve()
    if not dir_path.is_dir():
        return False

    cutoff = datetime.now().timestamp() - threshold_seconds

    try:
        for root, dirs, files in os.walk(dir_path):
            # 跳过忽略目录
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

            for name in files:
                if name == ".DS_Store":
                    continue
                file_path = Path(root) / name
                try:
                    mtime = file_path.stat().st_mtime
                    if mtime > cutoff:
                        return True
                except OSError:
                    continue
    except PermissionError:
        pass

    return False


class GenericAdapter(AgentAdapter):
    """
    通用适配器 — 适用于任何 AI Agent

    通过以下方式检测 Agent 状态：
    1. 进程检查：Agent 进程是否在运行
    2. 文件变化：Agent 工作目录最近是否有文件被修改
    3. 时间推断：根据进程启动时间和文件修改时间推断任务状态

    name 和 agent_type 作为类属性提供，子类可通过覆盖实现定制。
    """

    name = "通用模式"
    agent_type = "generic"

    def __init__(self, config: Optional[dict] = None) -> None:
        """
        初始化通用适配器

        Args:
            config: 配置字典，支持的字段：
                - name: Agent 显示名称（可选）
                - type: Agent 类型标识（可选）
                - process_name: 要监控的进程名关键字（可选）
                - work_dir: Agent 工作目录（可选）
                - stuck_threshold: 卡住阈值秒数（可选，默认 300）
        """
        config = config or {}
        self._process_name: str = config.get("process_name", "")
        self._work_dir: str = config.get("work_dir", "")
        self._stuck_threshold: int = config.get("stuck_threshold", 300)

        # 允许外部覆盖名称
        if "name" in config:
            self.name = config["name"]
        if "type" in config:
            self.agent_type = config["type"]

    def detect(self) -> bool:
        """
        通用模式永远可用

        Returns:
            True
        """
        return True

    def get_status(self) -> AgentStatus:
        """
        获取 Agent 当前状态

        判断逻辑：
        1. 如果配置了 process_name，用 psutil 查找进程
           - 进程存在 → 继续判断
           - 进程不存在 → activity = NOT_RUNNING
        2. 如果配置了 work_dir，检查最近文件修改时间
           - 有近期修改 → activity = ACTIVE
           - 无近期修改 → activity = IDLE（可能卡住/空闲）
        3. 如果 process_name + work_dir 都没有配置
           - 返回 UNKNOWN 状态
        4. 记录 PID、首次发现时间等信息

        Returns:
            AgentStatus 对象

        Raises:
            RuntimeError: 检测进程时出错
        """
        pid: Optional[int] = None
        create_time: Optional[float] = None
        activity: AgentActivity = AgentActivity.NOT_RUNNING

        # ── 进程检查 ──
        if self._process_name:
            try:
                procs = find_process(self._process_name)
            except Exception as e:
                raise RuntimeError(f"检测 Agent 进程失败: {e}")

            if procs:
                pid = procs[0]["pid"]
                create_time = procs[0].get("create_time")
                activity = AgentActivity.IDLE
            else:
                pid = None
                activity = AgentActivity.NOT_RUNNING

        # ── 文件变化检查 ──
        if self._work_dir and activity != AgentActivity.NOT_RUNNING:
            try:
                has_changes = check_recent_file_changes(
                    self._work_dir, self._stuck_threshold
                )
            except Exception:
                has_changes = False

            if has_changes:
                activity = AgentActivity.ACTIVE
            else:
                # 进程在运行但文件没变化 → 空闲或卡住
                activity = AgentActivity.IDLE

        # ── 没有配置任何检测方式 ──
        if not self._process_name and not self._work_dir:
            activity = AgentActivity.NOT_RUNNING

        last_seen: Optional[datetime] = None
        if create_time is not None:
            last_seen = datetime.fromtimestamp(create_time)

        return AgentStatus(
            agent_name=self.name,
            agent_type=self.agent_type,
            activity=activity,
            last_seen=last_seen or datetime.now(),
            tasks_today=0,
            total_cost_today=0.0,
            pid=pid,
        )

    def get_current_task(self) -> Optional[AgentTask]:
        """
        获取当前正在运行的任务（通用模式占位实现）

        通用模式无法获取具体任务描述，仅通过进程信息推断。
        如果进程在运行，返回占位任务。

        Returns:
            AgentTask 占位对象，进程未运行则返回 None
        """
        if not self._process_name:
            return None

        try:
            procs = find_process(self._process_name)
        except Exception:
            return None

        if not procs:
            return None

        create_time = procs[0].get("create_time")
        started_at = (
            datetime.fromtimestamp(create_time)
            if create_time else datetime.now()
        )

        return AgentTask(
            agent_name=self.name,
            agent_type=self.agent_type,
            task_id=f"generic_{procs[0]['pid']}_{int(started_at.timestamp())}",
            description="通用模式：进程运行中",
            project=self._work_dir,
            started_at=started_at,
            status=TaskStatus.RUNNING,
            session_id=f"pid_{procs[0]['pid']}",
        )
