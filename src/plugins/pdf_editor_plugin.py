#!/usr/bin/env python3
"""
PDF WORD 等在线免费转化工具插件

打开 PDF24 工具网页（https://tools.pdf24.org/zh/all-tools），提供免费的在线 PDF、Word、Excel 等文档转换和操作工具。
"""

import subprocess
from pathlib import Path
from cedar.utils import print

# PDF24 工具网页地址
PDF24_URL = "https://tools.pdf24.org/zh/all-tools"

# 支持的文档类型扩展名
DOCUMENT_EXTENSIONS = {
    '.pdf',  # PDF 文件
    '.doc', '.docx',  # Word 文档
    '.xls', '.xlsx',  # Excel 表格
    '.ppt', '.pptx',  # PowerPoint 演示文稿
    '.txt', '.rtf',  # 文本文件
}


def execute(files: list) -> tuple:
    """
    打开 PDF24 工具网页（支持 PDF、Word、Excel 等文档转换）
    
    Args:
        files: 文件路径列表（可选，如果提供支持的文档文件，可以在网页中直接使用）
        
    Returns:
        tuple: (success: bool, message: str, None)
    """
    print(f"[DEBUG] [PdfEditorPlugin] 开始打开 PDF24 工具网页，文件数量={len(files) if files else 0}")
    try:
        # 检查是否有支持的文档文件
        document_files = []
        if files:
            for file_path in files:
                path = Path(file_path)
                if path.exists() and path.suffix.lower() in DOCUMENT_EXTENSIONS:
                    document_files.append(str(path.absolute()))
        
        # 使用 macOS 的 open 命令打开浏览器
        # 如果有支持的文档文件，可以在网页中提示用户上传
        result = subprocess.run(
            ['open', PDF24_URL],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            if document_files:
                count = len(document_files)
                msg = f"已在浏览器打开 PDF24 工具（检测到 {count} 个文档文件）"
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
