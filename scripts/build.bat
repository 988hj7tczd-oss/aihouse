@echo off
echo === 构建 Python 包 ===
cd /d "%~dp0.."
pip install build -q
python -m build
echo Python 包: dist/

echo === 构建桌面端 ===
cd desktop
call npm install --silent
call npm run tauri build
echo 桌面安装包: desktop/src-tauri/target/release/bundle/

echo === 完成 ===
