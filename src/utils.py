#!/usr/bin/env python3
"""
工具函数模块

提供各模块共用的工具函数，遵循 DRY 原则，提高代码复用性。
"""

import os
import subprocess
import zipfile
import tarfile
from pathlib import Path
from cedar.utils import print


def run_script(script: str, timeout: int = 5) -> str:
    """
    执行 AppleScript，返回输出
    
    Args:
        script: AppleScript 脚本内容
        timeout: 超时时间（秒），默认 5 秒
        
    Returns:
        str: 脚本输出，如果执行失败返回空字符串
    """
    print(f"[DEBUG] [Utils] 执行 AppleScript，timeout={timeout}")
    try:
        r = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=timeout)
        print(f"[DEBUG] [Utils] AppleScript returncode={r.returncode}")
        print(f"[DEBUG] [Utils] stdout: {r.stdout[:200] if r.stdout else '(empty)'}")
        if r.stderr:
            print(f"[DEBUG] [Utils] stderr: {r.stderr[:200]}")
        result = r.stdout.strip() if r.returncode == 0 else ""
        print(f"[DEBUG] [Utils] AppleScript 执行完成，返回结果长度={len(result)}")
        return result
    except Exception as e:
        print(f"[ERROR] [Utils] AppleScript 执行失败: {e}")
        return ""


def escape_path(path: str) -> str:
    """
    转义路径中的特殊字符
    
    用于 AppleScript 中处理包含特殊字符的路径。
    
    Args:
        path: 需要转义的路径字符串
        
    Returns:
        str: 转义后的路径字符串
    """
    print(f"[DEBUG] [Utils] 转义路径: {path}")
    escaped = path.replace('\\', '\\\\').replace('"', '\\"')
    print(f"[DEBUG] [Utils] 转义后: {escaped}")
    return escaped


def copy_to_clipboard(text: str):
    """
    复制文本到剪贴板
    
    Args:
        text: 要复制的文本内容
    """
    print(f"[DEBUG] [Utils] 复制到剪贴板，文本长度={len(text)}")
    from AppKit import NSPasteboard, NSStringPboardType
    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    pb.setString_forType_(text, NSStringPboardType)
    print(f"[DEBUG] [Utils] ✓ 已复制到剪贴板")


def is_directory(path: str) -> bool:
    """
    判断路径是否为文件夹
    
    Args:
        path: 文件路径
        
    Returns:
        bool: 如果是文件夹返回 True，否则返回 False
    """
    try:
        result = os.path.isdir(path)
        print(f"[DEBUG] [Utils] 判断路径类型: {path} -> {'文件夹' if result else '文件'}")
        return result
    except Exception as e:
        print(f"[ERROR] [Utils] 判断路径类型失败: {e}")
        return False


def is_archive_file(path: str) -> bool:
    """
    判断路径是否为压缩文件
    
    通过检查文件扩展名判断是否为压缩文件。
    
    Args:
        path: 文件路径
        
    Returns:
        bool: 如果是压缩文件返回 True，否则返回 False
    """
    if is_directory(path):
        print(f"[DEBUG] [Utils] 路径是文件夹，不是压缩文件: {path}")
        return False
    
    ext = Path(path).suffix.lower()
    archive_extensions = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.tgz', '.tar.gz', '.tar.bz2'}
    result = ext in archive_extensions or any(path.lower().endswith(ext) for ext in archive_extensions)
    print(f"[DEBUG] [Utils] 判断压缩文件: {path} (扩展名={ext}) -> {result}")
    return result


def format_paths_list(files: list) -> str:
    """
    格式化路径列表，每行一个路径，添加图标前缀
    
    文件夹添加 📁 图标，文件添加 📄 图标。
    
    Args:
        files: 文件路径列表
        
    Returns:
        str: 格式化后的路径列表字符串
    """
    print(f"[DEBUG] [Utils] 格式化路径列表，文件数量={len(files)}")
    lines = []
    for path in files:
        if is_directory(path):
            lines.append(f"📁 {path}")
        else:
            lines.append(f"📄 {path}")
    result = "\n".join(lines)
    print(f"[DEBUG] [Utils] 格式化完成，结果长度={len(result)}")
    return result


def detect_archive_type(archive_path: str) -> str:
    """
    检测压缩文件类型
    
    通过检查文件头和扩展名来判断压缩文件类型。
    支持 ZIP、TAR、GZ、BZ2、RAR、7Z 等格式。
    
    Args:
        archive_path: 压缩文件路径
        
    Returns:
        str: 压缩文件类型（'zip'、'tar'、'gz'、'bz2'、'rar'、'7z' 等），如果无法识别返回 None
    """
    print(f"[DEBUG] [Utils] 检测压缩文件类型: {archive_path}")
    path = Path(archive_path)
    ext = path.suffix.lower()
    
    # 检查文件头
    try:
        with open(archive_path, 'rb') as f:
            header = f.read(4)
        
        print(f"[DEBUG] [Utils] 文件头: {header[:4]}")
        
        # ZIP 文件头：PK\x03\x04
        if header[:2] == b'PK':
            print(f"[DEBUG] [Utils] 检测到 ZIP 文件")
            return 'zip'
        
        # TAR 文件头
        if header == b'ustar' or b'ustar' in header:
            print(f"[DEBUG] [Utils] 检测到 TAR 文件")
            return 'tar'
        
        # GZ 文件头：\x1f\x8b
        if header[:2] == b'\x1f\x8b':
            print(f"[DEBUG] [Utils] 检测到 GZ 文件")
            return 'gz'
        
        # RAR 文件头：Rar!
        if header == b'Rar!':
            print(f"[DEBUG] [Utils] 检测到 RAR 文件")
            return 'rar'
        
        # 7Z 文件头：7z\xbc\xaf
        if header[:4] == b'7z\xbc\xaf':
            print(f"[DEBUG] [Utils] 检测到 7Z 文件")
            return '7z'
    except Exception as e:
        print(f"[ERROR] [Utils] 读取文件头失败: {e}")
    
    # 根据扩展名判断
    print(f"[DEBUG] [Utils] 根据扩展名判断: {ext}")
    if ext == '.zip':
        return 'zip'
    elif ext in ['.tar', '.tgz']:
        return 'tar'
    elif ext in ['.gz', '.tar.gz']:
        return 'gz'
    elif ext == '.rar':
        return 'rar'
    elif ext == '.7z':
        return '7z'
    elif ext in ['.bz2', '.tar.bz2']:
        return 'bz2'
    
    print(f"[DEBUG] [Utils] 无法识别压缩文件类型")
    return None


def convert_md_to_html(md_path: str, output_path: str = None) -> tuple:
    """
    将 Markdown 文件转换为 HTML
    
    Args:
        md_path: Markdown 文件路径
        output_path: 输出 HTML 文件路径，如果为 None 则自动生成
        
    Returns:
        tuple: (success: bool, message: str, output_path: str)
    """
    print(f"[DEBUG] [Utils] 开始转换 MD 到 HTML: {md_path}")
    try:
        md_path = Path(md_path)
        if not md_path.exists():
            return False, "Markdown 文件不存在", None
        
        # 如果没有指定输出路径，自动生成
        if output_path is None:
            output_path = md_path.parent / f"{md_path.stem}.html"
        else:
            output_path = Path(output_path)
        
        # 如果文件已存在，添加序号
        counter = 1
        original_path = output_path
        while output_path.exists():
            output_path = original_path.parent / f"{original_path.stem}_{counter}{original_path.suffix}"
            counter += 1
        
        # 读取 Markdown 内容
        md_content = md_path.read_text(encoding='utf-8')
        print(f"[DEBUG] [Utils] 读取 Markdown 内容，长度={len(md_content)}")
        
        # 尝试使用 markdown 库
        try:
            import markdown
            html_content = markdown.markdown(md_content, extensions=['extra', 'codehilite'])
            print(f"[DEBUG] [Utils] 使用 markdown 库转换成功")
        except ImportError:
            # 如果没有 markdown 库，使用简单的转换
            print(f"[DEBUG] [Utils] markdown 库未安装，使用简单转换")
            html_content = f"<pre>{md_content}</pre>"
        
        # 添加 HTML 模板
        full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{md_path.stem}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; }}
        pre {{ background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        code {{ background: #f5f5f5; padding: 2px 5px; border-radius: 3px; }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""
        
        # 写入 HTML 文件
        output_path.write_text(full_html, encoding='utf-8')
        print(f"[DEBUG] [Utils] ✓ HTML 文件已生成: {output_path}")
        return True, f"转换成功：{output_path.name}", str(output_path)
    
    except Exception as e:
        print(f"[ERROR] [Utils] MD 转 HTML 失败: {e}")
        return False, f"转换失败：{str(e)}", None


def convert_md_to_pdf(md_path: str, output_path: str = None) -> tuple:
    """
    将 Markdown 文件转换为 PDF
    
    Args:
        md_path: Markdown 文件路径
        output_path: 输出 PDF 文件路径，如果为 None 则自动生成
        
    Returns:
        tuple: (success: bool, message: str, output_path: str)
    """
    print(f"[DEBUG] [Utils] 开始转换 MD 到 PDF: {md_path}")
    try:
        md_path = Path(md_path)
        if not md_path.exists():
            return False, "Markdown 文件不存在", None
        
        # 如果没有指定输出路径，自动生成
        if output_path is None:
            output_path = md_path.parent / f"{md_path.stem}.pdf"
        else:
            output_path = Path(output_path)
        
        # 如果文件已存在，添加序号
        counter = 1
        original_path = output_path
        while output_path.exists():
            output_path = original_path.parent / f"{original_path.stem}_{counter}{original_path.suffix}"
            counter += 1
        
        # 先转换为 HTML，再转换为 PDF
        html_path = md_path.parent / f"{md_path.stem}_temp.html"
        success, msg, html_path_str = convert_md_to_html(md_path, str(html_path))
        
        if not success:
            return False, f"HTML 转换失败：{msg}", None
        
        print(f"[DEBUG] [Utils] HTML 转换成功，开始转换为 PDF...")
        
        # 尝试使用 weasyprint 或 pdfkit
        try:
            import weasyprint
            weasyprint.HTML(filename=str(html_path)).write_pdf(str(output_path))
            html_path.unlink()  # 删除临时 HTML 文件
            print(f"[DEBUG] [Utils] ✓ 使用 weasyprint 转换 PDF 成功: {output_path}")
            return True, f"转换成功：{output_path.name}", str(output_path)
        except ImportError:
            pass
        
        try:
            import pdfkit
            pdfkit.from_file(str(html_path), str(output_path))
            html_path.unlink()  # 删除临时 HTML 文件
            print(f"[DEBUG] [Utils] ✓ 使用 pdfkit 转换 PDF 成功: {output_path}")
            return True, f"转换成功：{output_path.name}", str(output_path)
        except ImportError:
            pass
        
        # 如果都没有安装，尝试使用系统工具
        try:
            # macOS 可以使用 textutil 或 cupsfilter
            result = subprocess.run(
                ['cupsfilter', str(html_path), str(output_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            html_path.unlink()  # 删除临时 HTML 文件
            if result.returncode == 0:
                print(f"[DEBUG] [Utils] ✓ 使用系统工具转换 PDF 成功: {output_path}")
                return True, f"转换成功：{output_path.name}", str(output_path)
        except Exception as e:
            print(f"[DEBUG] [Utils] 系统工具转换失败: {e}")
        
        # 如果都失败了
        html_path.unlink()  # 删除临时 HTML 文件
        return False, "PDF 转换失败，请安装 weasyprint 或 pdfkit 库", None
    
    except Exception as e:
        print(f"[ERROR] [Utils] MD 转 PDF 失败: {e}")
        return False, f"转换失败：{str(e)}", None


def compress_to_zip(files, output_path=None):
    """
    压缩文件/文件夹为 ZIP
    
    Args:
        files: 文件/文件夹路径列表
        output_path: 输出 ZIP 文件路径，如果为 None 则自动生成
        
    Returns:
        tuple: (success: bool, message: str, output_path: str)
    """
    print(f"[DEBUG] [Utils] 开始压缩文件为 ZIP，文件数量={len(files) if files else 0}")
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
        print(f"[DEBUG] [Utils] 输出路径: {output_path}")
        
        # 创建 ZIP 文件
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                file_path = Path(file_path)
                if not file_path.exists():
                    print(f"[DEBUG] [Utils] 跳过不存在的文件: {file_path}")
                    continue
                
                if file_path.is_file():
                    # 添加文件，使用文件名作为 ZIP 内的路径
                    zipf.write(file_path, file_path.name)
                    print(f"[DEBUG] [Utils] 已添加文件到 ZIP: {file_path.name}")
                elif file_path.is_dir():
                    # 递归添加文件夹，保持文件夹结构
                    # 使用文件夹名作为 ZIP 内的根目录
                    for root, dirs, files_in_dir in os.walk(file_path):
                        for file_name in files_in_dir:
                            file_full_path = Path(root) / file_name
                            # 计算相对于文件夹本身的路径，保持文件夹名
                            arcname = file_full_path.relative_to(file_path.parent)
                            zipf.write(file_full_path, arcname)
                    print(f"[DEBUG] [Utils] 已添加文件夹到 ZIP: {file_path.name}")
        
        print(f"[DEBUG] [Utils] ✓ 压缩成功: {output_path.name}")
        return True, f"压缩成功：{output_path.name}", str(output_path)
    
    except Exception as e:
        print(f"[ERROR] [Utils] 压缩失败: {e}")
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
    print(f"[DEBUG] [Utils] 开始解压文件: {archive_path}")
    try:
        archive_path = Path(archive_path)
        if not archive_path.exists():
            print(f"[ERROR] [Utils] 压缩文件不存在: {archive_path}")
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
        print(f"[DEBUG] [Utils] 输出目录: {output_dir}")
        
        # 检测压缩文件类型
        archive_type = detect_archive_type(archive_path)
        print(f"[DEBUG] [Utils] 检测到压缩文件类型: {archive_type}")
        
        if archive_type == 'zip':
            # 解压 ZIP
            print(f"[DEBUG] [Utils] 使用 zipfile 解压 ZIP 文件")
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                zipf.extractall(output_dir)
        
        elif archive_type in ['tar', 'gz', 'bz2']:
            # 解压 TAR/GZ/BZ2
            mode = 'r'
            if archive_type == 'gz' or archive_path.suffix.lower() in ['.gz', '.tgz', '.tar.gz']:
                mode = 'r:gz'
            elif archive_type == 'bz2' or archive_path.suffix.lower() in ['.bz2', '.tar.bz2']:
                mode = 'r:bz2'
            
            print(f"[DEBUG] [Utils] 使用 tarfile 解压 TAR 文件，模式={mode}")
            with tarfile.open(archive_path, mode) as tar:
                tar.extractall(output_dir)
        
        elif archive_type == 'rar':
            # 解压 RAR（需要系统工具）
            print(f"[DEBUG] [Utils] 使用系统工具解压 RAR 文件")
            return _decompress_rar(archive_path, output_dir)
        
        elif archive_type == '7z':
            # 解压 7Z（需要系统工具）
            print(f"[DEBUG] [Utils] 使用系统工具解压 7Z 文件")
            return _decompress_7z(archive_path, output_dir)
        
        else:
            print(f"[ERROR] [Utils] 不支持的压缩格式: {archive_path.suffix}")
            return False, f"不支持的压缩格式：{archive_path.suffix}", None
        
        print(f"[DEBUG] [Utils] ✓ 解压成功: {output_dir.name}")
        return True, f"解压成功：{output_dir.name}", str(output_dir)
    
    except Exception as e:
        print(f"[ERROR] [Utils] 解压失败: {e}")
        return False, f"解压失败：{str(e)}", None


def _decompress_rar(archive_path, output_dir):
    """使用系统工具解压 RAR"""
    print(f"[DEBUG] [Utils] 尝试使用 unrar 解压 RAR 文件")
    try:
        # 尝试使用 unrar 命令
        result = subprocess.run(
            ['unrar', 'x', str(archive_path), str(output_dir)],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            print(f"[DEBUG] [Utils] ✓ RAR 解压成功")
            return True, f"解压成功：{output_dir.name}", str(output_dir)
        else:
            print(f"[ERROR] [Utils] RAR 解压失败，returncode={result.returncode}")
            return False, "RAR 解压失败，请安装 unrar 工具", None
    except FileNotFoundError:
        print(f"[ERROR] [Utils] unrar 工具未找到")
        return False, "RAR 解压需要安装 unrar 工具", None
    except Exception as e:
        print(f"[ERROR] [Utils] RAR 解压异常: {e}")
        return False, f"RAR 解压失败：{str(e)}", None


def _decompress_7z(archive_path, output_dir):
    """使用系统工具解压 7Z"""
    print(f"[DEBUG] [Utils] 尝试使用 7z 或 p7zip 解压 7Z 文件")
    try:
        # 尝试使用 7z 或 p7zip 命令
        for cmd in ['7z', 'p7zip']:
            try:
                print(f"[DEBUG] [Utils] 尝试使用命令: {cmd}")
                result = subprocess.run(
                    [cmd, 'x', str(archive_path), f'-o{output_dir}'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode == 0:
                    print(f"[DEBUG] [Utils] ✓ 使用 {cmd} 解压 7Z 成功")
                    return True, f"解压成功：{output_dir.name}", str(output_dir)
            except FileNotFoundError:
                print(f"[DEBUG] [Utils] {cmd} 命令未找到，尝试下一个")
                continue
        
        print(f"[ERROR] [Utils] 7Z 解压工具未找到")
        return False, "7Z 解压需要安装 7z 或 p7zip 工具", None
    except Exception as e:
        print(f"[ERROR] [Utils] 7Z 解压异常: {e}")
        return False, f"7Z 解压失败：{str(e)}", None
