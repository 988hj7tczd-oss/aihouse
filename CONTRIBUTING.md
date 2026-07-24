# Contributing to AIHouse

我们欢迎任何形式的贡献！无论是新功能、bug 修复、文档改进，还是适配新的 Agent。

## 开发流程

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feat/your-feature`
3. 提交改动：`git commit -m "feat: add xxx"`
4. 推送到分支：`git push origin feat/your-feature`
5. 创建 Pull Request

## 添加新的 Agent 适配器

参考 `docs/adapters.md` 和已有的适配器示例：

```python
from aioutpost.core.adapter import AgentAdapter
from aioutpost.core.models import AgentStatus, AgentTask

class MyAgentAdapter(AgentAdapter):
    name = "My Agent"
    agent_type = "my_agent"
    
    def detect(self) -> bool:
        return shutil.which("my-agent") is not None
    
    def get_status(self) -> AgentStatus:
        # 实现状态检测
        pass
```

## 代码规范

- Python 3.9+，类型注解
- 中文注释，关键逻辑写清楚
- 每个公开函数有 docstring
- 路径统一用 `pathlib.Path`

## 提交规范

参考 [Conventional Commits](https://www.conventionalcommits.org/)：

- `feat:` 新功能
- `fix:` 修复
- `docs:` 文档
- `refactor:` 重构
- `test:` 测试
- `chore:` 杂项

## 问题反馈

提交 Issue 时请提供：
- 操作系统版本
- Python 版本
- 错误日志（剪切板）
- 复现步骤
