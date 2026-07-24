# 快速开始

## 1. 安装

```bash
pip install aihouse
```

> 详见[安装指南](installation.md)。

## 2. 初始化

```bash
aihouse init
```

这会创建配置文件目录 `~/.aihouse/`，包含：
- `config.yaml` — 监控配置
- `.env` — 环境变量（API Key 等）
- `aihouse.db` — 本地数据存储（自动创建）

## 3. 查看本机已安装的 Agent

```bash
aihouse detect
```

示例输出：

```
  Claude Code   ✗ 未安装
  Cursor        ✗ 未安装
  Codex CLI     ✗ 未安装
  OpenCode      ✓ 已安装
  Hermes        ✓ 已安装
```

AIHouse 会自动检测你电脑上已经装了哪些 AI Agent。

## 4. 启动监控

```bash
aihouse start
```

启动后在后台运行，自动检查所有已启用的 Agent 状态。

## 5. 查看状态

```bash
aihouse status
```

示例输出：

```
AIHouse 运行中 (PID: 12345, v0.1.0)
  Agent 数: 2
  Claude Code   not_running
  Hermes        idle
```

## 6. 查看任务历史

```bash
aihouse tasks
```

查看最近运行的任务记录。

## 7. 桌面端

如果你安装了桌面端（见[安装指南](installation.md)），启动后会在系统托盘显示图标：

```
┌──── 菜单栏/任务栏 ─────────────────────┐
│  ... 🔋 🕐 🔍 🟢 AIHouse              │
└─────────────────────────────────────────┘
```

图标颜色代表整体状态：
- 🟢 绿色 — 一切正常
- 🔵 蓝色 — 全部空闲
- 🟡 黄色 — 有 Agent 卡住或警告
- 🔴 红色 — 有 Agent 出问题了

点击图标弹出面板，查看详细状态。

## 8. 停止监控

```bash
aihouse stop
```

---

## 典型工作流

### 日常使用

```bash
# 早上启动
aihouse start

# 白天正常干活，Agent 状态随时可查
aihouse status

# 晚上停止（可选，不影响你睡觉）
aihouse stop
```

### 配合桌面端

```bash
# 一个终端跑后端
aihouse start

# 另一个终端/直接打开桌面端
cd desktop && npm run tauri dev
```

桌面端会自动连接后端的 API，实时显示 Agent 状态。
