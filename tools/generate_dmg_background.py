#!/usr/bin/env python3
"""生成 DMG 安装背景图"""

from pathlib import Path
import cv2
import numpy as np
from cedar.draw import putText

def create_dmg_background():
    w, h = 640, 480
    bg = np.full((h, w, 3), (250, 250, 250)[::-1], np.uint8)
    
    # 虚线箭头
    y = 240
    for x in range(240, 400, 20):
        cv2.line(bg, (x, y), (min(x + 10, 400), y), (60, 90, 255), 2)
    
    # 箭头头部
    cv2.fillPoly(bg, [np.array([[400, y], [390, y-6], [390, y+6]], np.int32)], (60, 90, 255))
    
    # 文字
    # 文字 (中文) - 使用 putText
    text = "拖拽到 Applications 文件夹安装"
    bg = putText(bg, text, (200, h-100), 
                 text_color=(10, 10, 10), text_size=18)
    
    cv2.imwrite(str(Path(__file__).parent / "dmg_background.png"), bg)
    print("✅ DMG 背景图已生成")

if __name__ == "__main__":
    create_dmg_background()
