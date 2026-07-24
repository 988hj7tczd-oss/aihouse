"""
通知管理器 — 支持 PushPlus、桌面通知、Bark 多渠道推送
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from aihouse.core.storage import Storage

# 去重时间窗口（秒）
DEDUP_WINDOW_SECONDS = 300


class Notifier:
    """
    通知管理器

    支持的通知渠道：
    - pushplus: 微信推送
    - desktop: 桌面通知（通过系统通知栏）
    - bark: iOS 推送

    配置示例 (config.yaml):
        notifications:
          - type: pushplus
            token: "${PUSHPLUS_TOKEN}"
            events:
              - task_completed
              - task_failed
              - agent_stuck
          - type: desktop
            events:
              - task_failed
              - agent_stuck
    """

    def __init__(self, config: List[dict], storage: Storage) -> None:
        """
        初始化通知管理器

        Args:
            config: notifications 配置列表
            storage: Storage 实例，用于记录已发送通知（去重）
        """
        self._config: List[dict] = config
        self._storage: Storage = storage

    def notify(self, event_type: str, title: str, message: str = "",
               agent_name: str = "") -> None:
        """
        发送通知

        流程：
        1. 检查 event_type 是否有对应的通知渠道配置
        2. 去重检测（同一告警 5 分钟内不重复推送）
        3. 遍历匹配的渠道并调用对应的发送方法
        4. 记录发送结果到 storage

        Args:
            event_type: 事件类型（task_completed / task_failed / agent_stuck / budget_exceeded）
            title: 通知标题
            message: 通知正文
            agent_name: 相关 Agent 名称
        """
        if not self._should_notify(event_type, title):
            return

        for channel in self._config:
            events = channel.get("events", [])
            if event_type not in events:
                continue

            channel_type = channel.get("type", "")
            sent = False

            if channel_type == "pushplus":
                token = channel.get("token", "")
                if token:
                    self._send_pushplus(token, title, message)
                    sent = True

            elif channel_type == "desktop":
                self._send_desktop(title, message)
                sent = True

            elif channel_type == "bark":
                key = channel.get("key", "")
                if key:
                    self._send_bark(key, title, message)
                    sent = True

            if sent:
                self._storage.save_notification(
                    event_type=event_type,
                    title=title,
                    message=message,
                    related_agent=agent_name if agent_name else None,
                )

    # ── 去重 ────────────────────────────────────────────────

    def _should_notify(self, event_type: str, title: str) -> bool:
        """
        判断是否应该发送这条通知（去重）

        规则：
        1. 同一事件类型 + 同一标题，5 分钟内不重复发送
        2. 查询 storage 中的最近通知记录
        3. 有匹配记录 → 跳过

        Args:
            event_type: 事件类型
            title: 通知标题

        Returns:
            True 表示应该发送，False 表示跳过
        """
        # 没有配置任何通知渠道
        if not self._config:
            return False

        recent = self._storage.get_recent_notifications(limit=50)
        now = datetime.now()

        for record in recent:
            record_time_str = record.get("created_at", "")
            if not record_time_str:
                continue
            try:
                record_time = datetime.fromisoformat(record_time_str)
            except (ValueError, TypeError):
                continue

            if (record.get("type") == event_type
                    and record.get("title") == title
                    and (now - record_time).total_seconds() < DEDUP_WINDOW_SECONDS):
                return False

        return True

    # ── PushPlus ────────────────────────────────────────────

    def _send_pushplus(self, token: str, title: str, content: str) -> None:
        """
        通过 PushPlus 发送微信推送

        API: POST https://www.pushplus.plus/send

        Args:
            token: PushPlus 令牌
            title: 推送标题
            content: 推送内容
        """
        try:
            resp = requests.post(
                "https://www.pushplus.plus/send",
                json={
                    "token": token,
                    "title": title,
                    "content": content,
                    "template": "txt",
                },
                timeout=10,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"PushPlus 推送失败: {e}")

    # ── 桌面通知 ────────────────────────────────────────────

    def _send_desktop(self, title: str, message: str) -> None:
        """
        发送桌面通知

        使用 plyer 库实现跨平台桌面通知。

        Args:
            title: 通知标题
            message: 通知内容
        """
        try:
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                app_name="AIHouse",
                timeout=5,
            )
        except ImportError:
            raise RuntimeError("桌面通知需要 plyer 库: pip install plyer")
        except Exception as e:
            raise RuntimeError(f"桌面通知失败: {e}")

    # ── Bark ────────────────────────────────────────────────

    def _send_bark(self, key: str, title: str, body: str) -> None:
        """
        发送 iOS 推送（Bark App）

        使用 POST 请求避免 URL 长度限制。

        API: POST https://api.day.app/push

        Args:
            key: Bark 设备密钥
            title: 推送标题
            body: 推送内容
        """
        try:
            resp = requests.post(
                "https://api.day.app/push",
                json={
                    "device_key": key,
                    "title": title,
                    "body": body,
                    "level": "active",
                },
                timeout=10,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Bark 推送失败: {e}")
