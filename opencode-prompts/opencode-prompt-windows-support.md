# Windows 全平台适配 — Agent 检测路径 + 桌面端 + API 完整跨平台支持

## 背景

AIHouse 项目路径 `~/Projects/aihouse/`。当前代码在 macOS 上正常运行，但多个 adapter 和 CLI 中有硬编码的 macOS/Linux 路径，在 Windows 上检测不到 agent 或跑不起来。

目标：**所有功能在 Windows 上跟 macOS 一模一样**——识别 Hermes、OpenCode、Cursor 等已安装 agent，正确显示状态和任务。

## 已知 Windows 路径问题

### 问题 1：OpenCode DB 路径 `opencode.py:18`

```python
# 当前 — Linux/macOS 专用
OPENCODE_DB = Path.home() / ".local" / "share" / "opencode" / "opencode.db"
```

Windows 上 OpenCode 的数据库位于 `%APPDATA%\opencode\opencode.db`（即 `C:\Users\<用户名>\AppData\Roaming\opencode\opencode.db`）。

修复：判断 `IS_WINDOWS` 时用 `Path(os.environ.get('APPDATA', '')) / "opencode" / "opencode.db"`

### 问题 2：Cursor 应用路径 `cursor.py:27`

```python
# 当前 — macOS 专用
if Path("/Applications/Cursor.app").exists():
```

Windows 上 Cursor 位于 `%LOCALAPPDATA%\Programs\Cursor\`（即 `C:\Users\<用户名>\AppData\Local\Programs\Cursor\Cursor.exe`）。

修复：判断 `IS_WINDOWS` 时检查 `Path(os.environ.get('LOCALAPPDATA', '')) / "Programs" / "Cursor" / "Cursor.exe"`

另外 Cursor 的 `~/.cursor` 目录检测也去掉——它只是配置残留，不是安装证据。

### 问题 3：Claude Code 日志目录 `claude_code.py:11,26`

```python
# 当前 — Linux/macOS 专用
CLAUDE_LOG_DIR = Path.home() / ".claude" / "logs"
# detect() 中
if Path.home().joinpath(".claude").is_dir():
```

Windows 上 Claude Code 数据位于 `%APPDATA%\Claude\`。

### 问题 4：config.py 中 KNOWN_AGENTS 的 dirs

```python
# 第 33 行 — Linux/macOS 专用
{"name": "OpenCode", "dirs": ["~/.local/share/opencode"], ...}
```

Windows 上需要改为 `%APPDATA%\opencode\`。

### 问题 5：CLI 桌面端二进制路径 `cli.py`

```python
# 第 71 行 — macOS 专用
candidates.append("/Applications/AIHouse.app/Contents/MacOS/aihouse")
# 第 76 行 — Linux 专用
candidates.append(os.path.expanduser("~/.local/bin/aihouse-desktop"))
```

Windows 的路径已经有了（73-74 行），但需要补上 Windows 的 Tauri dev 构建路径：
```python
# Windows dev 构建
Path("target/release/aihouse.exe")  # 或 aihouse.exe
```

### 问题 6：`kilo_code.py` 和 `cline.py` 的 VS Code 扩展路径

```python
# 当前 — Linux/macOS 专用
Path.home() / ".vscode" / "extensions",
Path.home() / ".vscode-insiders" / "extensions",
```

Windows 上 VS Code 扩展位于 `%USERPROFILE%\.vscode\extensions\` 和 `%USERPROFILE%\.vscode-insiders\extensions\`。

实际上 `Path.home() / ".vscode"` 在 Windows 上也能正确展开为 `C:\Users\<用户名>\.vscode\`，所以这个路径可能是对的。但需要确认 Windows 测试机上是否存在。

### 问题 7：Hermes 适配器

Hermes 的路径 `Path.home() / ".hermes"` 在 Windows 上可以正确展开。无需改动。

### 问题 8：aihose 主进程 PID/LOG 文件 `cli.py`

```python
PID_FILE = os.path.expanduser("~/.aihouse/aihouse.pid")
LOG_FILE = os.path.expanduser("~/.aihouse/aihouse.log")
```

`os.path.expanduser("~/.aihouse")` 在 Windows 上展开为 `C:\Users\<用户名>\.aihouse\`，能工作但不遵循 Windows 惯例（应该放 `%APPDATA%\AIHouse\` 或 `%LOCALAPPDATA%\AIHouse\`）。

这个改动影响较大且是设计偏好问题，暂时不改，保留为 `~/.aihouse`（能工作）。

## 修改范围

| 文件 | 要改的路径 |
|------|-----------|
| `src/aihouse/adapters/opencode.py` | OPENCODE_DB 路径（Windows 用 `%APPDATA%`） |
| `src/aihouse/adapters/cursor.py` | `/Applications/Cursor.app` 加 Windows 分支，去掉 `~/.cursor` 检测 |
| `src/aihouse/adapters/claude_code.py` | CLAUDE_LOG_DIR 路径（Windows 用 `%APPDATA%`） |
| `src/aihouse/adapters/kilo_code.py` | 扩展路径加 Windows 分支 |
| `src/aihouse/adapters/cline.py` | 同上 |
| `src/aihouse/config.py` | KNOWN_AGENTS 中 OpenCode 的 dirs 路径 |
| `src/aihouse/cli.py` | macOS 专属桌面路径加 IS_WINDOWS 分支 |

## 通用修复模式（每个 adapter 统一写法）

在文件顶部加 Windows 路径常量：

```python
import os

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    APP_DATA = Path(os.environ.get("APPDATA", ""))
    LOCAL_APP_DATA = Path(os.environ.get("LOCALAPPDATA", ""))
```

检测函数中对不同平台用不同路径：

```python
def detect(self) -> bool:
    if shutil.which("cursor") is not None:
        return True
    if IS_WINDOWS:
        cursor_exe = LOCAL_APP_DATA / "Programs" / "Cursor" / "Cursor.exe"
        if cursor_exe.exists():
            return True
    else:
        if Path("/Applications/Cursor.app").exists():
            return True
    return False
```

## 验证方式

在 Windows 测试机上：

```bash
aihouse status
# 应显示实际安装的 agent（Hermes、OpenCode、Cursor 等）
# 不应显示未安装的 agent

curl -s http://127.0.0.1:9800/api/status
# 检查每个 agent 的活动状态和任务描述
```

## 注意

- 保持 `IS_WINDOWS` 变量统一（每个文件已有）
- `shutil.which()` 和 `Path.home()` 是跨平台的，保留使用
- 改动后确保 macOS 上原有的 detect() 路径不受影响
- Windows 上的 `%APPDATA%` 是 `C:\Users\<用户名>\AppData\Roaming\`
- Windows 上的 `%LOCALAPPDATA%` 是 `C:\Users\<用户名>\AppData\Local\`
