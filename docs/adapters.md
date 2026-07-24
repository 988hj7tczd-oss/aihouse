# 适配器体系

AIHouse 通过适配器（Adapter）机制支持不同的 AI Agent。每个适配器知道如何读取对应 Agent 的状态。

---

## 工作原理

```
AIHouse 调度器
      │
      ▼
适配器管理器 → 遍历所有已注册的适配器
      │
      ├─ 调用 detect()     → 这个 Agent 安装了吗？
      ├─ 调用 get_status() → 当前在干什么？
      └─ 调用 get_current_task() → 正在跑什么任务？
```

---

## 内置适配器

| 适配器 | 类型标识 | 优先级 | 说明 |
|--------|---------|--------|------|
| 通用模式 | `generic` | 兜底 | 通过进程 + 文件变化判断 |
| Claude Code | `claude_code` | P0 | 读日志 + 进程 |
| Cursor | `cursor` | P1 | 读日志 + 进程 |
| Codex CLI | `codex` | P1 | 进程监控 |
| OpenCode | `opencode` | P1 | 进程监控 |
| Hermes | `hermes` | P2 | 读会话数据库 |

---

## 适配器接口

所有适配器都继承自 `AgentAdapter` 基类：

```python
class AgentAdapter:
    """所有 Agent 适配器必须实现的接口"""

    def detect(self) -> bool:
        """检测本机是否安装了此 Agent"""
        pass

    def get_status(self) -> AgentStatus:
        """获取 Agent 当前状态"""
        pass

    def get_current_task(self) -> AgentTask | None:
        """获取当前运行的任务（可选）"""
        pass

    def get_recent_tasks(self, limit=20) -> list[AgentTask]:
        """获取最近任务（可选）"""
        pass
```

---

## 通用模式（兜底方案）

通用模式适用于**任何** AI Agent，不依赖特定的日志格式。

**监控方式：**
1. **进程检查**：用 psutil 查找指定名称的进程
2. **文件变化**：检查工作目录最近是否有文件被修改

**配置示例：**

```yaml
agents:
  - name: "我的自定义 Agent"
    type: generic
    process_name: "my-agent"
    work_dir: "~/my-project"
    stuck_threshold: 300
```

**优势**：任何 Agent 都有进程和文件系统，所以这个方法永远不会失效。

**局限**：无法获取具体的任务描述和执行结果。

---

## 开发自定义适配器

如果你想监控 AIHouse 尚未支持的 Agent，可以自己写适配器：

### 步骤

```python
# 1. 在 adapters/ 下新建文件 my_agent.py

from aihouse.core.adapter import AgentAdapter
from aihouse.core.models import AgentStatus, AgentTask

class MyAgentAdapter(AgentAdapter):
    name = "我的 Agent"
    agent_type = "my_agent"

    def detect(self) -> bool:
        # 检查这个 Agent 是否安装了
        # 例如: shutil.which("my-agent")
        return True

    def get_status(self) -> AgentStatus:
        # 获取当前状态
        # 例如: 检查进程、读日志
        pass

    def get_current_task(self) -> AgentTask | None:
        # 获取当前任务
        pass
```

```python
# 2. 在 scheduler.py 的 BUILTIN_ADAPTERS 中注册
BUILTIN_ADAPTERS = {
    "my_agent": "aihouse.adapters.my_agent.MyAgentAdapter",
}
```

### 适配器能用的工具

| 工具 | 用途 | 跨平台 |
|------|------|--------|
| `psutil` | 进程监控 | ✅ |
| `watchdog` | 文件变化监控 | ✅ |
| `pathlib.Path` | 文件路径 | ✅ |
| `shutil.which` | 检测可执行文件 | ✅ |
| `subprocess` | 执行命令 | ✅ |

---

## 适配优先级

| 优先级 | Agent | 用户量 | 适配难度 |
|--------|-------|-------|---------|
| P0 | Claude Code | 最大 | 中 |
| P0 | 通用模式 | 所有用户 | 低 |
| P1 | Cursor | 大 | 中 |
| P1 | Codex CLI | 增长快 | 低 |
| P2 | OpenCode | 中 | 低 |
| P2 | Hermes | 小 | 低 |
