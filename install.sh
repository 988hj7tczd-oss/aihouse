#!/bin/bash
set -e

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║       AIHouse - AI Agent Monitor      ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""

# 检测 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 请先安装 Python 3.9+"
    echo "   https://www.python.org/downloads/"
    exit 1
fi

echo "📦 安装 AIHouse..."

# 从 GitHub Release 安装
pip install https://github.com/988hj7tczd-oss/aihouse/releases/download/v0.1.0/aihouse-0.1.0-py3-none-any.whl 2>/dev/null

# 初始化
aihouse init 2>/dev/null

echo ""
echo "✅ AIHouse 安装完成！"
echo ""
echo "   aihouse start     启动监控"
echo "   aihouse status    查看状态"
echo "   aihouse desktop   打开桌面端"
echo ""
