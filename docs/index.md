# AIHouse 使用文档

> 监控你的 AI Agent 在干什么。
>
> 一个开源的桌面应用，监控你所有 AI 编码 Agent 的任务状态。任务跑完了没、卡住了没、成功了没、花了多少钱——瞟一眼就知道。

---

## 快速导航

| 如果你要 | 看这里 |
|---------|--------|
| 快速上手 | [快速开始](getting-started.md) |
| 安装到电脑 | [安装指南](installation.md) |
| 配置要监控的 Agent | [配置说明](configuration.md) |
| 查看所有命令 | [CLI 命令参考](commands.md) |
| 使用桌面面板 | [桌面端使用](desktop.md) |
| 了解工作原理 | [架构说明](architecture.md) |
| 适配更多 Agent | [适配器体系](adapters.md) |

---

## 一句话介绍

**AIHouse** 是一个桌面工具，帮你盯着所有 AI Agent 的状态：

- **Claude Code** 在跑任务？跑完了没？卡住了没？
- **Cursor** 改了哪些文件？花了多少钱？
- **Hermes**、**Codex CLI**、**OpenCode** 都在干什么？

不用来回切终端，桌面托盘图标一目了然。

---

## 支持的系统

| 平台 | 状态 | 说明 |
|------|------|------|
| macOS | ✅ 已测试 | Intel 和 Apple Silicon |
| Windows | ⚠️ 理论支持 | 需要 Windows 10+ |
| Linux | ⚠️ 理论支持 | 需要桌面环境 |

---

## 支持的 Agent

| Agent | 监控方式 | 状态 |
|-------|---------|------|
| Claude Code | 日志文件 + 进程 | ✅ |
| Cursor | 日志文件 + 进程 | ✅ |
| Codex CLI | 进程监控 | ✅ |
| OpenCode | 进程监控 | ✅ |
| Hermes | SQLite 数据库 | ✅ |
| 通用模式（任意 Agent） | 进程 + 文件变化 | ✅ |

---

## 项目仓库

- GitHub：`https://github.com/你的用户名/aihouse`
- 问题反馈：GitHub Issues
