"""
HTTP 服务检查 — 检测指定 URL 是否正常响应
"""

from typing import Any, Dict

import requests


def check_http(url: str, timeout: int = 10,
               expected_code: int = 200) -> Dict[str, Any]:
    """
    检查 HTTP 服务是否正常

    发送 GET 请求并检查响应状态码和延迟。

    Args:
        url: 目标 URL
        timeout: 超时秒数
        expected_code: 期望的 HTTP 状态码

    Returns:
        {
            "status": "ok" / "fail",
            "latency_ms": 响应延迟毫秒数,
            "status_code": 实际状态码,
            "error": 错误描述（成功时为空）
        }
    """
    result: Dict[str, Any] = {
        "status": "fail",
        "latency_ms": 0,
        "status_code": 0,
        "error": "",
    }

    try:
        resp = requests.get(url, timeout=timeout)
        result["latency_ms"] = int(resp.elapsed.total_seconds() * 1000)
        result["status_code"] = resp.status_code

        if resp.status_code == expected_code:
            result["status"] = "ok"
        else:
            result["error"] = (
                f"期望状态码 {expected_code}，实际 {resp.status_code}"
            )
    except requests.ConnectionError:
        result["error"] = "连接失败"
    except requests.Timeout:
        result["error"] = f"超时（{timeout}秒）"
    except requests.RequestException as e:
        result["error"] = str(e)

    return result
