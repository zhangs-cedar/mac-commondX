#!/usr/bin/env python3
"""压缩解压管理器"""

import os
import zipfile
import tarfile
import subprocess
from pathlib import Path
from cedar.utils import print
from .utils import detect_archive_type


def compress_to_zip(files, output_path=None):
    """
    压缩文件/文件夹为 ZIP
    
    Args:
        files: 文件/文件夹路径列表
        output_path: 输出 ZIP 文件路径，如果为 None 则自动生成
        
    Returns:
        tuple: (success: bool, message: str, output_path: str)
    """
    try:
        if not files:
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
        
        output_path = Path(output_path)
        
        # 创建 ZIP 文件
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                file_path = Path(file_path)
                if not file_path.exists():
                    continue
                
                if file_path.is_file():
                    # 添加文件，使用文件名作为 ZIP 内的路径
                    zipf.write(file_path, file_path.name)
                elif file_path.is_dir():
                    # 递归添加文件夹，保持文件夹结构
                    # 使用文件夹名作为 ZIP 内的根目录
                    for root, dirs, files_in_dir in os.walk(file_path):
                        for file_name in files_in_dir:
                            file_full_path = Path(root) / file_name
                            # 计算相对于文件夹本身的路径，保持文件夹名
                            arcname = file_full_path.relative_to(file_path.parent)
                            zipf.write(file_full_path, arcname)
        
        return True, f"压缩成功：{output_path.name}", str(output_path)
    
    except Exception as e:
        print(f"压缩失败: {e}")
        return False, f"压缩失败：{str(e)}", None


def decompress_archive(archive_path, output_dir=None):
    """
    解压压缩文件
    
    Args:
        archive_path: 压缩文件路径
        output_dir: 输出目录，如果为 None 则解压到压缩文件所在目录
        
    Returns:
        tuple: (success: bool, message: str, output_dir: str)
    """
    try:
        archive_path = Path(archive_path)
        if not archive_path.exists():
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
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 检测压缩文件类型
        archive_type = detect_archive_type(archive_path)
        
        if archive_type == 'zip':
            # 解压 ZIP
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                zipf.extractall(output_dir)
        
        elif archive_type in ['tar', 'gz', 'bz2']:
            # 解压 TAR/GZ/BZ2
            mode = 'r'
            if archive_type == 'gz' or archive_path.suffix.lower() in ['.gz', '.tgz', '.tar.gz']:
                mode = 'r:gz'
            elif archive_type == 'bz2' or archive_path.suffix.lower() in ['.bz2', '.tar.bz2']:
                mode = 'r:bz2'
            
            with tarfile.open(archive_path, mode) as tar:
                tar.extractall(output_dir)
        
        elif archive_type == 'rar':
            # 解压 RAR（需要系统工具）
            return _decompress_rar(archive_path, output_dir)
        
        elif archive_type == '7z':
            # 解压 7Z（需要系统工具）
            return _decompress_7z(archive_path, output_dir)
        
        else:
            return False, f"不支持的压缩格式：{archive_path.suffix}", None
        
        return True, f"解压成功：{output_dir.name}", str(output_dir)
    
    except Exception as e:
        print(f"解压失败: {e}")
        return False, f"解压失败：{str(e)}", None


def _decompress_rar(archive_path, output_dir):
    """使用系统工具解压 RAR"""
    try:
        # 尝试使用 unrar 命令
        result = subprocess.run(
            ['unrar', 'x', str(archive_path), str(output_dir)],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            return True, f"解压成功：{output_dir.name}", str(output_dir)
        else:
            return False, "RAR 解压失败，请安装 unrar 工具", None
    except FileNotFoundError:
        return False, "RAR 解压需要安装 unrar 工具", None
    except Exception as e:
        return False, f"RAR 解压失败：{str(e)}", None


def _decompress_7z(archive_path, output_dir):
    """使用系统工具解压 7Z"""
    try:
        # 尝试使用 7z 或 p7zip 命令
        for cmd in ['7z', 'p7zip']:
            try:
                result = subprocess.run(
                    [cmd, 'x', str(archive_path), f'-o{output_dir}'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode == 0:
                    return True, f"解压成功：{output_dir.name}", str(output_dir)
            except FileNotFoundError:
                continue
        
        return False, "7Z 解压需要安装 7z 或 p7zip 工具", None
    except Exception as e:
        return False, f"7Z 解压失败：{str(e)}", None
