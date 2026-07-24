# 常见问题

## 安装与启动

### aihouse 命令找不到？

```bash
# 确认安装了
pip install aihouse

# 确认 pip 安装路径在 PATH 中
pip show aihouse | grep Location
```

### aihouse start 报错 "加载配置失败"？

```bash
# 确保先初始化
aihouse init

# 检查配置文件格式
cat ~/.aihouse/config.yaml
```

### 端口 9800 被占用？

```bash
# 查看谁占用了端口
lsof -i :9800

# 或换端口（需修改 config.yaml 中的端口配置）
```

---

## 监控相关

### Agent 状态一直显示 not_running？

可能的原因：

1. Agent 确实没安装 → 运行 `aihouse detect` 确认
2. Agent 进程名与适配器配置不匹配 → 检查适配器的进程名
3. Agent 日志路径不对 → 检查 `~/.claude/logs/` 是否存在

### 为什么 Agent 显示 idle 而不是 active？

Agent 空闲状态是正常的。只有当 Agent 正在执行任务时才显示 active。

### 卡住检测不准？

可以在配置中调整卡住阈值：

```yaml
agents:
  - name: "Claude Code"
    type: claude_code
    stuck_threshold: 600  # 改为 10 分钟无活动才告警
```

---

## 桌面端

### 桌面端一片空白？

```bash
# 1. 确认后端已启动
aihouse status

# 2. 确认 API 可用
curl http://127.0.0.1:9800/api/health

# 3. 如果 API 不可用，重启后端
aihouse restart
```

### 桌面端编译失败？

```bash
# 确认 Rust 和 Node.js 已安装
rustc --version
node --version
npm --version

# 重新安装依赖
cd desktop
rm -rf node_modules src-tauri/target
npm install
npm run tauri dev
```

---

## 费用监控

### 费用显示为 0？

```bash
# 检查 API Key 是否已配置
cat ~/.aihouse/.env

# 确认配置了正确的 provider
cat ~/.aihouse/config.yaml | grep -A3 api_cost
```

### 费用查询失败？

确认 API Key 有效且账户有使用记录。

---

## 卸载

```bash
pip uninstall aihouse
rm -rf ~/.aihouse
```
