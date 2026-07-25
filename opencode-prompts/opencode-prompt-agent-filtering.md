# 修复 Agent 显示逻辑 — 仅显示已检测到的 Agent + 修正活动状态判定

## 背景

AIHouse 项目路径 `~/Projects/aihouse/`，入口 `src/aihouse/`。

当前问题：
1. **未安装的 agent 显示在 UI 中**（如你从未装过 Cursor，却显示"运行中"）
2. **Hermes 在 CLI 对话中显示为 `idle`**（因为最新 session 是一条已完成的 cron 任务，而非当前活跃对话）
3. **已完成任务的 agent 仍显示 `active`**（如 OpenCode 跑完还显示"运行中"）

## 根因分析

### 问题 1：未安装的 agent 显示在 UI 中

`src/aihouse/core/scheduler.py` 的 `get_all_statuses()` 方法（第 159-168 行）：

```python
# 这段代码为所有配置中但未检测到的 agent 填充 NOT_RUNNING 状态
for agent_cfg in self._config.get("agents", []):
    name = agent_cfg.get("name", "")
    agent_type = agent_cfg.get("type", "")
    if name not in results:
        results[name] = AgentStatus(
            agent_name=name, ...
            activity=AgentActivity.NOT_RUNNING, ...
        )
```

即使某个 agent 的 `detect()` 返回 False（未检测到），它仍以 NOT_RUNNING 出现在 API 中。

### 问题 2：Cursor/OpenCode 误检测

各 adapter 的 `detect()` 方法最后一行都 fallback 到 `self._find_processes()`，用关键词模糊匹配进程名/cmdline。macOS 上大量系统进程和 Electron 进程的 cmdline 包含 "cursor"、"opencode" 等关键词 → 误报。

### 问题 3：始终显示 "运行中"

Cursor 和 OpenCode 等 adapter 的 `get_current_task()` 方法：只要检测到进程存在，就**无条件返回一个 RUNNING 任务**（无实际任务数据），导致 UI 永远显示运行中。

## 修改方案

### 修改 1：scheduler.py — 去掉 NOT_RUNNING 填充

删除 `get_all_statuses()` 中第 159-168 行的 fallback 循环。
只返回 `_adapter_cache` 里实际检测到的 agent。

### 修改 2：所有 adapter 的 detect() — 只检查安装痕迹，不检查进程

通用的 `detect()` 策略优先级（对所有 adapter 统一规范）：
1. `shutil.which(process_name)` — 命令行是否存在
2. 已知的应用安装路径（如 `/Applications/Cursor.app`、`~/.cursor` 目录）
3. 已知的配置/状态文件（如 `~/.hermes/state.db`）

**不再通过 `self._find_processes()` 做 detect**。进程检测只在 `get_status()` 中用于判断当前是否在运行。

### 修改 3：CursorAdapter / OpenCodeAdapter 等 — 没有实际任务时返回 None

- `get_current_task()`：如果无法从状态文件/API 获取到真实任务，返回 `None`
- 只有进程存在但没有当前任务 → `activity = IDLE`
- 进程不存在 → `activity = NOT_RUNNING`

### 修改 4：HermesAdapter — 优先活跃 session

`_get_current_session()` 的 SQL 查询改为：

**第一步**：查询当前正在运行（`ended_at IS NULL`）且非 cron 源的最新 session
**第二步**：如果无活跃 session，fallback 到最新的已完成 session（但源不是 cron）

```sql
-- 第一步：优先活跃 session
SELECT s.*, COALESCE(u.api_call_count, 0) as api_count,
       COALESCE(u.input_tokens, s.input_tokens, 0) as in_tokens,
       COALESCE(u.output_tokens, s.output_tokens, 0) as out_tokens,
       COALESCE(u.estimated_cost_usd, s.estimated_cost_usd, 0.0) as cost
FROM sessions s
LEFT JOIN session_model_usage u ON u.session_id = s.id
WHERE s.started_at IS NOT NULL AND s.ended_at IS NULL
  AND (s.source IS NULL OR s.source NOT IN ('cron'))
ORDER BY s.started_at DESC LIMIT 1
```

```sql
-- 第二步：无活跃 session 时，回退到最新已完成 session
SELECT ...
WHERE s.started_at IS NOT NULL AND s.ended_at IS NOT NULL
  AND (s.source IS NULL OR s.source NOT IN ('cron'))
ORDER BY s.started_at DESC LIMIT 1
```

注意：以上两条 SQL 在 `_get_current_session()` 方法中实现，先查活跃，查不到再查完成。

### 修改 5：get_status() 中 Hermes 「活跃」判定

```python
if current_task is not None and current_task.status == TaskStatus.RUNNING:
    activity = AgentActivity.ACTIVE  # 真有活跃任务
elif procs:
    activity = AgentActivity.IDLE     # 进程在但无活跃任务
else:
    activity = AgentActivity.NOT_RUNNING  # 完全没运行
```

### 修改 6：CursorAdapter/OpenCodeAdapter — get_current_task() 改为返回 None

当前：
```python
def get_current_task(self) -> Optional[AgentTask]:
    procs = self._find_processes()
    if not procs:
        return None
    # 永远返回一个 RUNNING 任务 ← 这是问题
    return AgentTask(..., status=TaskStatus.RUNNING, ...)
```

改为：
```python
def get_current_task(self) -> Optional[AgentTask]:
    # Cursor 没有可读的状态文件，无法获取真实任务
    # 返回 None 让 get_status() 显示为 IDLE
    return None
```

同理修改 OpenCodeAdapter、ClaudeCodeAdapter 等没有状态文件读取能力的 adapter。

## 影响范围

| 文件 | 改动 |
|------|------|
| `src/aihouse/core/scheduler.py` | 删 159-168 行 fallback 循环 |
| `src/aihouse/adapters/hermes.py` | `_get_current_session()` SQL 改为优先活跃 session |
| `src/aihouse/adapters/cursor.py` | `detect()` 去掉进程检测；`get_current_task()` 返回 None |
| `src/aihouse/adapters/opencode.py` | 同上 |
| `src/aihouse/adapters/claude_code.py` | 同上（如适用） |
| `src/aihouse/adapters/codex.py` | 同上（如适用） |
| `src/aihouse/adapters/pi.py` | 同上（如适用） |
| `src/aihouse/adapters/kilo_code.py` | 同上（如适用） |
| `src/aihouse/adapters/cline.py` | 同上（如适用） |

## 验证方式

```bash
aihouse restart
sleep 3
curl -s http://127.0.0.1:9800/api/status | python3 -c "
import json, sys
d = json.load(sys.stdin)
agents = d.get('agents', [])
print(f'共 {len(agents)} 个 agent（应为实际安装数量）')
for a in agents:
    print(f\"  {a['name']:12s}  act={a['activity']:12s}  pid={str(a.get('pid','?')):6s}\")
"
```

期望结果：
- 未安装的 agent（如 Pi、Cline、Kilo Code）不出现
- Hermes 显示 `active`（因为正在对话）
- Cursor/OpenCode 如进程在但无任务 → `idle`，如进程不在 → 不显示
