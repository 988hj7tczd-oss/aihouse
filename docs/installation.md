# 安装指南

## 前提条件

- Python 3.9 或更高版本
- pip（Python 包管理器）
- （可选）Node.js 18+ 和 Rust — 仅桌面端需要

---

## 安装后端（所有平台）

```bash
pip install aihouse
```

验证安装：

```bash
aihouse --version
# 输出: aihouse, version 0.1.0
```

---

## 安装桌面端（可选）

桌面端提供系统托盘图标和可视化面板。需要额外安装 Node.js 和 Rust。

### 1. 安装 Node.js

- **macOS / Linux**：https://nodejs.org/（下载 LTS 版本）
- **Windows**：https://nodejs.org/（下载 LTS 版本）
- 验证：`node --version` 和 `npm --version`

### 2. 安装 Rust

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

验证：`rustc --version`

### 3. 构建桌面端

```bash
# 从源码构建
git clone https://github.com/你的用户名/aihouse.git
cd aihouse/desktop
npm install
npm run tauri dev     # 开发模式
# 或
npm run tauri build   # 打包为安装程序
```

---

## 从源码安装

```bash
git clone https://github.com/你的用户名/aihouse.git
cd aihouse
pip install -e .
aihouse init
```

---

## Docker 安装（企业版）

> 计划中，尚未实现。
