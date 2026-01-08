#!/usr/bin/env python3
"""生成 DMG 安装背景图"""

from pathlib import Path
import cv2
import numpy as np
from cedar.draw import putText

def create_dmg_background():
    width, height = 640, 480
    bg_color = (250, 250, 250)  # RGB
    arrow_color = (60, 90, 255)  # BGR (橙色)
    
    # 创建白色背景 (BGR)
    img = np.full((height, width, 3), bg_color[::-1], dtype=np.uint8)
    
    # 箭头 (图标 -> Applications)
    arrow_y = 240
    arrow_start, arrow_end = 240, 400
    
    # 虚线
    for x in range(arrow_start, arrow_end, 20):
        cv2.line(img, (x, arrow_y), (min(x + 10, arrow_end), arrow_y), 
                arrow_color, 2)
    
    # 箭头头部
    pts = np.array([
        [arrow_end, arrow_y],
        [arrow_end - 10, arrow_y - 6],
        [arrow_end - 10, arrow_y + 6]
    ], np.int32)
    cv2.fillPoly(img, [pts], arrow_color)
    
    # 文字 (中文) - 使用 putText
    text = "拖拽到 Applications 文件夹安装"
    img = putText(img, text, (200, height - 100), 
                 text_color=(10, 10, 10), text_size=18)
    
    # 保存 (OpenCV 使用 BGR，PIL 需要 RGB)
    output_path = Path(__file__).parent / "dmg_background.png"
    cv2.imwrite(str(output_path), img)
    print(f"✅ DMG 背景图已生成: {output_path}")

if __name__ == "__main__":
    create_dmg_background()
