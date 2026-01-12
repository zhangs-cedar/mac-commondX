#!/usr/bin/env python3
"""
PDF 转 Word 插件

将 PDF 文件转换为 Word 文档，使用 pdf2docx 库实现。
"""

from pathlib import Path
from cedar.utils import print


def execute(pdf_path: str, output_path: str = None, start_page: int = 0, end_page: int = None) -> tuple:
    """
    将 PDF 文件转换为 Word 文档，尽量保持原始布局
    
    Args:
        pdf_path: PDF 文件路径
        output_path: 输出 Word 文件路径，如果为 None 则自动生成
        start_page: 起始页面（从0开始），默认0表示从第一页开始
        end_page: 结束页面（None 表示转换到最后一页），默认None
        
    Returns:
        tuple: (success: bool, message: str, output_path: str)
    """
    print(f"[DEBUG] [PdfToWordPlugin] 开始转换 PDF 到 Word: {pdf_path}")
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"[ERROR] [PdfToWordPlugin] PDF 文件不存在: {pdf_path}")
        return False, "PDF 文件不存在", None
    
    # 如果没有指定输出路径，自动生成
    if output_path is None:
        output_path = pdf_path.parent / f"{pdf_path.stem}.docx"
    else:
        output_path = Path(output_path)
    
    print(f"[DEBUG] [PdfToWordPlugin] 输出路径: {output_path}")
    
    # 如果文件已存在，添加序号
    counter = 1
    original_path = output_path
    while output_path.exists():
        output_path = original_path.parent / f"{original_path.stem}_{counter}{original_path.suffix}"
        counter += 1
        print(f"[DEBUG] [PdfToWordPlugin] 文件已存在，尝试新名称: {output_path}")
    
    # 尝试使用 pdf2docx 库进行转换
    try:
        from pdf2docx import Converter
        print(f"[DEBUG] [PdfToWordPlugin] pdf2docx 库已导入，开始转换...")
        print(f"[DEBUG] [PdfToWordPlugin] 转换配置: start_page={start_page}, end_page={end_page}")
        
        # 创建转换器（pdf2docx 会自动保持布局）
        cv = Converter(str(pdf_path))
        print(f"[DEBUG] [PdfToWordPlugin] 转换器已创建，开始转换 PDF 内容（保持布局）...")
        
        # 执行转换，pdf2docx 默认会尽量保持原始布局
        # start 和 end 参数用于指定页面范围
        cv.convert(str(output_path), start=start_page, end=end_page)
        print(f"[DEBUG] [PdfToWordPlugin] PDF 内容转换完成")
        
        # 关闭转换器
        cv.close()
        print(f"[DEBUG] [PdfToWordPlugin] 转换器已关闭")
        
        # 验证输出文件是否生成
        if not output_path.exists():
            print(f"[ERROR] [PdfToWordPlugin] Word 文件未生成: {output_path}")
            return False, "转换失败：输出文件未生成", None
        
        file_size = output_path.stat().st_size
        print(f"[DEBUG] [PdfToWordPlugin] ✓ Word 文件已生成: {output_path}, 大小={file_size} 字节")
        return True, f"转换成功：{output_path.name}", str(output_path)
            
    except ImportError:
        print(f"[ERROR] [PdfToWordPlugin] pdf2docx 库未安装")
        return False, "转换失败：请安装 pdf2docx 库（pip install pdf2docx）", None
    except Exception as e:
        print(f"[ERROR] [PdfToWordPlugin] PDF 转 Word 转换失败: {e}")
        return False, f"转换失败：{str(e)}", None


if __name__ == "__main__":
    """测试代码"""
    print("=" * 60)
    print("[TEST] 测试 PDF 转 Word 插件")
    print("=" * 60)
    
    # 注意：需要提供一个真实的 PDF 文件路径进行测试
    test_pdf = Path("/Users/zhangsong/Desktop/code/cedar_dev/mac-commondX/test/pdf/test_mermaid.pdf")
    
    if test_pdf.exists():
        success, msg, output_path = execute(str(test_pdf))
        print(f"[TEST] 转换结果: {msg}")
        
        if success:
            print(f"[TEST] ✓ 测试通过，输出文件: {output_path}")
        else:
            print(f"[TEST] ✗ 转换失败")
    else:
        print(f"[TEST] 测试文件不存在: {test_pdf}")
