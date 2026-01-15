#!/usr/bin/env python3
"""
Kimi API 插件

调用 Kimi API 实现翻译、解释等功能。
Kimi API 兼容 OpenAI SDK，使用 moonshot 模型。

支持处理多种类型的输入：
- 文本：直接处理文本内容
- 文件：使用文件上传 API 处理（支持 PDF、DOC、图片 OCR 等）
- 图片：使用文件上传 API 处理
"""

import os
import tempfile
from pathlib import Path
from openai import OpenAI
from cedar.utils import print, load_config

# --- 配置初始化 ---
_config_path = os.getenv('CONFIG_PATH')
CONFIG = load_config(_config_path) if _config_path else {}
API_KEY = CONFIG.get('kimi_api', {}).get('api_key')

# Kimi API 基础 URL（Moonshot API）
KIMI_API_BASE_URL = "https://api.moonshot.cn/v1"

# 需要通过 API 提取的文件扩展名（PDF、图片、DOCX 等）
API_EXTRACT_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.docx', '.gif', '.tiff', '.webp'}

# 初始化客户端
client = None
if API_KEY:
    try:
        client = OpenAI(api_key=API_KEY, base_url=KIMI_API_BASE_URL)
        print(f"[DEBUG] [KimiApiPlugin] ✓ OpenAI 客户端已初始化")
    except Exception as e:
        print(f"[ERROR] [KimiApiPlugin] 初始化客户端失败: {e}")
else:
    print(f"[WARN] [KimiApiPlugin] API Key 未配置，请在配置文件中设置 kimi_api.api_key")


def detect_clipboard_content_type():
    """
    检测剪贴板中的内容类型
    
    Returns:
        tuple: (has_text: bool, has_files: bool, has_image: bool, types: list)
    """
    print("[DEBUG] [KimiApiPlugin] 开始检测剪贴板内容类型...")
    try:
        from AppKit import (
            NSPasteboard,
            NSPasteboardTypeString,
            NSFilenamesPboardType,
            NSPasteboardTypePNG,
            NSPasteboardTypeTIFF
        )
        
        pb = NSPasteboard.generalPasteboard()
        types = pb.types()
        print(f"[DEBUG] [KimiApiPlugin] 剪贴板数据类型数量: {len(types) if types else 0}")
        
        has_text = False
        has_files = False
        has_image = False
        
        if types:
            for t in types:
                if t == NSPasteboardTypeString:
                    has_text = True
                    print(f"[DEBUG] [KimiApiPlugin] ✓ 检测到文本类型")
                elif t == NSFilenamesPboardType:
                    has_files = True
                    print(f"[DEBUG] [KimiApiPlugin] ✓ 检测到文件类型")
                elif t in [NSPasteboardTypePNG, NSPasteboardTypeTIFF]:
                    has_image = True
                    print(f"[DEBUG] [KimiApiPlugin] ✓ 检测到图片类型: {t}")
        
        print(f"[DEBUG] [KimiApiPlugin] 类型汇总 - 文本: {has_text}, 文件: {has_files}, 图片: {has_image}")
        return has_text, has_files, has_image, types
    except Exception as e:
        print(f"[ERROR] [KimiApiPlugin] 检测剪贴板类型失败: {e}")
        return False, False, False, None


def extract_content_via_api(file_path: Path):
    """
    调用 Kimi API 提取图片(OCR)或 PDF/DOC 文本
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 提取的文本内容，失败返回 None
    """
    print(f"[DEBUG] [KimiApiPlugin] 正在通过 API 解析文件: {file_path.name}...")
    if not client:
        print(f"[ERROR] [KimiApiPlugin] API Key 未配置，无法调用 API")
        return None
    
    try:
        # 上传文件到 Moonshot
        print(f"[DEBUG] [KimiApiPlugin] 上传文件到 Moonshot API...")
        file_object = client.files.create(file=file_path, purpose="file-extract")
        print(f"[DEBUG] [KimiApiPlugin] ✓ 文件已上传，file_id: {file_object.id}")
        
        # 提取文本内容
        print(f"[DEBUG] [KimiApiPlugin] 获取文件内容...")
        extracted_text = client.files.content(file_id=file_object.id).text
        print(f"[DEBUG] [KimiApiPlugin] ✓ 文件内容已获取，长度: {len(extracted_text)} 字符")
        
        # 调试输出：用横线包裹打印提取的内容预览
        print("-" * 30)
        print(f"[解析成功] 内容预览:\n{extracted_text[:200]}...")
        print("-" * 30)
        
        return extracted_text
    except Exception as e:
        print(f"[ERROR] [KimiApiPlugin] API 解析失败: {e}")
        import traceback
        print(traceback.format_exc())
        return None


def execute_from_clipboard(action: str = "translate") -> tuple:
    """
    从剪贴板获取内容并调用 Kimi API 处理
    
    自动检测剪贴板中的内容类型（文本/文件/图片），获取内容后调用 execute 处理。
    
    Args:
        action: 处理动作，可选值：
            - "translate": 翻译（默认翻译为中文）
            - "explain": 解释
            - "summarize": 总结
            - "analyze": 分析（用于图片和文件）
    
    Returns:
        tuple: (success: bool, message: str, result: str)
    """
    print(f"[DEBUG] [KimiApiPlugin] 从剪贴板获取内容并处理，action={action}")
    
    # 检测剪贴板内容类型
    has_text, has_files, has_image, types = detect_clipboard_content_type()
    
    content = None
    tmp_file_path = None  # 用于临时文件清理
    
    # 优先级：图片 > 文件 > 文本
    if has_image:
        print(f"[DEBUG] [KimiApiPlugin] 剪贴板中有图片，获取图片数据...")
        try:
            from AppKit import (
                NSPasteboard,
                NSPasteboardTypePNG,
                NSPasteboardTypeTIFF
            )
            pb = NSPasteboard.generalPasteboard()
            
            image_data = None
            image_type = None
            
            # 优先尝试 PNG
            if NSPasteboardTypePNG in types:
                image_data = pb.dataForType_(NSPasteboardTypePNG)
                if image_data:
                    image_type = "PNG"
                    print(f"[DEBUG] [KimiApiPlugin] ✓ 获取到 PNG 图片数据")
            
            # 如果没有 PNG，尝试 TIFF
            if not image_data and NSPasteboardTypeTIFF in types:
                image_data = pb.dataForType_(NSPasteboardTypeTIFF)
                if image_data:
                    image_type = "TIFF"
                    print(f"[DEBUG] [KimiApiPlugin] ✓ 获取到 TIFF 图片数据")
            
            if image_data:
                # 将图片数据保存为临时文件
                try:
                    # 转换 NSData 为 bytes
                    if hasattr(image_data, 'bytes'):
                        image_bytes = bytes(image_data.bytes())
                    elif isinstance(image_data, bytes):
                        image_bytes = image_data
                    else:
                        return False, f"不支持的图片数据类型: {type(image_data)}", None
                    
                    # 创建临时文件
                    suffix = ".png" if image_type == "PNG" else ".tiff"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                        tmp_file.write(image_bytes)
                        tmp_file_path = Path(tmp_file.name)
                    
                    print(f"[DEBUG] [KimiApiPlugin] 图片已保存到临时文件: {tmp_file_path}")
                    content = str(tmp_file_path)
                except Exception as e:
                    print(f"[ERROR] [KimiApiPlugin] 保存图片到临时文件失败: {e}")
                    return False, f"保存图片失败: {str(e)}", None
        except Exception as e:
            print(f"[ERROR] [KimiApiPlugin] 获取图片数据失败: {e}")
            return False, f"获取图片数据失败: {str(e)}", None
    
    elif has_files:
        print(f"[DEBUG] [KimiApiPlugin] 剪贴板中有文件，获取文件路径...")
        try:
            from AppKit import NSPasteboard, NSFilenamesPboardType
            pb = NSPasteboard.generalPasteboard()
            file_list = pb.propertyListForType_(NSFilenamesPboardType)
            
            if file_list:
                content = file_list[0]  # 取第一个文件
                print(f"[DEBUG] [KimiApiPlugin] ✓ 获取到文件路径: {content}")
            else:
                print(f"[ERROR] [KimiApiPlugin] 文件列表为空")
                return False, "剪贴板中文件列表为空", None
        except Exception as e:
            print(f"[ERROR] [KimiApiPlugin] 获取文件路径失败: {e}")
            return False, f"获取文件路径失败: {str(e)}", None
    
    elif has_text:
        print(f"[DEBUG] [KimiApiPlugin] 剪贴板中有文本，获取文本内容...")
        try:
            from AppKit import NSPasteboard, NSPasteboardTypeString
            pb = NSPasteboard.generalPasteboard()
            text_content = pb.stringForType_(NSPasteboardTypeString)
            
            if text_content:
                content = text_content
                print(f"[DEBUG] [KimiApiPlugin] ✓ 获取到文本内容，长度: {len(text_content)}")
            else:
                print(f"[ERROR] [KimiApiPlugin] 文本内容为空")
                return False, "剪贴板中文本内容为空", None
        except Exception as e:
            print(f"[ERROR] [KimiApiPlugin] 获取文本内容失败: {e}")
            return False, f"获取文本内容失败: {str(e)}", None
    
    else:
        print(f"[ERROR] [KimiApiPlugin] 剪贴板中没有支持的内容类型")
        return False, "剪贴板中没有支持的内容类型（文本/文件/图片）", None
    
    # 调用 execute 处理内容
    print(f"[DEBUG] [KimiApiPlugin] 调用 execute 处理内容...")
    result = execute(content, action)
    
    # 清理临时文件（如果是剪贴板图片）
    if tmp_file_path and tmp_file_path.exists():
        try:
            tmp_file_path.unlink()
            print(f"[DEBUG] [KimiApiPlugin] 临时文件已清理")
        except Exception as e:
            print(f"[WARN] [KimiApiPlugin] 清理临时文件失败: {e}")
    
    return result


def execute(input_data, action="translate"):
    """
    核心执行逻辑
    
    支持处理文本、文件路径、文件路径列表。
    文件处理：PDF/图片/DOCX 等通过 API 提取，文本文件优先本地读取，失败时自动转交 API。
    
    Args:
        input_data: 剪贴板文本或文件路径（str 或 list）
        action: 处理动作，可选值：
            - "translate": 翻译（默认翻译为中文）
            - "explain": 解释
            - "summarize": 总结
            - "analyze": 分析（用于图片和文件）
    
    Returns:
        tuple: (success: bool, message: str, result: str)
    """
    print(f"[DEBUG] [KimiApiPlugin] 开始处理内容，action={action}")
    
    if not API_KEY:
        print(f"[ERROR] [KimiApiPlugin] API Key 未配置")
        return False, "API Key 未配置", None
    
    if not client:
        print(f"[ERROR] [KimiApiPlugin] 客户端未初始化")
        return False, "客户端未初始化", None
    
    source_info = "剪贴板文本"
    final_content = ""
    file_path = None
    use_api_extract = False
    
    # 1. 路径检测逻辑
    potential_path = None
    if isinstance(input_data, list):
        if not input_data:
            return False, "文件列表为空", None
        potential_path = Path(input_data[0])
        print(f"[DEBUG] [KimiApiPlugin] 检测到文件路径列表，处理第一个文件: {potential_path}")
    else:
        potential_path = Path(str(input_data).strip())
    
    # 检查是否是文件路径
    if potential_path.exists() and potential_path.is_file():
        file_path = potential_path
        ext = file_path.suffix.lower()
        source_info = f"文件 ({file_path.name})"
        print(f"[DEBUG] [KimiApiPlugin] 检测到文件路径: {file_path}, 扩展名: {ext}")
        
        # 判断是否需要通过 API 提取（PDF、图片、DOCX 等）
        if ext in API_EXTRACT_EXTENSIONS:
            print(f"[DEBUG] [KimiApiPlugin] 文件类型需要 API 提取: {ext}")
            final_content = extract_content_via_api(file_path)
            use_api_extract = True
            if not final_content:
                return False, "文件内容提取失败，请确保文件格式正确且未被加密", None
        else:
            # 普通文本文件优先本地读取
            print(f"[DEBUG] [KimiApiPlugin] 尝试本地读取文本文件...")
            try:
                final_content = file_path.read_text(encoding='utf-8')
                print(f"[DEBUG] [KimiApiPlugin] ✓ 本地读取文本文件成功: {file_path.name}")
            except UnicodeDecodeError:
                # 如果 UTF-8 失败，尝试其他编码
                print(f"[DEBUG] [KimiApiPlugin] UTF-8 解码失败，尝试 GBK 编码...")
                try:
                    final_content = file_path.read_text(encoding='gbk')
                    print(f"[DEBUG] [KimiApiPlugin] ✓ 使用 GBK 编码读取成功")
                except:
                    # 本地读取失败，自动转交 API 处理
                    print(f"[DEBUG] [KimiApiPlugin] 本地读取失败，自动转交 API 处理...")
                    final_content = extract_content_via_api(file_path)
                    use_api_extract = True
                    if not final_content:
                        return False, "文件内容提取失败", None
            except Exception as e:
                # 本地读取失败，自动转交 API 处理
                print(f"[DEBUG] [KimiApiPlugin] 本地读取失败 ({e})，自动转交 API 处理...")
                final_content = extract_content_via_api(file_path)
                use_api_extract = True
                if not final_content:
                    return False, f"文件内容提取失败: {str(e)}", None
    else:
        # 纯文本
        final_content = str(input_data)
        print(f"[DEBUG] [KimiApiPlugin] 检测到文本内容，长度: {len(final_content)}")
    
    if not final_content or not final_content.strip():
        return False, "未获取到有效内容", None
    
    # 2. 构造精简提示词
    prompts = {
        "translate": "请将其翻译成中文（如原文为中文则翻译为英文）",
        "explain": "请解释这段内容",
        "summarize": "请简要总结核心要点",
        "analyze": "请分析这段内容",
    }
    
    task_desc = prompts.get(action, "请处理以下内容")
    
    # 告知 AI 来源以提高理解准确度，并强制简短回答
    user_message = (
        f"你现在收到了来自 {source_info} 的内容。\n"
        f"任务目标：{task_desc}。\n"
        f"要求：回答必须准确，并保持【极度简短、不啰嗦】。\n\n"
        f"--- 内容开始 ---\n"
        f"{final_content}\n"
        f"--- 内容结束 ---"
    )
    
    # 3. 选择模型
    if use_api_extract:
        model = "kimi-k2-turbo-preview"
        print(f"[DEBUG] [KimiApiPlugin] 选择模型: {model} (文件上传，支持文件提取)")
    else:
        model = "moonshot-v1-8k"
        print(f"[DEBUG] [KimiApiPlugin] 选择模型: {model} (简单文本内容)")
    
    # 4. 发送给 Kimi
    print(f"[DEBUG] [KimiApiPlugin] 构建 messages 完成，开始调用 API...")
    print(f"[DEBUG] [KimiApiPlugin] 使用模型: {model}, action: {action}")
    
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是 Kimi，一个专业的助手。你总是能给出精炼、无废话的回答。"},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
        )
        
        result_text = completion.choices[0].message.content
        print(f"[DEBUG] [KimiApiPlugin] ✓ API 调用成功，结果长度={len(result_text)}")
        
        return True, "处理成功", result_text
    except Exception as e:
        print(f"[ERROR] [KimiApiPlugin] API 请求失败: {e}")
        import traceback
        print(traceback.format_exc())
        
        return False, f"API 请求失败: {str(e)}", None
