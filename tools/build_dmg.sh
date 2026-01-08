#!/bin/bash
# CommondX 打包脚本

set -e

# 切换到项目根目录
cd "$(dirname "$0")/.."

APP_NAME="CommondX"
VERSION="1.0.0"

echo "=== $APP_NAME 打包 ==="

rm -rf build dist *.dmg

pyinstaller tools/CommondX.spec --noconfirm

DMG_TEMP="temp_dmg"
mkdir -p "$DMG_TEMP"
cp -r "dist/$APP_NAME.app" "$DMG_TEMP/"
ln -s /Applications "$DMG_TEMP/Applications"
hdiutil create -volname "$APP_NAME" -srcfolder "$DMG_TEMP" -ov -format UDZO "${APP_NAME}-${VERSION}.dmg"
rm -rf "$DMG_TEMP"

echo "=== 完成: ${APP_NAME}-${VERSION}.dmg ==="
