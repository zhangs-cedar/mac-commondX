#!/usr/bin/env python3
"""
解压插件

解压 Python 标准库支持的压缩文件格式（ZIP、TAR、GZ、BZ2）。
"""

import zipfile
import tarfile
from pathlib import Path
from cedar.utils import print


def _detect_archive_type(archive_path: str) -> str:
    """
    检测压缩文件类型
    
    Args:
        archive_path: 压缩文件路径
        
    Returns:
        str: 压缩文件类型，如果无法识别返回 None
    """
    print(f"[DEBUG] [DecompressPlugin] 检测压缩文件类型: {archive_path}")
    path = Path(archive_path)
    ext = path.suffix.lower()
    
    # 检查文件头
    try:
        with open(archive_path, 'rb') as f:
            header = f.read(4)
        
        print(f"[DEBUG] [DecompressPlugin] 文件头: {header[:4]}")
        
        # ZIP 文件头：PK\x03\x04
        if header[:2] == b'PK':
            print(f"[DEBUG] [DecompressPlugin] 检测到 ZIP 文件")
            return 'zip'
        
        # TAR 文件头
        if header == b'ustar' or b'ustar' in header:
            print(f"[DEBUG] [DecompressPlugin] 检测到 TAR 文件")
            return 'tar'
        
        # GZ 文件头：\x1f\x8b
        if header[:2] == b'\x1f\x8b':
            print(f"[DEBUG] [DecompressPlugin] 检测到 GZ 文件")
            return 'gz'
    except Exception as e:
        print(f"[ERROR] [DecompressPlugin] 读取文件头失败: {e}")
    
    # 根据扩展名判断
    print(f"[DEBUG] [DecompressPlugin] 根据扩展名判断: {ext}")
    if ext == '.zip':
        return 'zip'
    elif ext in ['.tar', '.tgz']:
        return 'tar'
    elif ext in ['.gz', '.tar.gz']:
        return 'gz'
    elif ext in ['.bz2', '.tar.bz2']:
        return 'bz2'
    
    print(f"[DEBUG] [DecompressPlugin] 无法识别压缩文件类型")
    return None


def execute(archive_path: str, output_dir: str = None) -> tuple:
    """
    解压压缩文件
    
    Args:
        archive_path: 压缩文件路径
        output_dir: 输出目录，如果为 None 则解压到压缩文件所在目录
        
    Returns:
        tuple: (success: bool, message: str, output_dir: str)
    """
    print(f"[DEBUG] [DecompressPlugin] 开始解压文件: {archive_path}")
    try:
        archive_path = Path(archive_path)
        if not archive_path.exists():
            print(f"[ERROR] [DecompressPlugin] 压缩文件不存在: {archive_path}")
            return False, "压缩文件不存在", None
        
        # 如果没有指定输出目录，解压到压缩文件所在目录
        if output_dir is None:
            output_dir = archive_path.parent / archive_path.stem
        else:
            output_dir = Path(output_dir)
        
        # 如果输出目录已存在，添加序号
        counter = 1
        original_dir = output_dir
        while output_dir.exists():
            output_dir = original_dir.parent / f"{original_dir.name}_{counter}"
            counter += 1
            print(f"[DEBUG] [DecompressPlugin] 目录已存在，尝试新名称: {output_dir}")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"[DEBUG] [DecompressPlugin] 输出目录: {output_dir}")
        
        # 检测压缩文件类型
        archive_type = _detect_archive_type(archive_path)
        print(f"[DEBUG] [DecompressPlugin] 检测到压缩文件类型: {archive_type}")
        
        if archive_type == 'zip':
            # 解压 ZIP
            print(f"[DEBUG] [DecompressPlugin] 使用 zipfile 解压 ZIP 文件")
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                zipf.extractall(output_dir)
        
        elif archive_type in ['tar', 'gz', 'bz2']:
            # 解压 TAR/GZ/BZ2
            mode = 'r'
            if archive_type == 'gz' or archive_path.suffix.lower() in ['.gz', '.tgz', '.tar.gz']:
                mode = 'r:gz'
            elif archive_type == 'bz2' or archive_path.suffix.lower() in ['.bz2', '.tar.bz2']:
                mode = 'r:bz2'
            
            print(f"[DEBUG] [DecompressPlugin] 使用 tarfile 解压 TAR 文件，模式={mode}")
            with tarfile.open(archive_path, mode) as tar:
                tar.extractall(output_dir)
        
        elif archive_type in ['rar', '7z']:
            # 不支持的格式
            print(f"[ERROR] [DecompressPlugin] 不支持的压缩格式: {archive_type}")
            return False, f"不支持的压缩格式：{archive_type}（仅支持 ZIP、TAR、GZ、BZ2）", None
        
        else:
            print(f"[ERROR] [DecompressPlugin] 不支持的压缩格式: {archive_path.suffix}")
            return False, f"不支持的压缩格式：{archive_path.suffix}（仅支持 ZIP、TAR、GZ、BZ2）", None
        
        print(f"[DEBUG] [DecompressPlugin] ✓ 解压成功: {output_dir.name}")
        return True, f"解压成功：{output_dir.name}", str(output_dir)
    
    except Exception as e:
        print(f"[ERROR] [DecompressPlugin] 解压失败: {e}")
        return False, f"解压失败：{str(e)}", None
