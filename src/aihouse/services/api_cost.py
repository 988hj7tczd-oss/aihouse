"""
AI 费用查询服务

支持 DeepSeek 和 OpenAI 的 API 费用查询。
"""

from datetime import date
from typing import Any, Dict

import requests


def query_cost(provider: str, api_key: str) -> Dict[str, Any]:
    """
    查询指定提供商今日的 API 费用

    Args:
        provider: 提供商名称 (deepseek / openai)
        api_key: API Key

    Returns:
        {"today": 今日费用, "currency": "USD", "error": ""}

    Raises:
        ValueError: 不支持的提供商
    """
    if provider == "deepseek":
        return _query_deepseek(api_key)
    elif provider == "openai":
        return _query_openai(api_key)
    else:
        raise ValueError(f"不支持的提供商: {provider}")


def check_api_key(provider: str, api_key: str) -> bool:
    """
    验证 API Key 是否有效

    Args:
        provider: 提供商名称
        api_key: API Key

    Returns:
        True 表示有效
    """
    try:
        if provider == "deepseek":
            resp = requests.get(
                "https://api.deepseek.com/user/balance",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            return resp.status_code == 200
        elif provider == "openai":
            resp = requests.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            return resp.status_code == 200
        else:
            return False
    except requests.RequestException:
        return False


def _query_deepseek(api_key: str) -> Dict[str, Any]:
    """查询 DeepSeek 费用"""
    try:
        resp = requests.get(
            "https://api.deepseek.com/user/balance",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if resp.status_code != 200:
            return {"today": 0.0, "currency": "USD", "error": f"HTTP {resp.status_code}"}
        data = resp.json()
        return {
            "today": float(data.get("total_balance", 0)),
            "currency": "USD",
            "error": "",
        }
    except requests.RequestException as e:
        return {"today": 0.0, "currency": "USD", "error": str(e)}


def _query_openai(api_key: str) -> Dict[str, Any]:
    """查询 OpenAI 费用"""
    today = date.today().isoformat()
    try:
        resp = requests.get(
            f"https://api.openai.com/v1/usage?date={today}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if resp.status_code != 200:
            return {"today": 0.0, "currency": "USD", "error": f"HTTP {resp.status_code}"}
        data = resp.json()
        return {
            "today": float(data.get("total_usage", 0)),
            "currency": "USD",
            "error": "",
        }
    except requests.RequestException as e:
        return {"today": 0.0, "currency": "USD", "error": str(e)}
