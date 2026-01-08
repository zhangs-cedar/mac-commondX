#!/usr/bin/env python3
"""生成 DMG 安装背景图 - 匹配新版图标风格"""

from pathlib import Path
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "Pillow"], check=True)
    from PIL import Image, ImageDraw, ImageFont

def create_dmg_background():
    """创建简约 DMG 背景图"""
    width, height = 640, 480
    bg_color = (250, 250, 250)  # 近似纯白，带一点暖色
    arrow_color = (255, 90, 60)  # 与图标一致的橙色
    
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # 绘制简单的箭头 (从图标指向 Applications)
    # 箭头位置调整：图标大概在 (160, 240)，App文件夹在 (480, 240)
    arrow_y = 240
    arrow_start = 240  # 图标右侧
    arrow_end = 400    # 文件夹左侧
    
    # 虚线箭头
    dash_len = 10
    for x in range(arrow_start, arrow_end, dash_len * 2):
        draw.line([(x, arrow_y), (min(x + dash_len, arrow_end), arrow_y)], 
                 fill=arrow_color, width=2)
    
    # 箭头头部
    draw.polygon([
        (arrow_end, arrow_y),
        (arrow_end - 10, arrow_y - 6),
        (arrow_end - 10, arrow_y + 6),
    ], fill=arrow_color)
    
    # 文字提示
    try:
        font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 13)
    except:
        font = ImageFont.load_default()
    
    text = "Drag to install"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    draw.text(((width - text_w)//2, height - 100), text, fill=(150, 150, 150), font=font)
    
    output_path = Path(__file__).parent / "dmg_background.png"
    img.save(output_path, "PNG")
    print(f"✅ DMG 背景图已生成: {output_path}")

if __name__ == "__main__":
    create_dmg_background()
