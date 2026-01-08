#!/usr/bin/env python3
"""生成 CommondX 应用图标 - 剪刀风格 macOS 图标"""

import subprocess
import tempfile
import os
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("安装 Pillow...")
    subprocess.run(["pip", "install", "Pillow"], check=True)
    from PIL import Image, ImageDraw


def draw_scissors(draw, size, color):
    """绘制剪刀图案"""
    cx, cy = size // 2, size // 2
    scale = size / 512
    
    # 剪刀参数
    blade_len = int(180 * scale)
    handle_r = int(50 * scale)
    blade_w = int(20 * scale)
    pivot_r = int(15 * scale)
    
    # 上刀片 (左上到中心)
    angle_up = -35
    import math
    rad_up = math.radians(angle_up)
    bx1 = cx - blade_len * math.cos(rad_up)
    by1 = cy - blade_len * math.sin(rad_up)
    
    # 下刀片 (左下到中心)
    angle_down = 35
    rad_down = math.radians(angle_down)
    bx2 = cx - blade_len * math.cos(rad_down)
    by2 = cy + blade_len * math.sin(rad_down)
    
    # 绘制刀片 (加粗线条模拟)
    for offset in range(-blade_w//2, blade_w//2 + 1):
        draw.line([(bx1, by1 + offset), (cx, cy + offset)], fill=color, width=2)
        draw.line([(bx2, by2 + offset), (cx, cy + offset)], fill=color, width=2)
    
    # 刀片三角形尖端
    tip_len = int(60 * scale)
    tip_w = int(25 * scale)
    
    # 上刀尖
    draw.polygon([
        (bx1 - tip_len * math.cos(rad_up), by1 - tip_len * math.sin(rad_up)),
        (bx1, by1 - tip_w),
        (bx1, by1 + tip_w),
    ], fill=color)
    
    # 下刀尖
    draw.polygon([
        (bx2 - tip_len * math.cos(rad_down), by2 + tip_len * math.sin(rad_down)),
        (bx2, by2 - tip_w),
        (bx2, by2 + tip_w),
    ], fill=color)
    
    # 手柄环 (右侧)
    handle_cx_up = cx + int(100 * scale)
    handle_cy_up = cy - int(70 * scale)
    handle_cx_down = cx + int(100 * scale)
    handle_cy_down = cy + int(70 * scale)
    
    ring_outer = handle_r
    ring_inner = int(handle_r * 0.5)
    ring_w = int(12 * scale)
    
    # 上手柄环
    draw.ellipse([
        handle_cx_up - ring_outer, handle_cy_up - ring_outer,
        handle_cx_up + ring_outer, handle_cy_up + ring_outer
    ], outline=color, width=ring_w)
    
    # 下手柄环
    draw.ellipse([
        handle_cx_down - ring_outer, handle_cy_down - ring_outer,
        handle_cx_down + ring_outer, handle_cy_down + ring_outer
    ], outline=color, width=ring_w)
    
    # 连接手柄到中心
    conn_w = int(15 * scale)
    draw.line([(cx, cy - int(10 * scale)), (handle_cx_up - ring_outer + ring_w, handle_cy_up)], 
              fill=color, width=conn_w)
    draw.line([(cx, cy + int(10 * scale)), (handle_cx_down - ring_outer + ring_w, handle_cy_down)], 
              fill=color, width=conn_w)
    
    # 中心铆钉
    draw.ellipse([
        cx - pivot_r, cy - pivot_r,
        cx + pivot_r, cy + pivot_r
    ], fill=color)


def create_icon(size):
    """创建单个尺寸的图标"""
    # 创建带圆角的背景
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 背景颜色 - 温暖的橙红色渐变效果
    margin = int(size * 0.08)
    corner_r = int(size * 0.22)
    
    # 绘制圆角矩形背景
    bg_color = (255, 90, 60)  # 活力橙红
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=corner_r,
        fill=bg_color
    )
    
    # 添加微妙的高光效果
    highlight_color = (255, 130, 100)
    hl_margin = int(size * 0.12)
    hl_height = int(size * 0.35)
    draw.rounded_rectangle(
        [hl_margin, hl_margin, size - hl_margin, hl_margin + hl_height],
        radius=int(corner_r * 0.8),
        fill=highlight_color
    )
    
    # 重新绘制主背景（覆盖高光下半部分）
    draw.rounded_rectangle(
        [margin, int(size * 0.3), size - margin, size - margin],
        radius=corner_r,
        fill=bg_color
    )
    
    # 绘制剪刀
    draw_scissors(draw, size, (255, 255, 255))
    
    return img


def create_iconset():
    """创建 iconset 并转换为 icns"""
    script_dir = Path(__file__).parent
    iconset_dir = script_dir / "CommondX.iconset"
    iconset_dir.mkdir(exist_ok=True)
    
    # macOS 图标尺寸
    sizes = [16, 32, 64, 128, 256, 512]
    
    for size in sizes:
        # 标准分辨率
        icon = create_icon(size)
        icon.save(iconset_dir / f"icon_{size}x{size}.png")
        
        # Retina (@2x)
        if size <= 256:
            icon_2x = create_icon(size * 2)
            icon_2x.save(iconset_dir / f"icon_{size}x{size}@2x.png")
    
    print(f"✅ 图标集已生成: {iconset_dir}")
    
    # 使用 iconutil 转换为 icns
    icns_path = script_dir / "CommondX.icns"
    result = subprocess.run(
        ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        print(f"✅ 图标文件已生成: {icns_path}")
        # 清理 iconset 目录
        import shutil
        shutil.rmtree(iconset_dir)
    else:
        print(f"❌ 转换失败: {result.stderr}")
        return None
    
    return icns_path


if __name__ == "__main__":
    create_iconset()
