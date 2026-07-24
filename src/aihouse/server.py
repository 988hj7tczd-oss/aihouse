"""
Flask REST API 服务器 — 为桌面端和 CLI 提供数据接口
"""

import threading
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, request
from flask_cors import CORS

from aihouse import __version__
from aihouse.core.analyzer import Analyzer
from aihouse.core.models import AgentActivity, AgentStatus, AgentTask

SENSITIVE_FIELD_KEYWORDS = {"key", "token", "password", "secret", "auth"}


class Server:
    """
    Flask REST API 服务器

    为桌面端和 CLI 提供数据接口。
    默认端口 9800，避免跟常用端口冲突。
    """

    def __init__(self, scheduler: Any, storage: Any, notifier: Any) -> None:
        """
        初始化 API 服务器

        Args:
            scheduler: Scheduler 实例
            storage: Storage 实例
            notifier: Notifier 实例
        """
        self._scheduler: Any = scheduler
        self._storage: Any = storage
        self._notifier: Any = notifier
        self._analyzer: Analyzer = Analyzer(storage, {}) if storage else None
        self._thread: Optional[threading.Thread] = None
        self._flask: Flask = Flask(__name__)
        CORS(self._flask)
        self._register_routes()

    # ── 生命周期 ────────────────────────────────────────────

    def start(self, host: str = "127.0.0.1", port: int = 9800) -> None:
        """
        启动 Flask 服务器（后台线程）

        Args:
            host: 监听地址，默认仅本地访问
            port: 监听端口
        """
        self._thread = threading.Thread(
            target=self._flask.run,
            kwargs={"host": host, "port": port, "debug": False, "use_reloader": False},
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """停止服务器"""
        import requests as req
        try:
            req.post("http://127.0.0.1:9800/shutdown", timeout=1)
        except Exception:
            pass

    # ── 路由注册 ────────────────────────────────────────────

    def _register_routes(self) -> None:
        """注册所有 API 路由"""

        # ── Agent 状态 ──

        @self._flask.route("/api/status")
        def get_all_status():
            """获取所有 Agent 的当前状态"""
            agents_data: List[Dict[str, Any]] = []

            if self._scheduler:
                statuses = self._scheduler.get_all_statuses()
                for name, status in statuses.items():
                    agents_data.append(self._status_to_dict(status))

            return jsonify({
                "agents": agents_data,
                "summary": self._compute_summary(agents_data),
            })

        @self._flask.route("/api/status/<agent_type>")
        def get_agent_status(agent_type):
            """获取指定 Agent 的详细信息"""
            if not self._scheduler:
                return jsonify({"error": "scheduler not available"}), 503

            adapter = self._scheduler.get_adapter(agent_type)
            if adapter is None:
                return jsonify({"error": f"adapter not found: {agent_type}"}), 404

            try:
                status = adapter.get_status()
            except Exception as e:
                return jsonify({"error": str(e)}), 500

            result = self._status_to_dict(status)
            result["recent_tasks"] = [
                self._task_to_dict(t)
                for t in adapter.get_recent_tasks(limit=20)
            ]
            return jsonify(result)

        # ── 任务历史 ──

        @self._flask.route("/api/tasks")
        def get_tasks():
            """获取最近任务列表"""
            limit = request.args.get("limit", 20, type=int)
            agent = request.args.get("agent", None)

            if not self._storage:
                return jsonify({"tasks": []})

            tasks = self._storage.get_recent_tasks(
                agent_type=agent, limit=limit
            )
            return jsonify({
                "tasks": [self._task_to_dict(t) for t in tasks]
            })

        @self._flask.route("/api/tasks/today")
        def get_tasks_today():
            """获取今日任务汇总"""
            if not self._storage:
                return jsonify({})

            if self._analyzer:
                summary = self._analyzer.get_today_summary()
            else:
                stats = self._storage.get_task_stats_today()
                summary = {**stats, "cost_by_agent": {}}

            return jsonify(summary)

        @self._flask.route("/api/tasks/<task_id>")
        def get_task_detail(task_id):
            """获取单个任务详情"""
            if not self._storage:
                return jsonify({"error": "storage not available"}), 503

            task = self._storage.get_task(task_id)
            if task is None:
                return jsonify({"error": "task not found"}), 404

            return jsonify(self._task_to_dict(task))

        # ── 控制 ──

        @self._flask.route("/api/control/refresh")
        def refresh_all():
            """立即触发一次全面检查"""
            if self._scheduler:
                self._scheduler.check_all()
                return jsonify({"status": "ok", "message": "检查已触发"})
            return jsonify({"error": "scheduler not available"}), 503

        # ── 配置 ──

        @self._flask.route("/api/config")
        def get_config():
            """
            返回当前配置（过滤掉敏感字段）
            """
            from aihouse.config import load_config
            try:
                config = load_config()
                safe = self._filter_sensitive(config)
                return jsonify(safe)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # ── 服务检查 ──

        @self._flask.route("/api/services")
        def get_services():
            """执行所有配置的 services 检查，返回结果列表"""
            from aihouse.config import load_config as _load_config
            try:
                cfg = _load_config()
            except Exception:
                return jsonify({"services": []})

            results: List[Dict[str, Any]] = []
            for svc in cfg.get("services", []):
                svc_type = svc.get("type", "")
                name = svc.get("name", "")
                if svc_type == "api_cost":
                    from aihouse.services.api_cost import query_cost
                    provider = svc.get("provider", "")
                    api_key = svc.get("api_key", "")
                    if not api_key or api_key == "***":
                        results.append({"name": name, "type": svc_type, "error": "API Key 未配置"})
                    else:
                        try:
                            cost = query_cost(provider, api_key)
                            results.append({"name": name, "type": svc_type, **cost})
                        except Exception as e:
                            results.append({"name": name, "type": svc_type, "error": str(e)})
                elif svc_type == "http":
                    from aihouse.services.http_check import check_http
                    url = svc.get("url", "")
                    try:
                        check = check_http(url)
                        results.append({"name": name, "type": svc_type, **check})
                    except Exception as e:
                        results.append({"name": name, "type": svc_type, "error": str(e)})

            return jsonify({"services": results})

        @self._flask.route("/api/services/cost")
        def get_services_cost():
            """查询今日费用汇总"""
            from aihouse.config import load_config as _load_config
            try:
                cfg = _load_config()
            except Exception:
                return jsonify({"costs": [], "total_today": 0.0})

            costs: List[Dict[str, Any]] = []
            total = 0.0
            for svc in cfg.get("services", []):
                if svc.get("type") != "api_cost":
                    continue
                from aihouse.services.api_cost import query_cost
                provider = svc.get("provider", "")
                api_key = svc.get("api_key", "")
                if not api_key or api_key == "***":
                    continue
                try:
                    cost = query_cost(provider, api_key)
                    today = cost.get("today", 0.0)
                    total += today
                    costs.append({
                        "name": svc.get("name", ""),
                        "provider": provider,
                        "today": today,
                        "currency": cost.get("currency", "USD"),
                    })
                except Exception:
                    continue

            return jsonify({"costs": costs, "total_today": round(total, 4)})

        # ── 健康检查 ──

        @self._flask.route("/api/health")
        def health():
            return jsonify({
                "status": "ok",
                "version": __version__,
            })

        # ── 内部关闭 ──

        @self._flask.route("/shutdown", methods=["POST"])
        def shutdown():
            import os
            os._exit(0)

    # ── 工具方法 ────────────────────────────────────────────

    @staticmethod
    def _status_to_dict(status: AgentStatus) -> Dict[str, Any]:
        """将 AgentStatus 转为可序列化的字典"""
        return {
            "name": status.agent_name,
            "type": status.agent_type,
            "activity": status.activity.value,
            "current_task": (
                Server._task_to_dict(status.current_task)
                if status.current_task else None
            ),
            "last_task": (
                Server._task_to_dict(status.last_task)
                if status.last_task else None
            ),
            "last_seen": (
                status.last_seen.isoformat() if status.last_seen else None
            ),
            "tasks_today": status.tasks_today,
            "total_cost_today": status.total_cost_today,
            "pid": status.pid,
        }

    @staticmethod
    def _task_to_dict(task: AgentTask) -> Dict[str, Any]:
        """将 AgentTask 转为可序列化的字典"""
        return {
            "agent_name": task.agent_name,
            "agent_type": task.agent_type,
            "task_id": task.task_id,
            "description": task.description,
            "project": task.project,
            "status": task.status.value,
            "started_at": task.started_at.isoformat(),
            "completed_at": (
                task.completed_at.isoformat() if task.completed_at else None
            ),
            "duration": task.duration,
            "output_summary": task.output_summary,
            "files_changed": task.files_changed,
            "error_message": task.error_message,
            "estimated_cost": task.estimated_cost,
            "estimated_tokens": task.estimated_tokens,
            "api_calls": task.api_calls,
            "session_id": task.session_id,
        }

    @staticmethod
    def _compute_summary(agents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算总体汇总和颜色状态

        颜色规则：
        - 有 Agent 失败/错误 → red
        - 有 Agent 卡住/警告 → yellow
        - 所有正常 → green
        - 全部空闲 → blue
        """
        total = len(agents)
        counts: Dict[str, int] = {}
        has_error = False
        has_warning = False
        all_idle = True

        for agent in agents:
            activity = agent.get("activity", "not_running")
            counts[activity] = counts.get(activity, 0) + 1

            if activity in ("error",):
                has_error = True
            if activity in ("stuck", "busy"):
                has_warning = True
            if activity != "idle":
                all_idle = False

        if has_error:
            color = "red"
        elif has_warning:
            color = "yellow"
        elif all_idle and total > 0:
            color = "blue"
        else:
            color = "green"

        return {
            "total": total,
            "color": color,
            **counts,
        }

    @staticmethod
    def _filter_sensitive(data: Any, depth: int = 0) -> Any:
        """
        递归过滤敏感字段

        所有键名包含 key / token / password / secret / auth 的字段值
        都会被替换为 '***'。

        Args:
            data: 要过滤的数据
            depth: 当前递归深度（防止无限递归）

        Returns:
            过滤后的数据
        """
        if depth > 10:
            return data

        if isinstance(data, dict):
            result: Dict[str, Any] = {}
            for k, v in data.items():
                if any(word in k.lower() for word in SENSITIVE_FIELD_KEYWORDS):
                    result[k] = "***"
                else:
                    result[k] = Server._filter_sensitive(v, depth + 1)
            return result

        if isinstance(data, list):
            return [Server._filter_sensitive(item, depth + 1) for item in data]

        return data
