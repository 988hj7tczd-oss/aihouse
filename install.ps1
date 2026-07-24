Write-Host ""
Write-Host "  ╔═══════════════════════════════════════╗"
Write-Host "  ║       AIHouse - AI Agent Monitor      ║"
Write-Host "  ╚═══════════════════════════════════════╝"
Write-Host ""

Write-Host "📦 安装 AIHouse..." -ForegroundColor Cyan

# 从 GitHub Release 安装
pip install https://github.com/988hj7tczd-oss/aihouse/releases/download/v0.1.0/aihouse-0.1.0-py3-none-any.whl 2>$null

# 初始化
aihouse init 2>$null

Write-Host ""
Write-Host "✅ AIHouse 安装完成！" -ForegroundColor Green
Write-Host ""
Write-Host "   aihouse start     启动监控"
Write-Host "   aihouse status    查看状态"
Write-Host "   aihouse desktop   打开桌面端"
Write-Host ""
