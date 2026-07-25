#!/bin/bash
set -e

echo "📦 安装 AIHouse..."

pip install aihouse 2>/dev/null || pip install --user aihouse

aihouse init

aihouse detect

echo ""
echo "📱 构建桌面端..."
echo ""
echo "  cd desktop && npm install && npm run tauri build"
echo ""

echo "✅ AIHouse 安装完成！"
echo ""
echo "运行 aihouse start 启动监控"
echo "运行 aihouse desktop 打开桌面端"
