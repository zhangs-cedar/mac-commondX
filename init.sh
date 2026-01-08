#!/bin/bash
# 重置 CommondX 到初始状态

echo "🔄 重置 CommondX..."

# 1. 清除辅助功能授权
tccutil reset Accessibility com.liuns.commondx 2>/dev/null && echo "✅ 已清除辅助功能授权" || echo "⚠️ 无需清除授权"

# 2. 删除用户数据（激活码、试用开始时间）
USER_DATA=~/Library/Application\ Support/CommondX/user.yaml
if [ -f "$USER_DATA" ]; then
    rm "$USER_DATA"
    echo "✅ 已删除用户数据"
else
    echo "⚠️ 用户数据不存在"
fi

# 3. 删除日志
rm -rf ~/Library/Logs/CommondX*.log 2>/dev/null && echo "✅ 已清除日志"

echo "🎉 重置完成！"
