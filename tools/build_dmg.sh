#!/bin/bash
# CommondX 打包脚本

set -e

APP_NAME="CommondX"
VERSION="1.0.0"

echo "=== $APP_NAME 打包脚本 ==="

# 清理旧构建
echo "清理旧构建..."
rm -rf build dist *.dmg

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt -q

# 构建应用
echo "构建应用..."
pyinstaller CommondX.spec --noconfirm

# 检查构建结果
if [ ! -d "dist/$APP_NAME.app" ]; then
    echo "错误: 构建失败"
    exit 1
fi

echo "应用构建成功: dist/$APP_NAME.app"

# 创建 DMG
echo "创建 DMG..."

DMG_NAME="${APP_NAME}-${VERSION}.dmg"
DMG_TEMP="temp_dmg"

# 创建临时目录
rm -rf "$DMG_TEMP"
mkdir -p "$DMG_TEMP"

# 复制应用
cp -r "dist/$APP_NAME.app" "$DMG_TEMP/"

# 创建 Applications 快捷方式
ln -s /Applications "$DMG_TEMP/Applications"

# 创建 DMG
hdiutil create -volname "$APP_NAME" -srcfolder "$DMG_TEMP" -ov -format UDZO "$DMG_NAME"

# 清理
rm -rf "$DMG_TEMP"

echo "=== 打包完成 ==="
echo "DMG: $DMG_NAME"
echo ""
echo "安装方法："
echo "1. 双击 $DMG_NAME"
echo "2. 将 $APP_NAME 拖到 Applications 文件夹"
echo "3. 首次运行需要在 系统设置 > 隐私与安全 > 辅助功能 中授权"
