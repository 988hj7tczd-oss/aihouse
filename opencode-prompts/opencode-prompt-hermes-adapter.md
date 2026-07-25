# 修复 Hermes Agent 适配器 — 正确读取 Hermes 运行状态

## 背景

AIHouse 项目路径 `~/Projects/aihouse/`，入口 `src/aihouse/`。已安装为 `pip install -e .` 模式。桌面端在 `desktop/`（Svelte + Tauri）。

Hermes（当前系统正在与我对聊的 AI Agent）已检测为 "active"，但显示的任务描述是 **整个 Hermes Persona 模板**（系统提示词），不是用户真正在问的问题。其他数据（token数、费用、持续时间）也都是错的。

## 根本原因（5个问题）

### 1️⃣ 任务描述读取 `system_prompt` 而非用户消息

当前代码 (`src/aihouse/adapters/hermes.py`, `get_current_task` 方法)：

```python
description = session.get("system_prompt", "") or session.get("context", "") or "Hermes 任务"
```

Hermes 的 `state.db`（位于 `~/.hermes/state.db`）的 `sessions` 表中，`system_prompt` 存的是 Agent Persona（你是谁/怎么回答问题），不是用户的实际任务。**用户的实际查询在 `messages` 表里**（第一条 role='user' 的消息内容才是任务描述）。

### 2️⃣ `started_at` 是 Unix 时间戳（REAL），适配器用 ISO 字符串解析

Hermes `sessions` 表的 `started_at` 是 REAL 类型（Unix 时间戳浮点数，如 `1784987242.030324`）。

当前代码：
```python
started_at = datetime.fromisoformat(started_at_str)  # ← 抛异常，跳到 fallback
```

修复后需：
```python
started_at = datetime.fromtimestamp(float(started_at_str))
```

### 3️⃣ sessions 表没有 `status` 列

当前代码查 `session.get("status", "")`。Hermes 的 sessions 表没有 status 列。

状态推断规则：
- `ended_at IS NULL` 且 `message_count > 0` → RUNNING
- `ended_at IS NOT NULL` → COMPLETED（可根据 `end_reason` 判断 FAILED）
- 没有当前活跃 session → 无任务

### 4️⃣ 费用/Token 数据没有读取

`session_model_usage` 表存了每个 session 的实际 token 数、API 调用次数和估算费用。当前适配器返回全 0。需要 LEFT JOIN 或单独查询。

### 5️⃣ `get_recent_tasks()` 未实现

返回空列表。需要从 sessions 表读取已结束的 session 作为历史任务。

## Hermes state.db 关键表结构

### sessions 表
| 列 | 类型 | 说明 |
|---|---|---|
| `id` | TEXT | 主键 (如 `ms0f8t1f1q51z6`) |
| `model` | TEXT | 模型名 (如 `deepseek-v4-flash`) |
| `system_prompt` | TEXT | Agent Persona（不要用它当任务描述！） |
| `title` | TEXT | 会话标题（可为 NULL，备选描述） |
| `started_at` | REAL | Unix 时间戳 |
| `ended_at` | REAL | NULL=运行中，有值=已结束 |
| `end_reason` | TEXT | 结束原因 (completed/error/cancelled) |
| `message_count` | INTEGER | 消息数 |
| `input_tokens` | INTEGER | 总输入 token |
| `output_tokens` | INTEGER | 总输出 token |
| `estimated_cost_usd` | REAL | 估算费用 |
| `source` | TEXT | 来源 (cli/gateway/webui) |

### messages 表
| 列 | 类型 | 说明 |
|---|---|---|
| `id` | INTEGER | 主键 |
| `session_id` | TEXT | 关联 sessions.id |
| `role` | TEXT | user/assistant/tool |
| `content` | TEXT | 消息内容 |
| `timestamp` | REAL | Unix 时间戳 |

### session_model_usage 表（费用明细）
| 列 | 说明 |
|---|---|
| `session_id` | 关联 sessions.id |
| `model` | 模型名 |
| `api_call_count` | API 调用次数 |
| `input_tokens` | 输入 token |
| `output_tokens` | 输出 token |
| `estimated_cost_usd` | 估算费用 |
| `actual_cost_usd` | 实际费用 |
| `last_seen` | 最后活动时间 (Unix ts) |

## 要求

**修改 `src/aihouse/adapters/hermes.py`**，不要改其他文件。

### get_current_task() 重构

1. 从 `~/.hermes/state.db` 查询最新 session：
```sql
SELECT s.*, COALESCE(u.api_call_count, 0) as api_count,
       COALESCE(u.input_tokens, s.input_tokens, 0) as in_tokens,
       COALESCE(u.output_tokens, s.output_tokens, 0) as out_tokens,
       COALESCE(u.estimated_cost_usd, s.estimated_cost_usd, 0.0) as cost
FROM sessions s
LEFT JOIN session_model_usage u ON u.session_id = s.id
WHERE started_at IS NOT NULL
ORDER BY started_at DESC LIMIT 1
```

2. 获取任务描述（优先级从高到低）：
   - 查 `messages` 表该 session 的第一个 `role='user'` 的消息 `content`，截取前 200 字符，超出加 `...`
   - Fallback: `sessions.title`
   - 最终 fallback: `"Hermes 任务"`

3. `started_at` 用 `datetime.fromtimestamp(float(value))` 解析（Hermes 存的是 Unix 时间戳 REAL，不是 ISO 字符串）

4. 状态推断：
   - `ended_at IS NULL AND message_count > 0` → `RUNNING`
   - `ended_at IS NOT NULL AND end_reason = 'error'` → `FAILED`
   - `ended_at IS NOT NULL` → `COMPLETED`
   - 否则 → `UNKNOWN`

5. 填充 `estimated_tokens` 和 `estimated_cost`（来自查询中的 in_tokens、cost 字段）

6. 计算 `duration`：如果有 `ended_at` 则 `ended_at - started_at`，否则 `now - started_at`

### get_status() 改进

1. `last_seen` 用最新 session 的 `started_at`（或 session_model_usage 的 `last_seen`），而不是进程创建时间
2. 如果 Hermes 进程在运行但当前没有活跃 session → `IDLE` 而不是 `ACTIVE`
3. 如果 Hermes 进程在运行且有活跃 session（`ended_at IS NULL`）→ `ACTIVE`

### get_recent_tasks() 实现

从 sessions 表读取最近 20 条已结束（`ended_at IS NOT NULL`）的会话，转换为 AgentTask 对象。每条记录的 description 可以从 messages 表第一条 user 消息获取。

## 验证方式

修改后重启 aihouse：

```bash
aihouse restart
sleep 3
curl -s http://127.0.0.1:9800/api/status/hermes | python3 -m json.tool
```

期望看到：
- `description` 是实际用户问题（如"检查一下aihouse这个工具项目..."），不是 Persona
- `started_at` 是合理的当前时间（2026-07-25 左右），不是 2026-07-15
- `duration` 有合理值
- `estimated_tokens` 有非零值
- `estimated_cost` 有非零值（不一定是 0）
- `activity` 为 "active"

## 注意

- 只改 `src/aihouse/adapters/hermes.py`
- 不需要在 `__init__.py` 或其他文件注册
- Hermes Desktop 长期运行（gpu-process/renderer 等），进程检测已经正常，不需要改 `detect()`
- Hermes state.db 可能正在被 Hermes 写入，用 `timeout=3` 避免锁住
- `session_model_usage.session_id` 的 ID 格式与 `sessions.id` 可能不同（如 `20260715_215520_cfda13` vs `ms0f8t1f1q51z6`），如果 LEFT JOIN 没有匹配，费用/token 靠 sessions 表本身字段即可
- 格式：遵循项目现有代码风格（类型注解、双引号字符串、Google-style docstring）
