#!/usr/bin/env python3
"""生成 CommondX 应用图标 - 白底橙色版"""

import math
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

SCRIPT_DIR = Path(__file__).parent
ORANGE = (255, 90, 60)
WHITE = (255, 255, 255)


def create_icon(size):
    scale = 8
    real_size = size * scale
    img = Image.new('RGBA', (real_size, real_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 1. 白色背景 & 圆角
    margin = int(real_size * 0.08)
    corner_r = int(real_size * 0.22)
    
    # 绘制背景
    mask = Image.new('L', (real_size, real_size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [margin, margin, real_size - margin, real_size - margin], 
        radius=corner_r, fill=255)
    
    bg = Image.new('RGBA', (real_size, real_size), (0, 0, 0, 0))
    # 白色实心背景
    bg_draw = ImageDraw.Draw(bg)
    bg_draw.rectangle([0, 0, real_size, real_size], fill=WHITE)
    
    # 裁剪背景
    final_img = Image.new('RGBA', (real_size, real_size), (0, 0, 0, 0))
    final_img.paste(bg, mask=mask)
    draw = ImageDraw.Draw(final_img)

    # 2. 剪刀绘制 (橙色)
    s = real_size / 22.0 * 0.8
    cx, cy = real_size / 2, real_size / 2
    orig_center = (11, 11)
    line_w = 1.5 * s

    def to_pixel(x, y):
        return cx + (x - orig_center[0]) * s, cy - (y - orig_center[1]) * s

    def rotate(pt, angle):
        rad = math.radians(angle)
        dx, dy = pt[0] - to_pixel(*orig_center)[0], pt[1] - to_pixel(*orig_center)[1]
        c = to_pixel(*orig_center)
        return c[0] + dx * math.cos(rad) - dy * math.sin(rad), \
               c[1] + dx * math.sin(rad) + dy * math.cos(rad)

    def draw_blade(oval_rect, start, end, angle):
        ox, oy, w, h = oval_rect
        pt_oval_c = to_pixel(ox + w/2, oy + h/2)
        oval_w, oval_h = w * s, h * s
        rot_angle = -angle 
        
        pt_s = to_pixel(*start)
        pt_e = to_pixel(*end)
        
        r_s, r_e = rotate(pt_s, rot_angle), rotate(pt_e, rot_angle)
        r_oval_c = rotate(pt_oval_c, rot_angle)

        # 1. 刀身 (橙色)
        draw.line([r_s, r_e], fill=ORANGE, width=int(line_w))
        
        # 2. 手柄圆环 (橙色实心)
        bbox = [r_oval_c[0] - oval_w/2, r_oval_c[1] - oval_h/2,
                r_oval_c[0] + oval_w/2, r_oval_c[1] + oval_h/2]
        draw.ellipse(bbox, fill=ORANGE)
        
        # 3. 挖空内圆 (白色)
        r_in = oval_w/2 - line_w
        draw.ellipse([r_oval_c[0]-r_in, r_oval_c[1]-r_in, 
                      r_oval_c[0]+r_in, r_oval_c[1]+r_in], fill=WHITE)

    draw_blade((4, 3, 5, 5), (6.5, 6.5), (16, 19), 0)
    draw_blade((13, 3, 5, 5), (15.5, 6.5), (6, 19), 0)

    return final_img.resize((size, size), Image.Resampling.LANCZOS)


def main():
    iconset_dir = SCRIPT_DIR / "CommondX.iconset"
    iconset_dir.mkdir(exist_ok=True)
    
    for size in [16, 32, 64, 128, 256, 512]:
        create_icon(size).save(iconset_dir / f"icon_{size}x{size}.png")
        if size <= 256:
            create_icon(size * 2).save(iconset_dir / f"icon_{size}x{size}@2x.png")
            
    create_icon(512).save(SCRIPT_DIR / "CommondX.png")
    
    icns_path = SCRIPT_DIR / "CommondX.icns"
    if subprocess.run(["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)]).returncode == 0:
        shutil.rmtree(iconset_dir)
        print(f"✅ 图标已生成: {icns_path}")
    else:
        print("❌ 生成失败")


if __name__ == "__main__":
    main()
