#!/usr/bin/env python3
"""
Markdown 转 PDF 插件

将 Markdown 文件转换为 PDF，使用纯 Python 实现。
"""

from pathlib import Path
from cedar.utils import print


def execute(md_path: str, output_path: str = None) -> tuple:
    """
    将 Markdown 文件转换为 PDF
    
    Args:
        md_path: Markdown 文件路径
        output_path: 输出 PDF 文件路径，如果为 None 则自动生成
        
    Returns:
        tuple: (success: bool, message: str, output_path: str)
    """
    print(f"[DEBUG] [MdToPdfPlugin] 开始转换 MD 到 PDF: {md_path}")
    try:
        md_path = Path(md_path)
        if not md_path.exists():
            print(f"[ERROR] [MdToPdfPlugin] Markdown 文件不存在: {md_path}")
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
            print(f"[DEBUG] [MdToPdfPlugin] 文件已存在，尝试新名称: {output_path}")
        
        # 先转换为 HTML，再转换为 PDF
        from .md_to_html_plugin import execute as md_to_html
        html_path = md_path.parent / f"{md_path.stem}_temp.html"
        success, msg, html_path_str = md_to_html(str(md_path), str(html_path))
        
        if not success:
            print(f"[ERROR] [MdToPdfPlugin] HTML 转换失败: {msg}")
            return False, f"HTML 转换失败：{msg}", None
        
        print(f"[DEBUG] [MdToPdfPlugin] HTML 转换成功，开始转换为 PDF...")
        
        # 尝试使用 weasyprint（纯 Python）
        try:
            import weasyprint
            print(f"[DEBUG] [MdToPdfPlugin] 使用 weasyprint 转换 PDF")
            weasyprint.HTML(filename=str(html_path)).write_pdf(str(output_path))
            html_path.unlink()  # 删除临时 HTML 文件
            print(f"[DEBUG] [MdToPdfPlugin] ✓ 使用 weasyprint 转换 PDF 成功: {output_path}")
            return True, f"转换成功：{output_path.name}", str(output_path)
        except ImportError:
            print(f"[DEBUG] [MdToPdfPlugin] weasyprint 库未安装，尝试下一个方案")
        except Exception as e:
            print(f"[DEBUG] [MdToPdfPlugin] weasyprint 转换失败: {e}")
        
        # 尝试使用 reportlab（纯 Python）
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            import re
            
            print(f"[DEBUG] [MdToPdfPlugin] 使用 reportlab 转换 PDF")
            
            # 读取 HTML 内容
            html_content = Path(html_path).read_text(encoding='utf-8')
            
            # 简单的 HTML 到文本转换（提取文本内容）
            # 移除 HTML 标签
            text_content = re.sub(r'<[^>]+>', '', html_content)
            # 清理多余空白
            text_content = re.sub(r'\n\s*\n', '\n\n', text_content)
            
            # 创建 PDF
            doc = SimpleDocTemplate(str(output_path), pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # 添加内容
            for line in text_content.split('\n'):
                if line.strip():
                    story.append(Paragraph(line.strip(), styles['Normal']))
                    story.append(Spacer(1, 0.1 * inch))
            
            doc.build(story)
            html_path.unlink()  # 删除临时 HTML 文件
            print(f"[DEBUG] [MdToPdfPlugin] ✓ 使用 reportlab 转换 PDF 成功: {output_path}")
            return True, f"转换成功：{output_path.name}", str(output_path)
        except ImportError:
            print(f"[DEBUG] [MdToPdfPlugin] reportlab 库未安装")
        except Exception as e:
            print(f"[DEBUG] [MdToPdfPlugin] reportlab 转换失败: {e}")
        
        # 如果都失败了
        html_path.unlink()  # 删除临时 HTML 文件
        print(f"[ERROR] [MdToPdfPlugin] 所有 PDF 转换方案都失败")
        return False, "PDF 转换失败，请安装 weasyprint 或 reportlab 库", None
    
    except Exception as e:
        print(f"[ERROR] [MdToPdfPlugin] MD 转 PDF 失败: {e}")
        return False, f"转换失败：{str(e)}", None
