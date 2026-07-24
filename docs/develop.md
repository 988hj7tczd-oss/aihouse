# 开发者指南

## 项目结构

```
aihouse/
├── src/aihouse/          ← Python 后端源码
│   ├── cli.py              ← 命令行入口
│   ├── config.py           ← 配置管理
│   ├── server.py           ← Flask REST API
│   ├── core/               ← 核心引擎
│   │   ├── models.py       ← 数据模型
│   │   ├── storage.py      ← SQLite 存储
│   │   ├── scheduler.py    ← 定时调度
│   │   ├── adapter.py      ← 适配器基类
│   │   ├── notifier.py     ← 通知推送
│   │   └── analyzer.py     ← 分析引擎
│   ├── adapters/           ← Agent 适配器
│   │   ├── generic.py      ← 通用模式
│   │   ├── claude_code.py
│   │   ├── cursor.py
│   │   ├── codex.py
│   │   ├── opencode.py
│   │   └── hermes.py
│   └── services/           ← 辅助服务
│       ├── api_cost.py     ← 费用查询
│       └── http_check.py   ← HTTP 检查
├── desktop/                ← Tauri 桌面端
│   ├── src/
│   │   ├── App.svelte      ← 主面板
│   │   ├── TaskDetail.svelte
│   │   ├── History.svelte
│   │   └── Settings.svelte
│   └── src-tauri/
│       └── src/main.rs     ← 系统托盘
├── docs/                   ← 文档
├── scripts/                ← 打包脚本
└── tests/                  ← 测试
```

## 开发环境

```bash
# 克隆项目
git clone https://github.com/你的用户名/aihouse.git
cd aihouse

# 安装 Python 依赖（开发模式）
pip install -e .
pip install pytest  # 用于测试

# 安装桌面端依赖
cd desktop
npm install
```

## 运行开发服务器

### 后端

```bash
# 方式一：CLI 命令
aihouse start

# 方式二：直接运行 Python
python -c "from aihouse.server import Server; from aihouse.core.storage import Storage; s=Storage(); Server(None,s,None).start(); input('运行中...')"
```

### 桌面端

```bash
cd desktop
npm run tauri dev
```

## 添加新的 Agent 适配器

参考 `docs/adapters.md`。

## 构建

```bash
# Python 包
bash scripts/build.sh

# 桌面端安装包
cd desktop
npm run tauri build
构建产物在 desktop/src-tauri/target/release/bundle/
```

## 测试

```bash
# Python 测试
pytest tests/

# 手动测试单个模块
python -c "from aihouse.core.models import AgentTask; print('OK')"
python -c "from aihouse.core.storage import Storage; s=Storage('/tmp/test.db'); print('OK')"
python -c "from aihouse.core.scheduler import Scheduler; s=Storage('/tmp/test2.db'); Scheduler(s,{'agents':[],'settings':{'poll_interval':30}}); print('OK')"
```

## 代码规范

- 类型注解（Python 3.10+）
- 中文注释（关键逻辑写清楚）
- 每个公开函数有 docstring
- 异常处理：外部输入需要验证，内部错误需要捕获
- 文件路径：统一用 `pathlib.Path`
