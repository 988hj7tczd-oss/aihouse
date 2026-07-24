# 配置说明

配置文件位于 `~/.aihouse/config.yaml`。初始配置可通过 `aihouse init` 生成。

---

## 配置结构

```yaml
project: AIHouse
version: 2

agents:         # 要监控的 AI Agent 列表
  - name: ...
    type: ...
    enabled: true/false

services:       # 辅助监控服务（可选）
  - name: ...
    type: api_cost / http

notifications:  # 通知渠道
  - type: pushplus / desktop / bark

settings:       # 全局设置
  poll_interval: 10
  history_retention_days: 30
  auto_start: false
```

---

## Agent 配置

### 基本格式

```yaml
agents:
  - name: "Claude Code"
    type: claude_code
    enabled: true
```

| 字段 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | 是 | — | 显示名称，自定 |
| `type` | 是 | — | Agent 类型标识 |
| `enabled` | 否 | `true` | 是否启用监控 |
| `log_path` | 否 | 自动检测 | 日志文件路径 |
| `stuck_threshold` | 否 | `300` | 卡住判定阈值（秒） |

### 支持的 Agent 类型

| type | Agent | 数据来源 |
|------|-------|---------|
| `claude_code` | Claude Code | 日志 + 进程 |
| `cursor` | Cursor | 日志 + 进程 |
| `codex` | Codex CLI | 进程 |
| `opencode` | OpenCode | 进程 |
| `hermes` | Hermes Agent | 会话数据库 |
| `generic` | 通用模式（任意 Agent） | 进程 + 文件变化 |

### 通用模式配置

通用模式适用于任意 AI Agent，不需要特定适配器：

```yaml
agents:
  - name: "我的 Agent"
    type: generic
    process_name: "my-agent"       # 要监控的进程名
    work_dir: "~/my-project"       # 工作目录（检测文件变化）
    stuck_threshold: 600            # 10 分钟无活动视为卡住
```

---

## 服务配置（可选）

### AI 费用监控

```yaml
services:
  - name: "DeepSeek 今日费用"
    type: api_cost
    provider: deepseek
    api_key: "${DEEPSEEK_API_KEY}"  # 从环境变量读取
    daily_budget: 5
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `provider` | 是 | `deepseek` 或 `openai` |
| `api_key` | 是 | 建议使用 `${VAR}` 环境变量引用 |
| `daily_budget` | 否 | 日预算（美元），超了告警 |

### HTTP 服务检查

```yaml
services:
  - name: "我的网站"
    type: http
    url: "https://example.com"
    expected_code: 200
    timeout: 10
```

| 字段 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `url` | 是 | — | 要检查的 URL |
| `expected_code` | 否 | `200` | 期望的状态码 |
| `timeout` | 否 | `10` | 超时时间（秒） |

---

## 通知配置

```yaml
notifications:
  - type: pushplus
    token: "${PUSHPLUS_TOKEN}"
    events:
      - task_completed
      - task_failed
      - agent_stuck
```

### 通知渠道

| type | 说明 | 注册方式 |
|------|------|---------|
| `pushplus` | 微信推送（推荐） | pushplus.plus 注册 |
| `desktop` | 桌面通知 | 无需注册 |
| `bark` | iOS 推送 | App Store 下载 Bark |

### 事件类型

| event | 触发条件 |
|-------|---------|
| `task_completed` | Agent 任务完成 |
| `task_failed` | Agent 任务失败 |
| `agent_stuck` | Agent 卡住 |
| `budget_exceeded` | 超出预算 |

---

## 全局设置

```yaml
settings:
  poll_interval: 10         # 轮询间隔（秒）
  history_retention_days: 30  # 历史保留天数
  auto_start: false          # 是否开机自启
```

---

## 环境变量

敏感信息（API Key、Token 等）不写在配置文件中，写在 `~/.aihouse/.env`：

```bash
DEEPSEEK_API_KEY=sk-xxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxx
PUSHPLUS_TOKEN=xxxxxxxx
BARK_KEY=xxxxxxxx
```

在配置文件中通过 `${变量名}` 引用。
