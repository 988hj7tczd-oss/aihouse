"""
命令行入口模块 — 使用 click 提供 aihouse 命令及其子命令
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import click
import psutil
import requests

from aihouse import __version__
from aihouse.config import init_config, get_config_path, detect_agents, load_config
from aihouse.core.storage import Storage
from aihouse.core.scheduler import Scheduler
from aihouse.core.notifier import Notifier
from aihouse.server import Server

PID_FILE = os.path.expanduser("~/.aihouse/aihouse.pid")
LOG_FILE = os.path.expanduser("~/.aihouse/aihouse.log")
API_BASE = "http://127.0.0.1:9800"

LOGO = r"""
       ___________
      /           \
     /             \
    /  HH     HH    \
   /   HH     HH     \
  /    HHHHHHHHH      \
  \    HH     HH      /
   \   HH     HH     /
    \  HH     HH    /
     \_____________/

  AIHouse — AI Agent Monitor
"""


def _check_api_alive() -> bool:
    """检查 API 服务器是否在运行（通过连接端口 9800）"""
    try:
        req = urllib.request.Request("http://127.0.0.1:9800/api/health")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _kill_process(pid: int) -> None:
    """跨平台终止进程"""
    system = platform.system()
    if system == "Windows":
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
    else:
        try:
            os.kill(pid, 15)
            for _ in range(10):
                try:
                    os.kill(pid, 0)
                    time.sleep(0.5)
                except OSError:
                    break
        except OSError:
            pass


def daemon() -> None:
    """后台运行：启动调度器和 API 服务器"""
    config = load_config()
    storage = Storage()
    notifier = Notifier(config.get("notifications", []), storage)
    scheduler = Scheduler(storage, notifier, config)
    scheduler.start()
    server = Server(scheduler, storage, notifier)
    server.start()

    while True:
        time.sleep(10)


def _print_version(ctx: click.Context, param: click.Parameter, value: bool) -> None:
    """--version 回调：先打印 LOGO 再打印版本号"""
    if not value or ctx.resilient_parsing:
        return
    click.echo(click.style(LOGO, fg="blue"))
    click.echo(f"aihouse, version {__version__}")
    ctx.exit()


@click.group(invoke_without_command=True)
@click.option(
    "-V", "--version", is_flag=True, is_eager=True, expose_value=False,
    callback=_print_version, help="显示版本号",
)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """
    AIHouse — AI Agent 统一监控与管理平台

    运行 aihouse <command> 查看具体帮助，例如：

        aihouse init    初始化配置目录
        aihouse start   启动监控
        aihouse status  查看运行状态
    """
    if ctx.invoked_subcommand is None:
        click.echo(click.style(LOGO, fg="blue"))
        click.echo(ctx.get_help())


@cli.command()
def init() -> None:
    """初始化配置目录 ~/.aihouse/"""
    try:
        init_config()
        click.echo(f"配置目录已初始化: {get_config_path()}")
    except Exception as e:
        click.echo(f"初始化失败: {e}", err=True)
        raise click.Abort()


@cli.command()
def start() -> None:
    """启动后台守护进程"""
    if _check_api_alive():
        click.echo("AIHouse 已在运行中")
        return

    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)
            click.echo("AIHouse 已在运行中")
            return
        except (OSError, ValueError):
            os.remove(PID_FILE)

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    proc = subprocess.Popen(
        [sys.executable, "-c",
         "from aihouse.cli import daemon; daemon()"],
        stdout=open(LOG_FILE, "a"),
        stderr=subprocess.STDOUT,
    )

    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))

    click.echo(f"AIHouse 已启动 (PID: {proc.pid})")


@cli.command()
def stop() -> None:
    """停止后台守护进程"""
    if not _check_api_alive() and not os.path.exists(PID_FILE):
        click.echo("AIHouse 未在运行")
        return

    if _check_api_alive():
        try:
            requests.post(f"{API_BASE}/shutdown", timeout=3)
        except Exception:
            pass

    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            _kill_process(pid)
        except (OSError, ValueError):
            pass
        os.remove(PID_FILE)

    click.echo("AIHouse 已停止")


@cli.command()
def status() -> None:
    """查看运行状态"""
    if not _check_api_alive():
        click.echo("未启动")
        return

    try:
        resp = requests.get(f"{API_BASE}/api/health", timeout=3)
        data = resp.json()
        version = data.get("version", "?")
    except Exception:
        version = "?"

    try:
        resp = requests.get(f"{API_BASE}/api/status", timeout=3)
        data = resp.json()
        agents = data.get("agents", [])
        summary = data.get("summary", {})
    except Exception:
        agents = []
        summary = {}

    click.echo(f"AIHouse 运行中 (v{version})")
    click.echo(f"  Agent 数: {summary.get('total', 0)}")

    for agent in agents:
        name = agent.get("name", "?")
        activity = agent.get("activity", "?")
        task = agent.get("current_task")
        task_info = f" 当前任务: {task['description']}" if task else ""
        click.echo(f"  {name:12s}  {activity:12s}{task_info}")


@cli.command()
@click.option("--limit", default=20, type=int, help="返回条数上限")
@click.option("--agent", default=None, type=str, help="按 Agent 类型筛选")
def tasks(limit: int, agent: str | None) -> None:
    """查看最近任务历史"""
    db_path = os.path.expanduser("~/.aihouse/aihouse.db")
    if not os.path.exists(db_path):
        click.echo("暂无任务数据（数据库不存在）")
        return

    try:
        storage = Storage(db_path)
        task_list = storage.get_recent_tasks(
            agent_type=agent, limit=limit
        )
    except Exception as e:
        click.echo(f"读取任务失败: {e}", err=True)
        return

    if not task_list:
        click.echo("暂无任务记录")
        return

    for t in task_list:
        date_str = t.started_at.strftime("%m-%d %H:%M")
        duration_str = f"{t.duration:.0f}s" if t.duration is not None else "-"
        click.echo(
            f"  {date_str} | {t.agent_name:12s} | {duration_str:>6s} | "
            f"{t.status.value:10s} | {t.description[:50]}"
        )


@cli.command()
def log() -> None:
    """查看 AIHouse 运行日志（最后 50 行）"""
    if not os.path.exists(LOG_FILE):
        click.echo("日志文件不存在")
        return

    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        tail = "".join(lines[-50:])
        click.echo(tail)
    except Exception as e:
        click.echo(f"读取日志失败: {e}", err=True)


@cli.command()
def restart() -> None:
    """重启 AIHouse 守护进程"""
    import subprocess as sp
    import sys as _sys

    if _check_api_alive() or os.path.exists(PID_FILE):
        click.echo("正在停止...")
        if _check_api_alive():
            try:
                requests.post(f"{API_BASE}/shutdown", timeout=3)
            except Exception:
                pass
        if os.path.exists(PID_FILE):
            try:
                with open(PID_FILE) as f:
                    pid = int(f.read().strip())
                _kill_process(pid)
            except (OSError, ValueError):
                pass
            os.remove(PID_FILE)
        time.sleep(2)
    else:
        click.echo("AIHouse 未在运行，直接启动")

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    proc = sp.Popen(
        [_sys.executable, "-c", "from aihouse.cli import daemon; daemon()"],
        stdout=open(LOG_FILE, "a"),
        stderr=sp.STDOUT,
    )
    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))
    click.echo(f"AIHouse 已重启 (PID: {proc.pid})")


@cli.command()
def detect() -> None:
    """检测本机已安装的 Agent"""
    agents = detect_agents()
    for agent in agents:
        status_text = "✓ 已安装" if agent["installed"] else "✗ 未安装"
        click.echo(f"  {agent['name']:12s}  {status_text}")


@cli.command()
def config() -> None:
    """打开配置文件"""
    config_path = get_config_path()
    if config_path.exists():
        click.echo(f"配置文件路径: {config_path}")
    else:
        click.echo("配置文件不存在，请先运行 aihouse init")


@cli.command()
def desktop() -> None:
    """启动 AIHouse 桌面端（自动启动后端）"""
    # 确保后端在运行
    if not _is_backend_running():
        click.echo("后端未运行，正在启动...")
        try:
            config = load_config()
            storage = Storage()
            notifier_obj = Notifier(config.get("notifications", []), storage)
            scheduler_obj = Scheduler(storage, notifier_obj, config)
            scheduler_obj.start()
            server_obj = Server(scheduler_obj, storage, notifier_obj)
            server_obj.start()
            click.echo("后端已启动")
        except Exception as e:
            click.echo(f"启动后端失败: {e}", err=True)
            click.echo("请先运行 aihouse start")
            raise click.Abort()

    binary = os.path.expanduser(
        "~/Projects/aihouse/desktop/src-tauri/target/release/aihouse"
    )

    if not os.path.exists(binary):
        click.echo("桌面端未编译，正在编译（首次需要 2-5 分钟）...")
        click.echo("cd desktop && npm run tauri build")
        click.echo("编译完成后再次运行 aihouse desktop")
        return

    click.echo("启动桌面端...")
    subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@cli.command()
@click.argument("agent_type", required=False)
def diagnose(agent_type: str | None = None) -> None:
    """诊断适配器状态，排查为什么读不到 Agent 数据"""
    check_agents = detect_agents()

    if agent_type:
        target = [a for a in check_agents if a["type"] == agent_type]
        if not target:
            click.echo(f"未找到 Agent 类型: {agent_type}")
            click.echo(f"可用的类型: {', '.join(a['type'] for a in check_agents)}")
            return
        _diagnose_one(target[0])
    else:
        click.echo(f"共检测 {len(check_agents)} 个 Agent:\n")
        for agent in check_agents:
            _diagnose_one(agent)
            click.echo("")


def _diagnose_one(agent: dict) -> None:
    """诊断单个 Agent"""
    name = agent["name"]
    agent_type = agent["type"]
    installed = agent["installed"]
    category = agent.get("category", "通用")
    icon = "✅" if installed else "⬜"

    click.echo(f"{icon} {name} ({agent_type}, {category} Agent)")

    if not installed:
        click.echo(f"   状态: 未安装（通过 keyword/dir 均未检测到）")
        return

    from aihouse.core.scheduler import load_adapter
    adapter = load_adapter(agent_type)

    from aihouse.config import KNOWN_AGENTS
    agent_cfg = next((a for a in KNOWN_AGENTS if a["name"] == name), {})
    keywords = agent_cfg.get("keywords", [agent_type])

    pid = None
    proc_found = False
    for kw in keywords:
        for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
            try:
                combined = (
                    f"{proc.info.get('name','')} "
                    f"{' '.join(proc.info.get('cmdline') or [])}"
                ).lower()
                if kw.lower() in combined:
                    pid = proc.info["pid"]
                    proc_found = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if proc_found:
            break

    if pid:
        try:
            p = psutil.Process(pid)
            click.echo(f"   PID: {pid} (已运行 {int(time.time()-p.create_time())}s)")
        except Exception:
            click.echo(f"   PID: {pid}")
    else:
        click.echo(f"   进程: 未检测到")

    for kw in keywords:
        which_result = shutil.which(kw)
        click.echo(f"   binary: {kw:15s} → {'✅ ' + which_result if which_result else '❌ 未找到'}")

    for d in agent_cfg.get("dirs", []):
        p = Path(d).expanduser()
        if p.exists():
            size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else p.stat().st_size
            size_str = f"{size/1024/1024:.0f}MB" if size > 1024*1024 else f"{size/1024:.0f}KB" if size > 1024 else f"{size}B"
            click.echo(f"   目录: {str(p):35s} ✅ ({size_str})")
        else:
            click.echo(f"   目录: {str(p):35s} ❌ 不存在")

    if adapter:
        try:
            status = adapter.get_status()
            click.echo(f"   适配器状态: {status.activity.value}")
            if status.current_task:
                click.echo(f"   当前任务: {status.current_task.description[:60]}")
        except Exception as e:
            click.echo(f"   适配器状态: ❌ {e}")
    else:
        click.echo(f"   适配器: 未加载")


def _is_backend_running() -> bool:
    """检查后端是否在运行（API 检测 + PID 文件兜底）"""
    if _check_api_alive():
        return True
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
        except (OSError, ValueError):
            os.remove(PID_FILE)
    return False
