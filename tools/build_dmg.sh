#!/bin/bash
# CommondX 打包脚本 - 现代化 DMG

set -e

cd "$(dirname "$0")/.."

APP_NAME="CommondX"
VERSION="1.0.0"
TOOLS_DIR="tools"

echo "=== $APP_NAME 打包 ==="

# 清除旧的辅助功能授权记录
tccutil reset Accessibility com.liuns.commondx 2>/dev/null || true

rm -rf build dist *.dmg

# 构建应用
pyinstaller tools/CommondX.spec --noconfirm

# 检查 create-dmg 是否安装
if ! command -v create-dmg &> /dev/null; then
    echo "⚠️  create-dmg 未安装，正在安装..."
    brew install create-dmg
fi

# 删除旧的 DMG（create-dmg 不会覆盖）
rm -f "dist/${APP_NAME}-${VERSION}.dmg"

# 创建现代化 DMG
echo "=== 创建 DMG ==="
create-dmg \
    --volname "$APP_NAME" \
    --volicon "$TOOLS_DIR/CommondX.icns" \
    --background "$TOOLS_DIR/dmg_background.png" \
    --window-pos 200 120 \
    --window-size 640 480 \
    --icon-size 128 \
    --icon "$APP_NAME.app" 160 240 \
    --hide-extension "$APP_NAME.app" \
    --app-drop-link 480 240 \
    --no-internet-enable \
    "dist/${APP_NAME}-${VERSION}.dmg" \
    "dist/$APP_NAME.app"

echo "=== 完成: dist/${APP_NAME}-${VERSION}.dmg ==="
