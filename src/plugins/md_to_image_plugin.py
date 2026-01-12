#!/usr/bin/env python3
"""
Markdown 转图片插件

将 Markdown 文件转换为图片，使用 html2image 库实现高质量渲染。
"""

from pathlib import Path
from cedar.utils import print


def execute(md_path: str, output_path: str = None, format: str = "png", size: tuple = (1920, 1080)) -> tuple:
    """
    将 Markdown 文件转换为图片（html2image 方案）
    
    Args:
        md_path: Markdown 文件路径
        output_path: 输出图片路径，如果为 None 则自动生成
        format: 图片格式（png、jpeg），默认 png
        size: 图片尺寸 (width, height)，默认 (1920, 1080)
        
    Returns:
        tuple: (success: bool, message: str, output_path: str)
    """
    print(f"[DEBUG] [MdToImagePlugin] 开始转换 MD 到图片: {md_path}")
    try:
        md_path = Path(md_path)
        if not md_path.exists():
            print(f"[ERROR] [MdToImagePlugin] Markdown 文件不存在: {md_path}")
            return False, "Markdown 文件不存在", None
        
        # 如果没有指定输出路径，自动生成
        if output_path is None:
            output_path = md_path.parent / f"{md_path.stem}.{format}"
        else:
            output_path = Path(output_path)
        
        # 如果文件已存在，添加序号
        counter = 1
        original_path = output_path
        while output_path.exists():
            output_path = original_path.parent / f"{original_path.stem}_{counter}{original_path.suffix}"
            counter += 1
            print(f"[DEBUG] [MdToImagePlugin] 文件已存在，尝试新名称: {output_path}")
        
        # 读取 Markdown 内容并转换为 HTML（直接在内存中处理，无需临时文件）
        print(f"[DEBUG] [MdToImagePlugin] 读取 Markdown 内容...")
        md_content = md_path.read_text(encoding='utf-8')
        print(f"[DEBUG] [MdToImagePlugin] Markdown 内容长度={len(md_content)}")
        
        # 转换为 HTML
        try:
            import markdown
            print(f"[DEBUG] [MdToImagePlugin] 使用 markdown 库转换")
            html_content = markdown.markdown(md_content, extensions=['extra', 'codehilite'])
            print(f"[DEBUG] [MdToImagePlugin] markdown 库转换成功")
        except ImportError:
            # 如果没有 markdown 库，使用简单的转换
            print(f"[DEBUG] [MdToImagePlugin] markdown 库未安装，使用简单转换")
            html_content = f"<pre>{md_content}</pre>"
        
        # 添加 HTML 模板（与 md_to_html_plugin 保持一致）
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
        
        print(f"[DEBUG] [MdToImagePlugin] HTML 转换完成，开始转换为图片...")
        print(f"[DEBUG] [MdToImagePlugin] 图片尺寸: {size}, 格式: {format}")
        
        # 使用 html2image 渲染并截图
        try:
            from html2image import Html2Image
            print(f"[DEBUG] [MdToImagePlugin] html2image 库已导入")
            print(f"[DEBUG] [MdToImagePlugin] HTML 内容长度={len(full_html)}")
            
            # 初始化 Html2Image 实例，设置高分辨率尺寸和输出目录
            output_dir = str(output_path.parent)
            hti = Html2Image(size=size, output_path=output_dir)
            print(f"[DEBUG] [MdToImagePlugin] Html2Image 实例已创建，尺寸={size}, 输出目录={output_dir}")
            
            # 渲染 HTML 并保存为图片
            save_as = output_path.name
            print(f"[DEBUG] [MdToImagePlugin] 开始截图，保存文件名: {save_as}")
            
            hti.screenshot(
                html_str=full_html,
                save_as=save_as,
                size=size
            )
            
            # 验证文件是否已创建
            if output_path.exists():
                print(f"[DEBUG] [MdToImagePlugin] ✓ 图片已保存: {output_path}")
            else:
                # 如果文件不在预期位置，尝试在当前目录查找
                temp_image = Path(save_as)
                if temp_image.exists():
                    temp_image.rename(output_path)
                    print(f"[DEBUG] [MdToImagePlugin] 图片已从当前目录移动到目标位置: {output_path}")
                else:
                    raise FileNotFoundError(f"图片文件未生成: {output_path}")
            
            print(f"[DEBUG] [MdToImagePlugin] ✓ 图片转换成功: {output_path}")
            return True, f"转换成功：{output_path.name}", str(output_path)
            
        except ImportError:
            print(f"[ERROR] [MdToImagePlugin] html2image 库未安装")
            return False, "图片转换需要安装 html2image 库（pip install html2image）", None
        except Exception as e:
            print(f"[ERROR] [MdToImagePlugin] html2image 转换失败: {e}")
            return False, f"图片转换失败：{str(e)}", None
    
    except Exception as e:
        print(f"[ERROR] [MdToImagePlugin] MD 转图片失败: {e}")
        return False, f"转换失败：{str(e)}", None
