#!/usr/bin/env python3
"""生成 CommondX 应用图标 - 基于状态栏图标复刻版"""

import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

SCRIPT_DIR = Path(__file__).parent
BG_TOP = (255, 100, 60)
BG_BOTTOM = (235, 70, 40)
WHITE = (255, 255, 255)

def create_final_icon(size):
    scale = 8  # 超高采样以获得完美圆滑度
    real_size = size * scale
    img = Image.new('RGBA', (real_size, real_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 1. 背景 (垂直渐变)
    margin = int(real_size * 0.08)
    corner_r = int(real_size * 0.22)
    
    for y in range(margin, real_size - margin):
        ratio = (y - margin) / (real_size - 2 * margin)
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * ratio)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * ratio)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * ratio)
        draw.line([(margin, y), (real_size - margin, y)], fill=(r, g, b), width=1)
    
    # 裁剪圆角
    mask = Image.new('L', (real_size, real_size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [margin, margin, real_size - margin, real_size - margin], 
        radius=corner_r, fill=255)
    
    bg = Image.new('RGBA', (real_size, real_size), (0, 0, 0, 0))
    bg.paste(img, mask=mask)
    img = bg
    draw = ImageDraw.Draw(img)

    # 2. 绘制剪刀 (复刻状态栏图标比例)
    # 状态栏图标坐标系是 22x22
    # 我们将其映射到 real_size
    
    s = real_size / 22.0 * 0.7  # 缩放系数 (留出边距)
    cx, cy = real_size / 2, real_size / 2
    
    # 原始坐标系中心大约在 (11, 11)
    # 状态栏绘制逻辑：
    # 左臂: 圆(4,3) d=5; 线(6.5,8) -> (16,19)
    # 右臂: 圆(13,3) d=5; 线(15.5,8) -> (6,19)
    
    # 我们需要将坐标原点从左下角(NSView默认)改为左上角(PIL默认)，并居中
    # 原始坐标范围大致 x:[4, 18], y:[3, 19]
    # 中心点大约 (11, 11)
    
    offset_x = cx - 11 * s
    offset_y = cy - 11 * s
    
    line_width = 2.0 * s  # 线条宽度
    
    # 绘制函数
    def draw_part(is_left):
        if is_left:
            # 左臂（在图标中其实对应右半部分的手柄和左半部分的刀尖）
            # 圆 (4, 3) 5x5 => 这里的坐标其实是相对于左下角的
            # 我们假设 status_bar.py 是标准的 Cocoa 坐标系 (原点左下)
            # 那么 y=3 是底部，y=19 是顶部
            # 但看 status_bar.py 的代码，剪刀是倒着的？或者坐标系被转换了？
            # 让我们直接按视觉效果重构：
            # 手柄在底部，刀尖在顶部。
            
            # 重新定义标准坐标：
            # 刀尖向上：(0, -10)
            # 手柄向下：(-5, 8) 和 (5, 8)
            
            pass 
        pass

    # 还是直接按几何画最稳
    # 状态栏那个是 "X" 形状
    
    # 左臂：从右上(手柄) 到 左下(刀尖)
    # 右臂：从左上(手柄) 到 右下(刀尖)
    # 我们的图标通常是刀尖朝左下或右上
    
    # 采用标准图标姿势：
    # 刀尖指向 左下 (对应 -45度)
    # 手柄在 右上
    
    # 定义几何参数
    blade_length = 10 * s # 刀刃长
    handle_dist = 6 * s   # 手柄离中心距离
    handle_r = 2.5 * s    # 手柄半径
    
    import math
    
    # 旋转 -45 度 (刀尖指左下)
    # 实际上我们希望是一个正 X 形状然后旋转
    # 臂1：(-10, 0) -- (10, 0)
    # 臂2：(0, -10) -- (0, 10)  <- 这样是十字
    
    # 剪刀是： >-< 形状
    # 臂1：左上刀尖 <-> 右下手柄
    # 臂2：左下刀尖 <-> 右上手柄
    
    rot = math.radians(-45)
    cos_a, sin_a = math.cos(rot), math.sin(rot)
    
    def transform(x, y):
        # 旋转 + 平移
        rx = x * cos_a - y * sin_a
        ry = x * sin_a + y * cos_a
        return cx + rx, cy + ry
    
    # 绘制单个臂
    def draw_arm(mirror=False):
        sign = -1 if mirror else 1
        
        # 关键点 (水平放置时的坐标)
        # 刀尖 (左)
        p_tip = (-8 * s, 0)
        # 手柄连接点 (右)
        p_conn = (5 * s, 0)
        # 手柄圆心
        p_handle = (7.5 * s, 3 * s * sign) # 稍微错开
        
        # 修正：剪刀的两臂是交叉直线的
        # 臂1：左刀尖 <-> 右手柄
        # 臂2：左刀尖 <-> 右手柄 (镜像)
        
        # 让我们画两根交叉的棒槌
        # 棒槌中心在 (0,0)
        
        # 偏移角度
        angle = math.radians(15 * sign)
        dx = math.cos(angle)
        dy = math.sin(angle)
        
        len_tip = 10 * s
        len_handle = 6 * s
        
        # 刀尖点
        t_tip = (-len_tip * dx, -len_tip * dy)
        # 手柄点
        t_handle = (len_handle * dx, len_handle * dy)
        
        # 转换坐标
        pt1 = transform(*t_tip)
        pt2 = transform(*t_handle)
        
        # 绘制杆子
        draw.line([pt1, pt2], fill=WHITE, width=int(line_width))
        
        # 绘制手柄圆圈
        r = 3.5 * s
        h_center = transform(t_handle[0] + (r-1*s)*dx, t_handle[1] + (r-1*s)*dy)
        
        bbox = [h_center[0]-r, h_center[1]-r, h_center[0]+r, h_center[1]+r]
        
        # 实心白圆
        draw.ellipse(bbox, fill=WHITE)
        
        # 挖空内圆 (用背景色)
        r_in = r - line_width * 0.4
        bbox_in = [h_center[0]-r_in, h_center[1]-r_in, h_center[0]+r_in, h_center[1]+r_in]
        
        # 采样该位置背景色
        bg_y = int(max(margin, min(real_size-margin, h_center[1])))
        ratio = (bg_y - margin) / (real_size - 2 * margin)
        bg_r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * ratio)
        bg_g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * ratio)
        bg_b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * ratio)
        
        draw.ellipse(bbox_in, fill=(bg_r, bg_g, bg_b))

    draw_arm(False) # 上臂
    draw_arm(True)  # 下臂
    
    # 中心点
    pivot_r = line_width * 0.7
    draw.ellipse([cx-pivot_r, cy-pivot_r, cx+pivot_r, cy+pivot_r], fill=WHITE)
    
    # 中心孔
    hole_r = pivot_r * 0.4
    # 采样中心背景色
    ratio = 0.5
    bg_r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * ratio)
    bg_g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * ratio)
    bg_b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * ratio)
    draw.ellipse([cx-hole_r, cy-hole_r, cx+hole_r, cy+hole_r], fill=(bg_r, bg_g, bg_b))

    return img.resize((size, size), Image.Resampling.LANCZOS)

def create_iconset():
    iconset_dir = SCRIPT_DIR / "CommondX.iconset"
    iconset_dir.mkdir(exist_ok=True)
    
    for size in [16, 32, 64, 128, 256, 512]:
        create_final_icon(size).save(iconset_dir / f"icon_{size}x{size}.png")
        if size <= 256:
            create_final_icon(size * 2).save(iconset_dir / f"icon_{size}x{size}@2x.png")
            
    create_final_icon(512).save(SCRIPT_DIR / "CommondX.png")
    
    icns_path = SCRIPT_DIR / "CommondX.icns"
    subprocess.run(["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)])
    shutil.rmtree(iconset_dir)
    print(f"✅ 图标生成完毕: {icns_path}")

if __name__ == "__main__":
    create_iconset()
