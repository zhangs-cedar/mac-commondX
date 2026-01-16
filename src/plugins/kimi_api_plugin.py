#!/usr/bin/env python3
import os
import tempfile
from pathlib import Path
from openai import OpenAI
# 尝试导入本地解析库
import pytesseract
from PIL import Image
from pypdf import PdfReader
from docx import Document
from cedar.utils import print, load_config


# --- 配置初始化 ---
_config_path = os.getenv('CONFIG_PATH')
CONFIG = load_config(_config_path) if _config_path else {}
API_KEY = CONFIG.get('kimi_api', {}).get('api_key')

# Kimi API 基础 URL
KIMI_API_BASE_URL = "https://api.moonshot.cn/v1"

# 支持本地解析的扩展名
LOCAL_PARSE_EXTENSIONS = {
    'pdf': ['.pdf'],
    'docx': ['.docx'],
    'image': ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp']
}

# 初始化客户端
client = None
if API_KEY:
    try:
        client = OpenAI(api_key=API_KEY, base_url=KIMI_API_BASE_URL)
        print(f"[DEBUG] [KimiApiPlugin] ✓ OpenAI 客户端已初始化")
    except Exception as e:
        print(f"[ERROR] [KimiApiPlugin] 初始化客户端失败: {e}")
else:
    print(f"[WARN] [KimiApiPlugin] API Key 未配置")


def local_ocr_image(file_path: Path) -> str:
    """本地 OCR 解析图片 (依赖 Tesseract)"""
    try:
        print(f"[DEBUG] [LocalParser] 正在进行本地 OCR: {file_path.name}")
        # 设置语言为 简体中文+英文
        text = pytesseract.image_to_string(Image.open(file_path), lang='chi_sim+eng')
        return text.strip()
    except Exception as e:
        print(f"[WARN] [LocalParser] 本地 OCR 失败: {e} (可能未安装 tesseract)")
        return None

def local_parse_pdf(file_path: Path) -> str:
    """本地解析 PDF 文本"""
    try:
        print(f"[DEBUG] [LocalParser] 正在解析 PDF: {file_path.name}")
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"[WARN] [LocalParser] PDF 解析失败: {e}")
        return None

def local_parse_docx(file_path: Path) -> str:
    """本地解析 Word 文档"""
    try:
        print(f"[DEBUG] [LocalParser] 正在解析 DOCX: {file_path.name}")
        doc = Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs]).strip()
    except Exception as e:
        print(f"[WARN] [LocalParser] DOCX 解析失败: {e}")
        return None

def extract_content_smart(file_path: Path) -> str:
    """
    智能提取内容：优先本地解析，失败则调用 Kimi API
    """
    ext = file_path.suffix.lower()
    content = None
    
    # 1. 尝试本地解析
    if ext in LOCAL_PARSE_EXTENSIONS['image']:
        content = local_ocr_image(file_path)
    elif ext in LOCAL_PARSE_EXTENSIONS['pdf']:
        content = local_parse_pdf(file_path)
        # 如果 PDF 提取内容为空（可能是扫描版），且没报错，置为 None 触发 API 解析
        if content is not None and len(content.strip()) < 10:
            print("[DEBUG] [LocalParser] PDF 提取内容过少，疑似扫描版，转交 API 处理")
            content = None
    elif ext in LOCAL_PARSE_EXTENSIONS['docx']:
        content = local_parse_docx(file_path)
    else:
        # 普通文本尝试直接读取
        try:
            content = file_path.read_text(encoding='utf-8')
        except:
            try:
                content = file_path.read_text(encoding='gbk')
            except:
                pass

    if content:
        print(f"[DEBUG] [LocalParser] ✓ 本地解析成功，长度: {len(content)}")
        return content

    # 2. 本地失败，回退到 Kimi API 文件上传
    print(f"[DEBUG] [KimiApiPlugin] 本地解析不可用，转交 Kimi API 处理: {file_path.name}")
    return extract_content_via_api_fallback(file_path)


def extract_content_via_api_fallback(file_path: Path):
    """(回退方案) 调用 Kimi API 提取文件内容"""
    if not client:
        return None
    try:
        file_object = client.files.create(file=file_path, purpose="file-extract")
        extracted_text = client.files.content(file_id=file_object.id).text
        # 只有在 API 调用时才删除文件（Kimi 建议），这里暂时保留文件对象用于后续清理逻辑如果需要
        # client.files.delete(file_id=file_object.id) 
        return extracted_text
    except Exception as e:
        print(f"[ERROR] [KimiApiPlugin] API 解析失败: {e}")
        return None


def detect_clipboard_content_type():
    """检测剪贴板中的内容类型 (macOS AppKit)"""
    try:
        from AppKit import NSPasteboard, NSPasteboardTypeString, NSFilenamesPboardType, NSPasteboardTypePNG, NSPasteboardTypeTIFF
        pb = NSPasteboard.generalPasteboard()
        types = pb.types()
        
        has_text = NSPasteboardTypeString in types
        has_files = NSFilenamesPboardType in types
        has_image = any(t in types for t in [NSPasteboardTypePNG, NSPasteboardTypeTIFF])
        
        return has_text, has_files, has_image, types
    except Exception as e:
        print(f"[ERROR] 检测剪贴板失败: {e}")
        return False, False, False, None


def execute_from_clipboard(action: str = "translate") -> tuple:
    """入口：从剪贴板获取内容并处理"""
    has_text, has_files, has_image, types = detect_clipboard_content_type()
    content_obj = None
    tmp_file_path = None
    
    # 优先级：图片 > 文件 > 文本
    if has_image:
        print("[DEBUG] 处理剪贴板图片...")
        try:
            from AppKit import NSPasteboard, NSPasteboardTypePNG, NSPasteboardTypeTIFF
            pb = NSPasteboard.generalPasteboard()
            
            # 获取图片数据
            img_data = pb.dataForType_(NSPasteboardTypePNG) or pb.dataForType_(NSPasteboardTypeTIFF)
            if img_data:
                # 转存为临时文件供 OCR 读取
                img_bytes = bytes(img_data.bytes())
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(img_bytes)
                    tmp_file_path = Path(tmp.name)
                content_obj = tmp_file_path
        except Exception as e:
            return False, f"图片获取失败: {e}", None

    elif has_files:
        print("[DEBUG] 处理剪贴板文件...")
        try:
            from AppKit import NSPasteboard, NSFilenamesPboardType
            pb = NSPasteboard.generalPasteboard()
            files = pb.propertyListForType_(NSFilenamesPboardType)
            if files:
                content_obj = Path(files[0])
        except Exception as e:
            return False, f"文件获取失败: {e}", None

    elif has_text:
        print("[DEBUG] 处理剪贴板文本...")
        try:
            from AppKit import NSPasteboard, NSPasteboardTypeString
            pb = NSPasteboard.generalPasteboard()
            content_obj = pb.stringForType_(NSPasteboardTypeString)
        except Exception as e:
            return False, f"文本获取失败: {e}", None
    
    else:
        return False, "剪贴板为空或不支持的格式", None

    # 执行核心逻辑
    try:
        result = execute(content_obj, action)
    finally:
        # 清理临时图片文件
        if tmp_file_path and tmp_file_path.exists():
            try:
                os.unlink(tmp_file_path)
            except:
                pass
    
    return result


def execute(input_data, action="translate"):
    """
    核心处理逻辑: 解析内容 -> 构造 Prompt -> 调用 LLM
    """
    print(f"[DEBUG] [execute] 开始执行，action={action}, input_data={input_data}")
    if not API_KEY or not client:
        print(f"[ERROR] [execute] API Key 或客户端检查失败: API_KEY={bool(API_KEY)}, client={bool(client)}")
        return False, "API Key 未配置或客户端初始化失败", None
    print(f"[DEBUG] [execute] API Key 和客户端检查通过")

    final_text = ""
    source_desc = "文本"

    # 1. 解析输入数据
    print(f"[DEBUG] [execute] 步骤1: 解析输入数据...")
    if isinstance(input_data, (Path, str)) and Path(str(input_data)).exists():
        file_path = Path(str(input_data))
        source_desc = f"文件 ({file_path.name})"
        print(f"[DEBUG] [execute] 输入是文件: {file_path}")
        # 调用智能提取 (本地 -> API)
        final_text = extract_content_smart(file_path)
        print(f"[DEBUG] [execute] 文件解析完成，内容长度: {len(final_text) if final_text else 0}")
        if not final_text:
            print(f"[ERROR] [execute] 文件解析失败：内容为空或无法识别")
            return False, "文件解析失败（内容为空或无法识别）", None
    else:
        print(f"[DEBUG] [execute] 输入是文本，长度: {len(str(input_data))}")
        final_text = str(input_data)

    if not final_text.strip():
        print(f"[ERROR] [execute] 最终内容为空")
        return False, "内容为空", None
    print(f"[DEBUG] [execute] 步骤1完成，最终文本长度: {len(final_text)}")

    # 截断过长文本以防止超出 Context (简单的截断，实际可根据 token 计算)
    # Kimi 支持长文本，但为了响应速度，可以考虑适当截断或总结
    # 这里我们保留完整文本，依赖 Kimi 的长窗口能力
    
    # 2. 构造 Prompt
    print(f"[DEBUG] [execute] 步骤2: 构造 Prompt...")
    prompts = {
        "translate": "请将以下内容翻译成中文（若原文为中文则译为英文）。直接输出翻译结果，不要废话。",
        "explain": "请用通俗易懂的语言解释以下内容。保留核心信息。",
        "summarize": "请对以下内容进行结构化总结，列出关键要点。",
        "analyze": "请深入分析以下内容，指出其核心逻辑、潜在含义或优缺点。",
    }
    
    sys_prompt = "你是 Kimi，一个高效、准确的 AI 助手。你的回答必须直接切入主题，没有任何开场白或结束语。"
    user_prompt = (
        f"任务：{prompts.get(action, '请处理此内容')}。\n\n"
        f"--- 待处理内容 ({source_desc}) ---\n"
        f"{final_text[:20000]} {'...' if len(final_text) > 20000 else ''}\n" # 简单防爆
        f"--- 内容结束 ---"
    )
    print(f"[DEBUG] [execute] Prompt 构造完成，user_prompt 长度: {len(user_prompt)}")

    # 3. 调用 Kimi Chat API
    print(f"[DEBUG] [execute] 步骤3: 调用 Kimi Chat API...")
    print(f"[DEBUG] [execute] action={action}, 文本长度={len(final_text)}")
    try:
        print(f"[DEBUG] [execute] 正在发送请求到 LLM...")
        completion = client.chat.completions.create(
            model="moonshot-v1-8k", # 如果文本很长，代码逻辑可以自动切换到 32k
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
        )
        result_text = completion.choices[0].message.content
        print(f"[DEBUG] [execute] ✓ LLM 请求成功，返回内容长度: {len(result_text)}")
        return True, "成功", result_text
    except Exception as e:
        print(f"[ERROR] [execute] LLM 请求失败: {e}")
        import traceback
        print(f"[ERROR] [execute] 详细错误信息:\n{traceback.format_exc()}")
        return False, f"LLM 请求失败: {str(e)}", None

if __name__ == "__main__":
    # 简单的本地测试逻辑
    print("[DEBUG] [测试] 开始测试流程...")
    APP_DATA_DIR = Path.home() / "Library/Application Support/CommondX"
    # 配置文件路径
    CONFIG_PATH = APP_DATA_DIR / "config.yaml"
    os.environ['CONFIG_PATH'] = str(CONFIG_PATH)
    print(f"[DEBUG] [测试] 配置文件路径: {CONFIG_PATH}")

    # 加载配置
    _config_path = os.getenv('CONFIG_PATH')
    CONFIG = load_config(_config_path)
    API_KEY = CONFIG.get('kimi_api', {}).get('api_key')
    print(f"[DEBUG] [测试] API_KEY: {API_KEY[:20]}..." if API_KEY else "[DEBUG] [测试] API_KEY: 未配置")
    
    # 重新初始化 client（因为文件顶部初始化时 API_KEY 可能还未加载）
    if API_KEY:
        try:
            client = OpenAI(api_key=API_KEY, base_url=KIMI_API_BASE_URL)
            print(f"[DEBUG] [测试] ✓ OpenAI 客户端已重新初始化")
        except Exception as e:
            print(f"[ERROR] [测试] 初始化客户端失败: {e}")
            client = None
    else:
        print(f"[WARN] [测试] API Key 未配置，无法初始化客户端")
        client = None
    
    # 执行测试
    test_list = [
        "/Users/zhangsong/Desktop/文档/config.pdf",
        "/Users/zhangsong/Desktop/文档/20251220-基于双backbone双head架构网络的纺织品缺陷检测与严重程度评.docx",
        "/Users/zhangsong/Desktop/文档/1.txt",
        "/Users/zhangsong/Desktop/文档/Snipaste_2026-01-16_10-45-39.png"
        "Hello, world!",
        "Hello, world!",
    ]
    for test_item in test_list:
        print(f"[DEBUG] [测试] 开始执行 execute()...")
        result = execute(test_item, action="translate")
        print(f"[DEBUG] [测试] execute() 返回结果:")
        print(f"[DEBUG] [测试]   成功: {result[0]}")
        print(f"[DEBUG] [测试]   消息: {result[1]}")
        if result[2]:
            print(f"[DEBUG] [测试]   内容长度: {len(result[2])}")
            print(f"[DEBUG] [测试]   内容预览: {result[2][:200]}...")
        else:
            print(f"[DEBUG] [测试]   内容: None")


    