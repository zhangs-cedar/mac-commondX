#!/usr/bin/env python3
"""
PDF 编辑插件

打开 PDF24 工具网页（https://tools.pdf24.org/zh），提供免费的在线 PDF 操作工具。
"""

import subprocess
from pathlib import Path
from cedar.utils import print

# PDF24 工具网页地址
PDF24_URL = "https://tools.pdf24.org/zh"


def execute(files: list) -> tuple:
    """
    打开 PDF24 工具网页
    
    Args:
        files: 文件路径列表（可选，如果提供 PDF 文件，可以在网页中直接使用）
        
    Returns:
        tuple: (success: bool, message: str, None)
    """
    print(f"[DEBUG] [PdfEditorPlugin] 开始打开 PDF24 工具网页，文件数量={len(files) if files else 0}")
    try:
        # 检查是否有 PDF 文件
        pdf_files = []
        if files:
            for file_path in files:
                path = Path(file_path)
                if path.exists() and path.suffix.lower() == '.pdf':
                    pdf_files.append(str(path.absolute()))
        
        # 使用 macOS 的 open 命令打开浏览器
        # 如果有 PDF 文件，可以在网页中提示用户上传
        result = subprocess.run(
            ['open', PDF24_URL],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            if pdf_files:
                count = len(pdf_files)
                msg = f"已在浏览器打开 PDF24 工具（检测到 {count} 个 PDF 文件）"
            else:
                msg = "已在浏览器打开 PDF24 工具"
            print(f"[DEBUG] [PdfEditorPlugin] ✓ 浏览器已打开，URL: {PDF24_URL}")
            return True, msg, None
        else:
            error_msg = f"打开浏览器失败: {result.stderr}"
            print(f"[ERROR] [PdfEditorPlugin] {error_msg}")
            return False, error_msg, None
    
    except subprocess.TimeoutExpired:
        error_msg = "打开浏览器超时"
        print(f"[ERROR] [PdfEditorPlugin] {error_msg}")
        return False, error_msg, None
    except Exception as e:
        error_msg = f"打开浏览器失败：{str(e)}"
        print(f"[ERROR] [PdfEditorPlugin] {error_msg}")
        return False, error_msg, None
