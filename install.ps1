Write-Host "📦 安装 AIHouse..." -ForegroundColor Cyan

pip install aihouse

aihouse init

aihouse detect

Write-Host ""
Write-Host "📱 构建桌面端..."
Write-Host ""
Write-Host "  cd desktop && npm install && npm run tauri build"
Write-Host ""

Write-Host "✅ AIHouse 安装完成！" -ForegroundColor Green
Write-Host "运行 aihouse start 启动监控"
Write-Host "运行 aihouse desktop 打开桌面端"
