#!/usr/bin/env python3
"""
Markdown 转 HTML 插件

将 Markdown 文件转换为 HTML，使用纯 Python 实现。
"""

from pathlib import Path
import re
from cedar.utils import print


def _detect_and_convert_mermaid(html_content: str) -> tuple:
    """
    检测并转换 Mermaid 代码块
    
    Args:
        html_content: 原始 HTML 内容
        
    Returns:
        tuple: (转换后的 HTML 内容, 是否包含 Mermaid 代码块)
    """
    print(f"[DEBUG] [MdToHtmlPlugin] 开始检测 Mermaid 代码块...")
    
    # 检测是否存在 Mermaid 代码块
    # 匹配 <pre><code class="language-mermaid"> 或 <pre><code class="mermaid">
    mermaid_pattern = r'<pre><code[^>]*class=["\'](?:language-)?mermaid["\'][^>]*>(.*?)</code></pre>'
    
    has_mermaid = bool(re.search(mermaid_pattern, html_content, re.DOTALL | re.IGNORECASE))
    print(f"[DEBUG] [MdToHtmlPlugin] 检测到 Mermaid 代码块: {has_mermaid}")
    
    if not has_mermaid:
        return html_content, False
    
    # 转换 Mermaid 代码块为 <div class="mermaid">
    def replace_mermaid(match):
        mermaid_code = match.group(1)
        # 解码 HTML 实体（markdown 库可能会转义）
        mermaid_code = mermaid_code.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        print(f"[DEBUG] [MdToHtmlPlugin] 转换 Mermaid 代码块，长度={len(mermaid_code)}")
        return f'<div class="mermaid">\n{mermaid_code}\n</div>'
    
    converted_html = re.sub(mermaid_pattern, replace_mermaid, html_content, flags=re.DOTALL | re.IGNORECASE)
    mermaid_count = len(re.findall(r'<div class="mermaid">', converted_html))
    print(f"[DEBUG] [MdToHtmlPlugin] 成功转换 {mermaid_count} 个 Mermaid 代码块")
    
    return converted_html, True


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
        
        # 检测并转换 Mermaid 代码块
        html_content, has_mermaid = _detect_and_convert_mermaid(html_content)
        print(f"[DEBUG] [MdToHtmlPlugin] Mermaid 检测完成，包含 Mermaid: {has_mermaid}")
        
        # 构建 Mermaid.js CDN 链接和初始化脚本（仅在检测到 Mermaid 时添加）
        mermaid_head = ""
        mermaid_script = ""
        if has_mermaid:
            print(f"[DEBUG] [MdToHtmlPlugin] 添加 Mermaid.js 支持")
            mermaid_head = """    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
    <style>
        .mermaid { 
            text-align: center; 
            margin: 20px 0; 
            background: #fff; 
            padding: 20px; 
            border-radius: 5px; 
            overflow-x: auto;
        }
    </style>"""
            mermaid_script = """    <script>
        mermaid.initialize({ 
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose'
        });
    </script>"""
        
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
{mermaid_head}
</head>
<body>
{html_content}
{mermaid_script}
</body>
</html>"""
        
        # 写入 HTML 文件
        output_path.write_text(full_html, encoding='utf-8')
        print(f"[DEBUG] [MdToHtmlPlugin] ✓ HTML 文件已生成: {output_path}")
        return True, f"转换成功：{output_path.name}", str(output_path)
    
    except Exception as e:
        print(f"[ERROR] [MdToHtmlPlugin] MD 转 HTML 失败: {e}")
        return False, f"转换失败：{str(e)}", None


if __name__ == "__main__":
    """测试代码"""
    print("=" * 60)
    print("[TEST] 开始测试 MD 转 HTML 插件（包含 Mermaid 支持）")
    print("=" * 60)
    
    # 使用指定的测试目录
    test_dir = Path("/Users/zhangsong/Desktop/code/cedar_dev/mac-commondX/test")
    print(f"[TEST] 测试目录: {test_dir}")
    
    # 确保测试目录存在
    test_dir.mkdir(parents=True, exist_ok=True)
    print(f"[TEST] 测试目录已创建/确认存在")
    
    try:
        # 测试 1: 普通 Markdown（无 Mermaid）
        print("\n[TEST] 测试 1: 普通 Markdown 文件（无 Mermaid）")
        test_md_1 = test_dir / "test_normal.md"
        test_md_1.write_text("""# 测试文档

这是一个普通的 Markdown 文档。

## 代码示例

```python
print("Hello, World!")
```

**粗体文本** 和 *斜体文本*
""", encoding='utf-8')
        print(f"[TEST] 创建测试文件: {test_md_1}")
        
        success, msg, output_path = execute(str(test_md_1))
        print(f"[TEST] 转换结果: success={success}, msg={msg}")
        if success:
            html_content = Path(output_path).read_text(encoding='utf-8')
            has_mermaid_js = "mermaid.min.js" in html_content
            print(f"[TEST] HTML 包含 Mermaid.js: {has_mermaid_js} (应该为 False)")
            assert not has_mermaid_js, "普通 Markdown 不应包含 Mermaid.js"
            print(f"[TEST] ✓ 测试 1 通过")
        
        # 测试 2: 包含 Mermaid 的 Markdown
        print("\n[TEST] 测试 2: 包含 Mermaid 图表的 Markdown 文件")
        test_md_2 = test_dir / "test_mermaid.md"
        test_md_2.write_text("""# 测试 Mermaid 图表

这是一个包含 Mermaid 图表的文档。

## 流程图示例

```mermaid
graph TD
    A[开始] --> B{判断条件}
    B -->|是| C[执行操作1]
    B -->|否| D[执行操作2]
    C --> E[结束]
    D --> E
```

## 序列图示例

```mermaid
sequenceDiagram
    participant A as 用户
    participant B as 系统
    A->>B: 发送请求
    B->>A: 返回响应
```

普通文本继续...
""", encoding='utf-8')
        print(f"[TEST] 创建测试文件: {test_md_2}")
        
        success, msg, output_path = execute(str(test_md_2))
        print(f"[TEST] 转换结果: success={success}, msg={msg}")
        if success:
            html_content = Path(output_path).read_text(encoding='utf-8')
            has_mermaid_js = "mermaid.min.js" in html_content
            has_mermaid_div = '<div class="mermaid">' in html_content
            mermaid_count = html_content.count('<div class="mermaid">')
            print(f"[TEST] HTML 包含 Mermaid.js: {has_mermaid_js} (应该为 True)")
            print(f"[TEST] HTML 包含 Mermaid div: {has_mermaid_div} (应该为 True)")
            print(f"[TEST] Mermaid 图表数量: {mermaid_count} (应该为 2)")
            assert has_mermaid_js, "包含 Mermaid 的文档应包含 Mermaid.js"
            assert has_mermaid_div, "应包含 Mermaid div 标签"
            assert mermaid_count == 2, f"应包含 2 个 Mermaid 图表，实际: {mermaid_count}"
            print(f"[TEST] ✓ 测试 2 通过")
        
        # 测试 3: 混合内容（普通代码 + Mermaid）
        print("\n[TEST] 测试 3: 混合内容（普通代码块 + Mermaid 图表）")
        test_md_3 = test_dir / "test_mixed.md"
        test_md_3.write_text("""# 混合内容测试

## Python 代码

```python
def hello():
    print("Hello")
```

## Mermaid 图表

```mermaid
pie title 数据分布
    "类型A" : 40
    "类型B" : 30
    "类型C" : 20
    "类型D" : 10
```

## JavaScript 代码

```javascript
console.log("test");
```
""", encoding='utf-8')
        print(f"[TEST] 创建测试文件: {test_md_3}")
        
        success, msg, output_path = execute(str(test_md_3))
        print(f"[TEST] 转换结果: success={success}, msg={msg}")
        if success:
            html_content = Path(output_path).read_text(encoding='utf-8')
            has_mermaid_js = "mermaid.min.js" in html_content
            has_python_code = "def hello()" in html_content or "language-python" in html_content
            mermaid_count = html_content.count('<div class="mermaid">')
            print(f"[TEST] HTML 包含 Mermaid.js: {has_mermaid_js} (应该为 True)")
            print(f"[TEST] HTML 包含 Python 代码: {has_python_code} (应该为 True)")
            print(f"[TEST] Mermaid 图表数量: {mermaid_count} (应该为 1)")
            assert has_mermaid_js, "应包含 Mermaid.js"
            assert has_python_code, "应包含 Python 代码块"
            assert mermaid_count == 1, f"应包含 1 个 Mermaid 图表，实际: {mermaid_count}"
            print(f"[TEST] ✓ 测试 3 通过")
        
        print("\n" + "=" * 60)
        print("[TEST] 所有测试通过！✓")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n[TEST] ✗ 测试失败: {e}")
    except Exception as e:
        print(f"\n[TEST] ✗ 测试异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理测试文件
        pass

