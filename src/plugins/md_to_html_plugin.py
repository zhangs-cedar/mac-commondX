#!/usr/bin/env python3
"""
Markdown 转 HTML 插件

将 Markdown 文件转换为 HTML，使用纯 Python 实现。
"""

from pathlib import Path
import re
from cedar.utils import print

# Mermaid.js 路径配置
# 使用项目目录中的文件（打包时会包含）
MERMAID_JS_PROJECT = Path(__file__).parent / "assets" / "mermaid.min.js"


def _get_mermaid_js() -> str:
    """
    获取 Mermaid.js 代码（完全离线支持）
    
    从项目目录读取：src/plugins/assets/mermaid.min.js
    
    Returns:
        str: Mermaid.js 代码，如果获取失败返回空字符串
    """
    print(f"[DEBUG] [MdToHtmlPlugin] 开始获取 Mermaid.js...")
    
    if MERMAID_JS_PROJECT.exists():
        try:
            mermaid_code = MERMAID_JS_PROJECT.read_text(encoding='utf-8')
            print(f"[DEBUG] [MdToHtmlPlugin] 从项目目录读取 Mermaid.js，长度={len(mermaid_code)}")
            return mermaid_code
        except Exception as e:
            print(f"[WARN] [MdToHtmlPlugin] 读取项目文件失败: {e}")
    
    print(f"[WARN] [MdToHtmlPlugin] 未找到 Mermaid.js 文件，Mermaid 图表将无法渲染")
    return ""


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
    # 支持多种格式：
    # 1. <pre><code class="language-mermaid"> 或 <pre><code class="mermaid">
    # 2. <div class="codehilite"><pre><code>（codehilite 扩展格式，需要从内容中提取）
    # 3. 直接匹配包含 mermaid 关键字的代码块
    
    # 先尝试标准格式
    mermaid_pattern1 = r'<pre><code[^>]*class=["\'](?:language-)?mermaid["\'][^>]*>(.*?)</code></pre>'
    has_mermaid1 = bool(re.search(mermaid_pattern1, html_content, re.DOTALL | re.IGNORECASE))
    
    # 检查是否包含 mermaid 图表语法关键词
    mermaid_keywords = ['graph', 'sequenceDiagram', 'classDiagram', 'stateDiagram', 'erDiagram', 
                       'gantt', 'pie', 'gitgraph', 'journey', 'flowchart']
    has_mermaid2 = any(keyword in html_content for keyword in mermaid_keywords)
    
    # 尝试匹配 codehilite 格式的代码块，并检查内容
    # codehilite 可能生成: <div class="codehilite"><pre><code>...</code></pre></div>
    # 或者: <div class="codehilite"><pre><span></span><code>...</code></pre></div>
    codehilite_pattern = r'<div class="codehilite"><pre>(?:<span[^>]*></span>)?<code>(.*?)</code></pre></div>'
    codehilite_blocks = re.findall(codehilite_pattern, html_content, re.DOTALL | re.IGNORECASE)
    
    has_mermaid3 = False
    for block in codehilite_blocks:
        # 解码 HTML 实体
        decoded = block.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        # 检查是否包含 mermaid 语法
        if any(keyword in decoded for keyword in mermaid_keywords):
            has_mermaid3 = True
            break
    
    has_mermaid = has_mermaid1 or has_mermaid2 or has_mermaid3
    print(f"[DEBUG] [MdToHtmlPlugin] 检测到 Mermaid 代码块: {has_mermaid} (标准格式={has_mermaid1}, 关键词={has_mermaid2}, codehilite={has_mermaid3})")
    
    if not has_mermaid:
        return html_content, False
    
    # 转换标准格式的 Mermaid 代码块
    def replace_mermaid_standard(match):
        mermaid_code = match.group(1)
        # 解码 HTML 实体
        mermaid_code = mermaid_code.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        # 移除语法高亮的 HTML 标签
        mermaid_code = re.sub(r'<[^>]+>', '', mermaid_code)
        print(f"[DEBUG] [MdToHtmlPlugin] 转换标准格式 Mermaid 代码块，长度={len(mermaid_code)}")
        return f'<div class="mermaid">\n{mermaid_code.strip()}\n</div>'
    
    # 转换 codehilite 格式的 Mermaid 代码块
    def replace_mermaid_codehilite(match):
        code_content = match.group(1)
        # 解码 HTML 实体
        decoded = code_content.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        # 移除语法高亮的 HTML 标签（包括 <span> 等）
        mermaid_code = re.sub(r'<[^>]+>', '', decoded)
        # 检查是否包含 mermaid 语法
        if any(keyword in mermaid_code for keyword in mermaid_keywords):
            print(f"[DEBUG] [MdToHtmlPlugin] 转换 codehilite 格式 Mermaid 代码块，长度={len(mermaid_code)}")
            return f'<div class="mermaid">\n{mermaid_code.strip()}\n</div>'
        return match.group(0)  # 不是 mermaid，保持原样
    
    # 先处理标准格式
    converted_html = re.sub(mermaid_pattern1, replace_mermaid_standard, html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # 再处理 codehilite 格式
    converted_html = re.sub(codehilite_pattern, replace_mermaid_codehilite, converted_html, flags=re.DOTALL | re.IGNORECASE)
    
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
        
        # 构建离线 Mermaid.js 支持（仅在检测到 Mermaid 时添加）
        mermaid_head = ""
        mermaid_script = ""
        if has_mermaid:
            print(f"[DEBUG] [MdToHtmlPlugin] 添加离线 Mermaid.js 支持")
            
            # 尝试获取 Mermaid.js（从缓存或下载）
            mermaid_js_code = _get_mermaid_js()
            
            if mermaid_js_code:
                print(f"[DEBUG] [MdToHtmlPlugin] Mermaid.js 已加载，长度={len(mermaid_js_code)}")
                mermaid_head = f"""    <script>
{mermaid_js_code}
    </script>
    <style>
        .mermaid {{ 
            text-align: center; 
            margin: 20px 0; 
            background: #fff; 
            padding: 20px; 
            border-radius: 5px; 
            overflow-x: auto;
        }}
    </style>"""
                mermaid_script = """    <script>
        mermaid.initialize({ 
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose'
        });
    </script>"""
            else:
                print(f"[WARN] [MdToHtmlPlugin] 无法加载 Mermaid.js，Mermaid 图表将无法渲染")
        
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
    from cedar.utils import create_name
    
    print("=" * 60)
    print("[TEST] 测试 MD 转 HTML 插件（Mermaid 支持）")
    print("=" * 60)
    
    test_dir = Path("/Users/zhangsong/Desktop/code/cedar_dev/mac-commondX/test/" + create_name())
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建测试文件
    test_md = test_dir / "test_mermaid.md"
    test_content = """# 测试 Mermaid 图表

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

## Python 代码示例

```python
def hello(name):
    # 问候函数
    print("Hello, " + name + "!")

if __name__ == "__main__":
    hello("World")
```

## JavaScript 代码示例

```javascript
function greet(name) {
    console.log("Hello, " + name + "!");
}

greet("World");
```
"""
    test_md.write_text(test_content, encoding='utf-8')
    
    # 执行转换
    success, msg, output_path = execute(str(test_md))
    print(f"[TEST] 转换结果: {msg}")
    
    if success:
        html_content = Path(output_path).read_text(encoding='utf-8')
        has_mermaid_js = "mermaid.initialize" in html_content
        mermaid_count = html_content.count('<div class="mermaid">')
        
        print(f"[TEST] HTML 包含 Mermaid.js: {has_mermaid_js}")
        print(f"[TEST] Mermaid 图表数量: {mermaid_count}")
        
        assert has_mermaid_js, "应包含 Mermaid.js"
        assert mermaid_count == 2, f"应包含 2 个 Mermaid 图表，实际: {mermaid_count}"
        print(f"[TEST] ✓ 测试通过")
    else:
        print(f"[TEST] ✗ 转换失败")

