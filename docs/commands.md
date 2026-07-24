# CLI 命令参考

## 全局选项

```bash
aihouse [选项] <命令>
```

| 选项 | 说明 |
|------|------|
| `--version` | 显示版本号 |
| `--help` | 显示帮助信息 |

---

## 命令列表

| 命令 | 说明 | 快速上手 |
|------|------|---------|
| `init` | 初始化配置 | 第一次使用 |
| `start` | 启动后台监控 | 日常使用 |
| `stop` | 停止后台监控 | 日常使用 |
| `status` | 查看运行状态 | 日常使用 |
| `tasks` | 查看任务历史 | 需要时 |
| `detect` | 检测本机 Agent | 配置时 |
| `log` | 查看运行日志 | 排错时 |
| `restart` | 重启监控 | 需要时 |
| `config` | 打开配置文件 | 配置时 |

---

## 命令详解

### `aihouse init`

初始化配置目录。首次使用必须运行。

```bash
aihouse init
```

创建 `~/.aihouse/` 目录和默认配置文件。

---

### `aihouse start`

启动后台守护进程，开始监控所有已启用的 Agent。

```bash
aihouse start
# 输出: AIHouse 已启动 (PID: 12345)
```

启动后：
- 按配置的间隔（默认 10 秒）轮询所有 Agent
- API 服务器在 `http://127.0.0.1:9800` 运行
- 检测到异常时自动记录通知

---

### `aihouse status`

查看当前监控状态。

```bash
aihouse status
```

输出示例：

```
AIHouse 运行中 (PID: 12345, v0.1.0)
  Agent 数: 3
  Claude Code   active       当前任务: 重构用户模块
  Cursor        idle
  Codex CLI     not_running
```

状态值含义：

| 状态 | 含义 |
|------|------|
| `active` | Agent 正在运行任务 |
| `idle` | Agent 已启动，空闲中 |
| `busy` | Agent 忙碌 |
| `error` | Agent 异常 |
| `not_running` | Agent 未运行 |

---

### `aihouse stop`

停止后台守护进程。

```bash
aihouse stop
# 输出: AIHouse 已停止
```

---

### `aihouse tasks`

查看任务历史记录。

```bash
aihouse tasks
aihouse tasks --limit 10
aihouse tasks --agent claude_code
```

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--limit` | 20 | 返回条数 |
| `--agent` | 全部 | 按 Agent 类型筛选 |

---

### `aihouse detect`

检测本机安装了哪些 AI Agent。

```bash
aihouse detect
```

返回每个 Agent 的安装状态：

```
  Claude Code   ✓ 已安装
  Cursor        ✗ 未安装
  Codex CLI     ✗ 未安装
  OpenCode      ✓ 已安装
  Hermes        ✓ 已安装
```

---

### `aihouse log`

查看 AIHouse 自身的运行日志（最后 50 行）。

```bash
aihouse log
```

日志文件位置：`~/.aihouse/aihouse.log`

---

### `aihouse restart`

重启后台守护进程。相当于先 `stop` 再 `start`。

```bash
aihouse restart
```

---

### `aihouse config`

显示配置文件路径。

```bash
aihouse config
# 输出: 配置文件路径: /Users/xxx/.aihouse/config.yaml
```

---

## 配置文件位置

所有配置文件在 `~/.aihouse/` 目录下：

| 文件 | 说明 |
|------|------|
| `config.yaml` | 监控配置（Agent、通知、设置） |
| `.env` | 环境变量（API Key 等敏感信息） |
| `aihouse.db` | SQLite 数据库（任务记录、日志） |
| `aihouse.log` | AIHouse 运行日志 |
| `aihouse.pid` | 守护进程 PID 文件 |
