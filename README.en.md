# AIHouse

> **Watch what your AI Agents are doing.**
>
> An open-source desktop application that monitors all your AI coding agents' task status.
> Know when a task is done, stuck, failed, or how much it cost — at a glance.

[![GitHub Release](https://img.shields.io/github/v/release/988hj7tczd-oss/aihouse)](https://github.com/988hj7tczd-oss/aihouse/releases)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](pyproject.toml)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)]()

---

## 🖥️ Preview

```
┌──── System Tray ────────────────┐
│ 🟢 AIHouse  ·  All Normal        │  ← Status at a glance
└──────────────────────────────────┘

┌──────────────────────────────────┐
│  AIHouse     14:30  All Normal ✅│
│──────────────────────────────────│
│  Claude Code  🟢 Refactoring 3m  │  ← One row per agent
│  Cursor       🔵 Idle            │
│  Hermes       🟢 Generating 2m   │
│                                  │
│  📊 Today: 7 done · 0 failed     │
│  💰 Cost: $2.45                  │
│                                  │
│  [History] [Settings] [Refresh]  │
└──────────────────────────────────┘
```

---

## ✨ Features

- **Real-time Monitoring** — System tray icon with color-coded status (green/blue/yellow/red)
- **Multi-Agent Dashboard** — Claude Code, Cursor, Hermes, OpenCode and more in one panel
- **Task Tracking** — See what task each agent is running and for how long
- **Stuck Detection** — Automatic alerts when an agent is stuck
- **Cost Tracking** — Daily API cost summary with budget alerts
- **Notifications** — WeChat (PushPlus) / Desktop / iOS (Bark)
- **History** — Browse all past agent tasks
- **Auto-Detect** — Automatically detects installed agents on your machine
- **Cross-Platform** — macOS / Windows / Linux
- **Lightweight** — Python backend + Tauri desktop, ~10MB bundle

---

## 📦 Installation

> Download the latest wheel from [GitHub Releases](https://github.com/988hj7tczd-oss/aihouse/releases).

### macOS / Linux

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

> Will be available on PyPI soon (`pip install aihouse`)

### Desktop App (Optional)

The desktop app provides a system tray icon and visual dashboard.

```bash
# Install Node.js: https://nodejs.org/
# Install Rust: https://rustup.rs/

cd desktop
npm install
npm run tauri dev     # Development mode
npm run tauri build   # Build installer
```

---

## 🚀 Quick Start

```bash
# 1. Initialize config
aihouse init

# 2. Detect agents on your machine
aihouse detect

# 3. Start monitoring
aihouse start

# 4. Check status
aihouse status

# 5. View task history
aihouse tasks

# 6. Stop
aihouse stop
```

---

## 🤖 Supported Agents

| Agent | Type | Monitoring Method | Status |
|-------|------|------------------|--------|
| **Hermes** | CLI | SQLite (state.db) | ✅ Stable |
| **Claude Code** | CLI | Log files | ✅ Stable |
| **Cursor** | Desktop App | Process detection | ✅ Stable |
| **Codex CLI** | CLI | Process detection | ✅ Stable |
| **OpenCode** | CLI | SQLite | ✅ Stable |
| **OpenClaw** | CLI | JSON/SQLite | ✅ Stable |
| **Kilo Code** | VS Code Plugin | Process detection | ⚠️ Basic |
| **Cline** | VS Code Plugin | Process detection | ⚠️ Basic |
| **GitHub Copilot** | VS Code Plugin | Process detection | ⚠️ Basic |
| **Generic** | Any Agent | Process + file changes | ✅ Fallback |

---

## 📋 CLI Commands

| Command | Description |
|---------|------------|
| `aihouse init` | Initialize config directory |
| `aihouse start` | Start background monitoring |
| `aihouse stop` | Stop monitoring |
| `aihouse restart` | Restart monitoring |
| `aihouse status` | View agent status |
| `aihouse tasks` | View task history |
| `aihouse detect` | Detect installed agents |
| `aihouse log` | View runtime logs |
| `aihouse desktop` | Launch desktop app |
| `aihouse diagnose` | Diagnose adapter status |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────┐
│  Desktop (Tauri)                      │
│  ┌──────────┐  ┌──────────────────┐  │
│  │ Tray Icon│  │ Dashboard Panel  │  │
│  │ 🟢🔵🟡🔴 │  │ Agent Status     │  │
│  └──────────┘  │ Task Detail      │  │
│                │ History/Settings │  │
│                └────────┬─────────┘  │
└─────────────────────────┼────────────┘
                          │ REST API
┌─────────────────────────┼────────────┐
│  Backend (Python)        │           │
│  ┌────────────────────────────────┐  │
│  │ Scheduler → Adapter → Analyzer│  │
│  │                    ↓           │  │
│  │ SQLite Storage ← Notifier     │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

---

## 🤝 Contributing

Contributions are welcome!

- [Contributing Guide](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security Policy](SECURITY.md)

---

## 📄 License

MIT License

Copyright (c) 2026 Zhuanz

---

## ⭐ Star History

If you find this tool useful, please give it a star ⭐
