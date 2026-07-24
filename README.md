# AIHouse

> **监控你的 AI Agent 在干什么。**
>
> 一个开源的桌面应用，监控你所有 AI 编码 Agent 的任务状态。
> 任务跑完了没、卡住了没、成功了没、花了多少钱——瞟一眼就知道。

[![GitHub Release](https://img.shields.io/github/v/release/988hj7tczd-oss/aihouse)](https://github.com/988hj7tczd-oss/aihouse/releases)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](pyproject.toml)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)]()

**中文** | [English](README.en.md)

---

## 🖥️ 界面预览

```
┌──── 系统托盘 ───────────────────┐
│ 🟢 AIHouse  ·  一切正常          │  ← 瞟一眼就知道状态
└─────────────────────────────────┘

┌──────────────────────────────────┐
│  AIHouse     14:30  全部正常 ✅   │
│──────────────────────────────────│
│  Claude Code  🟢 重构用户模块 3m  │  ← 每个 Agent 一行
│  Cursor       🔵 空闲            │
│  Hermes       🟢 生成文章 2m     │
│                                  │
│  📊 今日: 7完成 · 0失败 · 1卡住  │
│  💰 今日费用: $2.45              │
│                                  │
│  [历史] [设置] [刷新]              │
└──────────────────────────────────┘
```

---

## ✨ 功能

- **实时监控** — 系统托盘图标，颜色代表整体状态（绿/蓝/黄/红）
- **多 Agent 统一面板** — Claude Code、Cursor、Hermes、OpenCode 等在一个界面显示
- **任务追踪** — 每个 Agent 当前在跑什么任务、跑了多久
- **卡住检测** — Agent 长时间无活动自动告警
- **费用统计** — 每日 API 花费汇总，超预算自动通知
- **通知推送** — 微信推送（PushPlus）/ 桌面通知 / iOS（Bark）
- **历史记录** — 查看所有 Agent 的历史任务
- **自动检测** — 自动识别本机已安装的 Agent
- **跨平台** — macOS / Windows / Linux
- **轻量** — Python 后端 + Tauri 桌面端，打包仅 ~10MB

---

## 📦 安装

> 从 [GitHub Releases](https://github.com/988hj7tczd-oss/aihouse/releases) 下载最新版 wheel 包安装。

### macOS

```bash
curl -L -o aihouse-0.1.0-py3-none-any.whl \
  https://github.com/988hj7tczd-oss/aihouse/releases/download/v0.1.0/aihouse-0.1.0-py3-none-any.whl
pip install aihouse-0.1.0-py3-none-any.whl
aihouse init
aihouse start
aihouse status
```

### Windows

```powershell
curl -L -o aihouse-0.1.0-py3-none-any.whl ^
  https://github.com/988hj7tczd-oss/aihouse/releases/download/v0.1.0/aihouse-0.1.0-py3-none-any.whl
pip install aihouse-0.1.0-py3-none-any.whl
aihouse init
aihouse start
aihouse status
```

### Linux

```bash
curl -L -o aihouse-0.1.0-py3-none-any.whl \
  https://github.com/988hj7tczd-oss/aihouse/releases/download/v0.1.0/aihouse-0.1.0-py3-none-any.whl
pip install aihouse-0.1.0-py3-none-any.whl
aihouse init
aihouse start
aihouse status
```

> 后续上传 PyPI 后，只需 `pip install aihouse`

### 桌面端（可选）

桌面端提供系统托盘图标和可视化面板。

```bash
# 安装 Node.js：https://nodejs.org/
# 安装 Rust：https://rustup.rs/

cd desktop
npm install
npm run tauri dev     # 开发模式
npm run tauri build   # 打包安装程序
```

> 详细安装说明请查看 [安装指南](docs/installation.md)

---

## 🚀 快速开始

```bash
# 1. 初始化配置
aihouse init

# 2. 检测本机 Agent
aihouse detect

# 3. 启动监控
aihouse start

# 4. 查看状态
aihouse status

# 5. 查看任务历史
aihouse tasks

# 6. 停止监控
aihouse stop
```

> 详细使用说明请查看 [快速开始](docs/getting-started.md)

---

## 🤖 支持的 Agent

| Agent | 类型 | 监控方式 | 状态 |
|-------|------|---------|------|
| **Hermes** | CLI 工具 | 读 state.db SQLite | ✅ 稳定 |
| **Claude Code** | CLI 工具 | 读 ~/.claude/logs/ | ✅ 稳定 |
| **Cursor** | 桌面应用 | 进程检测 | ✅ 稳定 |
| **Codex CLI** | CLI 工具 | 进程检测 | ✅ 稳定 |
| **OpenCode** | CLI 工具 | 读 SQLite | ✅ 稳定 |
| **OpenClaw** | CLI 工具 | 读 JSON/SQLite | ✅ 稳定 |
| **Kilo Code** | VS Code 插件 | 进程检测 | ⚠️ 基础 |
| **Cline** | VS Code 插件 | 进程检测 | ⚠️ 基础 |
| **GitHub Copilot** | VS Code 插件 | 进程检测 | ⚠️ 基础 |
| **通义灵码** | VS Code 插件 | 进程检测 | ⚠️ 基础 |
| **通用模式** | 任意 Agent | 进程 + 文件变化 | ✅ 兜底 |

---

## 📋 CLI 命令

| 命令 | 说明 |
|------|------|
| `aihouse init` | 初始化配置目录 |
| `aihouse start` | 启动后台监控 |
| `aihouse stop` | 停止监控 |
| `aihouse restart` | 重启监控 |
| `aihouse status` | 查看 Agent 状态 |
| `aihouse tasks` | 查看任务历史 |
| `aihouse detect` | 检测本机 Agent |
| `aihouse log` | 查看运行日志 |
| `aihouse desktop` | 启动桌面端 |
| `aihouse diagnose` | 诊断适配器状态 |

> 完整命令参考请查看 [CLI 命令](docs/commands.md)

---

## 🏗️ 架构

```
┌──────────────────────────────────────┐
│  桌面端 (Tauri)                       │
│  ┌──────────┐  ┌──────────────────┐  │
│  │ 系统托盘  │  │ 弹出面板          │  │
│  │ 🟢🔵🟡🔴 │  │ Agent 状态列表   │  │
│  └──────────┘  │ 任务详情 / 历史   │  │
│                │ / 设置            │  │
│                └────────┬─────────┘  │
└─────────────────────────┼────────────┘
                          │ REST API
┌─────────────────────────┼────────────┐
│  后端 (Python)           │           │
│  ┌────────────────────────────────┐  │
│  │ 调度器 → 适配器 → 分析引擎     │  │
│  │                    ↓           │  │
│  │ SQLite 存储 ← 通知器 → 微信   │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

> 详细架构说明请查看 [架构说明](docs/architecture.md)

---

## 📖 文档

| 文档 | 说明 |
|------|------|
| [快速开始](docs/getting-started.md) | 5 分钟上手 |
| [安装指南](docs/installation.md) | Mac / Windows / Linux |
| [CLI 命令](docs/commands.md) | 命令详解 |
| [配置说明](docs/configuration.md) | 配置文件参考 |
| [桌面端使用](docs/desktop.md) | 面板操作 |
| [架构说明](docs/architecture.md) | 工作原理 |
| [适配器体系](docs/adapters.md) | Agent 适配 |
| [常见问题](docs/faq.md) | 排错指南 |
| [开发者指南](docs/develop.md) | 参与开发 |

---

## 🤝 参与贡献

欢迎提交 Pull Request 或 Issue！

- [贡献指南](CONTRIBUTING.md)
- [行为准则](CODE_OF_CONDUCT.md)
- [安全政策](SECURITY.md)

---

## 📄 开源协议

MIT License

Copyright (c) 2026 Zhuanz

---

## ⭐ Star 历史

如果你觉得这个工具有用，欢迎点亮 Star ⭐
