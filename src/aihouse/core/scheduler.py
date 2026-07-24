import importlib
from datetime import datetime
from typing import Any, Dict, Optional

from apscheduler.schedulers.background import BackgroundScheduler

from aihouse.core.models import AgentActivity, AgentStatus, TaskStatus
from aihouse.core.storage import Storage


BUILTIN_ADAPTERS: Dict[str, str] = {
    "generic": "aihouse.adapters.generic.GenericAdapter",
    "hermes": "aihouse.adapters.hermes.HermesAdapter",
    "claude_code": "aihouse.adapters.claude_code.ClaudeCodeAdapter",
    "cursor": "aihouse.adapters.cursor.CursorAdapter",
    "codex": "aihouse.adapters.codex.CodexAdapter",
    "opencode": "aihouse.adapters.opencode.OpenCodeAdapter",
    "pi": "aihouse.adapters.pi.PiAdapter",
    "openclaw": "aihouse.adapters.openclaw.OpenClawAdapter",
    "kilo_code": "aihouse.adapters.kilo_code.KiloCodeAdapter",
    "cline": "aihouse.adapters.cline.ClineAdapter",
}


def load_adapter(agent_type: str) -> Optional[Any]:
    module_path = BUILTIN_ADAPTERS.get(agent_type)
    if module_path is None:
        return None

    try:
        module_name, class_name = module_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        adapter_class = getattr(module, class_name)
        adapter = adapter_class()
        if adapter.detect():
            return adapter
    except Exception:
        pass

    return None


class Scheduler:

    def __init__(self, storage: Storage, notifier, config: dict) -> None:
        self._storage: Storage = storage
        self._notifier = notifier
        self._config: dict = config
        self._poll_interval: int = (
            config.get("settings", {}).get("poll_interval", 10)
        )
        self._scheduler: BackgroundScheduler = BackgroundScheduler()
        self._adapter_cache: Dict[str, Any] = {}

        for agent_cfg in config.get("agents", []):
            if agent_cfg.get("enabled", True):
                agent_type = agent_cfg["type"]
                if agent_type not in self._adapter_cache:
                    adapter = load_adapter(agent_type)
                    if adapter is not None:
                        self._adapter_cache[agent_type] = adapter

        self._scheduler.add_job(
            self.check_all,
            "interval",
            seconds=self._poll_interval,
            id="check_all",
            replace_existing=True,
        )

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=True)

    def is_running(self) -> bool:
        return self._scheduler.running

    def check_all(self) -> None:
        for agent_cfg in self._config.get("agents", []):
            if not agent_cfg.get("enabled", True):
                continue

            agent_type = agent_cfg["type"]
            adapter = self._adapter_cache.get(agent_type)
            if adapter is None:
                continue

            try:
                status: AgentStatus = adapter.get_status()
            except Exception:
                self._storage.save_snapshot(
                    agent_name=agent_cfg["name"],
                    agent_type=agent_type,
                    activity=AgentActivity.NOT_RUNNING.value,
                )
                continue

            pid = status.pid
            self._storage.save_snapshot(
                agent_name=status.agent_name,
                agent_type=status.agent_type,
                activity=status.activity.value,
                pid=pid,
            )

            if status.current_task is not None:
                self._storage.save_task(status.current_task)

            task = status.current_task
            if task is not None:
                if task.status == TaskStatus.STUCK:
                    self._storage.save_notification(
                        event_type="agent_stuck",
                        title=f"{status.agent_name} 任务卡住",
                        message=(
                            f"任务 '{task.description}' 已运行超过预期时间"
                        ),
                        related_agent=status.agent_name,
                    )
                    if self._notifier:
                        self._notifier.notify(
                            "agent_stuck",
                            f"{status.agent_name} 任务卡住",
                            task.description,
                            status.agent_name,
                        )
                elif task.status == TaskStatus.FAILED:
                    self._storage.save_notification(
                        event_type="task_failed",
                        title=f"{status.agent_name} 任务失败",
                        message=(
                            f"任务 '{task.description}' 失败: "
                            f"{task.error_message}"
                        ),
                        related_agent=status.agent_name,
                    )
                    if self._notifier:
                        self._notifier.notify(
                            "task_failed",
                            f"{status.agent_name} 任务失败",
                            task.error_message,
                            status.agent_name,
                        )

    def get_all_statuses(self) -> Dict[str, AgentStatus]:
        results: Dict[str, AgentStatus] = {}
        for agent_type, adapter in self._adapter_cache.items():
            try:
                status = adapter.get_status()
                results[status.agent_name] = status
            except Exception:
                continue
        return results

    def get_adapter(self, agent_type: str) -> Optional[Any]:
        return self._adapter_cache.get(agent_type)
