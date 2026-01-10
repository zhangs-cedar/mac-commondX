#!/bin/bash
# 重置 CommondX 到初始状态

echo "🔄 重置 CommondX..."

# 1. 清除辅助功能授权
tccutil reset Accessibility com.liuns.commondx 2>/dev/null && echo "✅ 已清除辅助功能授权" || echo "⚠️ 无需清除授权"

# 2. 删除用户数据（激活码、试用开始时间）
# 注意：路径包含空格，必须使用引号
APP_DATA_DIR="$HOME/Library/Application Support/CommondX"
config="$APP_DATA_DIR/config.yaml"
license="$APP_DATA_DIR/license.yaml"

echo "📁 数据目录: $APP_DATA_DIR"

# 删除配置文件
if [ -f "$config" ]; then
    rm -f "$config"
    echo "✅ 已删除配置文件"
else
    echo "ℹ️  配置文件不存在"
fi

# 删除许可证文件
if [ -f "$license" ]; then
    rm -f "$license"
    echo "✅ 已删除许可证文件"
else
    echo "ℹ️  许可证文件不存在"
fi

# 列出剩余文件
echo ""
echo "📋 剩余文件："
if [ -d "$APP_DATA_DIR" ]; then
    ls -la "$APP_DATA_DIR" 2>/dev/null || echo "   (目录为空)"
else
    echo "   (目录不存在)"
fi

echo ""
echo "🎉 重置完成！"
