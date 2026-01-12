#!/usr/bin/env python3
"""
Markdown 转 HTML 插件

将 Markdown 文件转换为 HTML，使用纯 Python 实现。
"""

from pathlib import Path
from cedar.utils import print


def execute(md_path: str, output_path: str = None) -> tuple:
    """
    将 Markdown 文件转换为 HTML
    
    Args:
        md_path: Markdown 文件路径
        output_path: 输出 HTML 文件路径，如果为 None 则自动生成
        
    Returns:
        tuple: (success: bool, message: str, output_path: str)
    """
    print(f"[DEBUG] [MdToHtmlPlugin] 开始转换 MD 到 HTML: {md_path}")
    try:
        md_path = Path(md_path)
        if not md_path.exists():
            print(f"[ERROR] [MdToHtmlPlugin] Markdown 文件不存在: {md_path}")
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
            print(f"[DEBUG] [MdToHtmlPlugin] 文件已存在，尝试新名称: {output_path}")
        
        # 读取 Markdown 内容
        md_content = md_path.read_text(encoding='utf-8')
        print(f"[DEBUG] [MdToHtmlPlugin] 读取 Markdown 内容，长度={len(md_content)}")
        
        # 尝试使用 markdown 库
        try:
            import markdown
            print(f"[DEBUG] [MdToHtmlPlugin] 使用 markdown 库转换")
            html_content = markdown.markdown(md_content, extensions=['extra', 'codehilite'])
            print(f"[DEBUG] [MdToHtmlPlugin] markdown 库转换成功")
        except ImportError:
            # 如果没有 markdown 库，使用简单的转换
            print(f"[DEBUG] [MdToHtmlPlugin] markdown 库未安装，使用简单转换")
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
        print(f"[DEBUG] [MdToHtmlPlugin] ✓ HTML 文件已生成: {output_path}")
        return True, f"转换成功：{output_path.name}", str(output_path)
    
    except Exception as e:
        print(f"[ERROR] [MdToHtmlPlugin] MD 转 HTML 失败: {e}")
        return False, f"转换失败：{str(e)}", None
