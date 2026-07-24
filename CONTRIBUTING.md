# 贡献指南

感谢你考虑为 AIHouse 贡献代码！🎉

## 贡献方式

### 🐛 报告 Bug

1. 搜索 [Issues](https://github.com/988hj7tczd-oss/aihouse/issues) 看是否已存在
2. 使用 Bug 报告模板创建 Issue
3. 提供复现步骤、日志和运行环境

### 💡 功能建议

1. 使用功能建议模板创建 Issue
2. 描述你遇到的痛点和期望的解决方案

### 🔧 提交代码

## 开发环境搭建

### 后端

```bash
# 克隆仓库
git clone https://github.com/988hj7tczd-oss/aihouse.git
cd aihouse

# 安装依赖
pip install -e .
pip install pytest

# 运行测试
python -c "from aihouse.core.models import AgentTask; print('OK')"
```

### 桌面端

```bash
# 安装 Node.js 和 Rust
# 然后：
cd desktop
npm install
npm run tauri dev
```

## 代码规范

### Python

- Python 3.9+
- 使用类型注解
- 中文注释，关键逻辑写清楚
- 每个公开函数有 docstring
- 路径用 `pathlib.Path`，不要用字符串拼接

### Git 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>: <description>

[optional body]

[optional footer]
```

| Type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `refactor` | 重构 |
| `test` | 测试 |
| `chore` | 构建/工具 |

示例：

```
feat: 添加 OpenClaw 适配器

实现 OpenClaw 的任务监控，读取 ~/.openclaw/openclaw.json
和 SQLite 数据库中的 session 信息。

Closes #12
```

### Pull Request 流程

1. Fork 仓库并创建特性分支：`feat/your-feature`
2. 提交改动，确保测试通过
3. 创建 PR，描述改了什么和为什么
4. 等待 Review

### 适配器开发指南

参考 `docs/adapters.md` 和现有适配器：

```python
from aihouse.core.adapter import AgentAdapter

class MyAdapter(AgentAdapter):
    name = "My Agent"
    agent_type = "my_agent"
    
    def detect(self) -> bool:
        """检测本机是否安装了此 Agent"""
        return shutil.which("my-agent") is not None
    
    def get_status(self) -> AgentStatus:
        """获取 Agent 当前状态"""
        # 1. 查进程
        # 2. 读日志/SQLite/JSON
        # 3. 返回状态
        pass
```

## 社区

- [Issues](https://github.com/988hj7tczd-oss/aihouse/issues) - 问题反馈
- [Discussions](https://github.com/988hj7tczd-oss/aihouse/discussions) - 讨论交流
