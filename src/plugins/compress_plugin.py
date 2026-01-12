#!/usr/bin/env python3
"""
压缩插件

将文件/文件夹压缩为 ZIP 格式，使用纯 Python 实现。
"""

import os
import zipfile
from pathlib import Path
from cedar.utils import print


def execute(files: list, output_path: str = None) -> tuple:
    """
    压缩文件/文件夹为 ZIP
    
    Args:
        files: 文件/文件夹路径列表
        output_path: 输出 ZIP 文件路径，如果为 None 则自动生成
        
    Returns:
        tuple: (success: bool, message: str, output_path: str)
    """
    print(f"[DEBUG] [CompressPlugin] 开始压缩文件为 ZIP，文件数量={len(files) if files else 0}")
    try:
        if not files:
            print("[ERROR] [CompressPlugin] 没有要压缩的文件")
            return False, "没有要压缩的文件", None
        
        # 如果没有指定输出路径，自动生成
        if output_path is None:
            if len(files) == 1:
                # 单个文件/文件夹，使用其名称
                base_path = Path(files[0])
                output_path = base_path.parent / f"{base_path.name}.zip"
            else:
                # 多个文件，使用第一个文件所在目录
                base_dir = Path(files[0]).parent
                output_path = base_dir / "压缩包.zip"
            
            # 如果文件已存在，添加序号
            counter = 1
            original_path = output_path
            while output_path.exists():
                output_path = original_path.parent / f"{original_path.stem}_{counter}{original_path.suffix}"
                counter += 1
                print(f"[DEBUG] [CompressPlugin] 文件已存在，尝试新名称: {output_path}")
        
        output_path = Path(output_path)
        print(f"[DEBUG] [CompressPlugin] 输出路径: {output_path}")
        
        # 创建 ZIP 文件
        print(f"[DEBUG] [CompressPlugin] 开始创建 ZIP 文件...")
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                file_path = Path(file_path)
                if not file_path.exists():
                    print(f"[DEBUG] [CompressPlugin] 跳过不存在的文件: {file_path}")
                    continue
                
                if file_path.is_file():
                    # 添加文件，使用文件名作为 ZIP 内的路径
                    zipf.write(file_path, file_path.name)
                    print(f"[DEBUG] [CompressPlugin] 已添加文件到 ZIP: {file_path.name}")
                elif file_path.is_dir():
                    # 递归添加文件夹，保持文件夹结构
                    # 使用文件夹名作为 ZIP 内的根目录
                    print(f"[DEBUG] [CompressPlugin] 开始添加文件夹: {file_path.name}")
                    for root, dirs, files_in_dir in os.walk(file_path):
                        for file_name in files_in_dir:
                            file_full_path = Path(root) / file_name
                            # 计算相对于文件夹本身的路径，保持文件夹名
                            arcname = file_full_path.relative_to(file_path.parent)
                            zipf.write(file_full_path, arcname)
                            print(f"[DEBUG] [CompressPlugin] 已添加文件: {arcname}")
                    print(f"[DEBUG] [CompressPlugin] 已添加文件夹到 ZIP: {file_path.name}")
        
        print(f"[DEBUG] [CompressPlugin] ✓ 压缩成功: {output_path.name}")
        return True, f"压缩成功：{output_path.name}", str(output_path)
    
    except Exception as e:
        print(f"[ERROR] [CompressPlugin] 压缩失败: {e}")
        return False, f"压缩失败：{str(e)}", None
