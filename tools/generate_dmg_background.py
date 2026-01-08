#!/usr/bin/env python3
"""生成 DMG 安装背景图 - 原生 macOS 风格"""

from pathlib import Path
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "Pillow"], check=True)
    from PIL import Image, ImageDraw, ImageFont


def create_dmg_background():
    """创建 DMG 背景图"""
    width, height = 640, 480
    
    # 创建渐变背景 - 浅灰色，macOS 原生风格
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    
    # 从上到下的微妙渐变
    for y in range(height):
        # 浅灰色渐变
        gray = int(245 - (y / height) * 15)
        draw.line([(0, y), (width, y)], fill=(gray, gray, gray))
    
    # 绘制箭头 (从 App 指向 Applications)
    arrow_y = 240
    arrow_start = 230
    arrow_end = 410
    arrow_color = (120, 120, 120)
    arrow_w = 3
    
    # 箭头主线
    draw.line([(arrow_start, arrow_y), (arrow_end - 20, arrow_y)], 
              fill=arrow_color, width=arrow_w)
    
    # 箭头头部
    arrow_head_size = 15
    draw.polygon([
        (arrow_end, arrow_y),
        (arrow_end - arrow_head_size, arrow_y - arrow_head_size // 2),
        (arrow_end - arrow_head_size, arrow_y + arrow_head_size // 2),
    ], fill=arrow_color)
    
    # 添加底部提示文字
    try:
        # 尝试使用系统字体
        font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 14)
    except:
        font = ImageFont.load_default()
    
    hint_text = "将 CommondX 拖到 Applications 文件夹"
    bbox = draw.textbbox((0, 0), hint_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_x = (width - text_width) // 2
    text_y = height - 60
    
    draw.text((text_x, text_y), hint_text, fill=(100, 100, 100), font=font)
    
    # 保存
    output_path = Path(__file__).parent / "dmg_background.png"
    img.save(output_path, "PNG")
    print(f"✅ DMG 背景图已生成: {output_path}")
    
    return output_path


if __name__ == "__main__":
    create_dmg_background()
