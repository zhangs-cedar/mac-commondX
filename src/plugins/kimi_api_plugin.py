#!/usr/bin/env python3
"""
Kimi API 插件

调用 Kimi API 实现翻译、解释等功能。
Kimi API 兼容 OpenAI SDK，使用 moonshot 模型。

支持处理多种类型的输入：
- 文本：直接处理文本内容
- 文件：读取文件内容并处理
- 图片：将图片转换为 base64 编码后处理
"""

import os
import base64
import tempfile
from pathlib import Path
from openai import OpenAI
from cedar.utils import print, load_config

# 配置文件路径 - 从环境变量读取
_config_path_str = os.getenv('CONFIG_PATH')
CONFIG_PATH = Path(_config_path_str)

# Kimi API 基础 URL（Moonshot API）
KIMI_API_BASE_URL = "https://api.moonshot.cn/v1"

# 支持的文本文件扩展名
TEXT_FILE_EXTENSIONS = {'.txt', '.md', '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', 
                        '.html', '.css', '.json', '.xml', '.yaml', '.yml', '.sh', '.bat',
                        '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.sql',
                        '.log', '.conf', '.config', '.ini', '.csv', '.tsv'}


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


def read_file_content(file_path: str) -> tuple:
    """
    读取文件内容
    
    Args:
        file_path: 文件路径
        
    Returns:
        tuple: (success: bool, content: str, file_type: str, error_msg: str)
    """
    print(f"[DEBUG] [KimiApiPlugin] 开始读取文件: {file_path}")
    try:
        path = Path(file_path)
        
        if not path.exists():
            print(f"[ERROR] [KimiApiPlugin] 文件不存在: {file_path}")
            return False, None, None, f"文件不存在: {file_path}"
        
        if not path.is_file():
            print(f"[ERROR] [KimiApiPlugin] 路径不是文件: {file_path}")
            return False, None, None, f"路径不是文件: {file_path}"
        
        # 检查文件扩展名
        ext = path.suffix.lower()
        print(f"[DEBUG] [KimiApiPlugin] 文件扩展名: {ext}")
        
        # 如果是图片文件，转换为 base64
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp', '.svg'}
        if ext in image_extensions:
            print(f"[DEBUG] [KimiApiPlugin] 检测到图片文件，转换为 base64...")
            try:
                with open(file_path, 'rb') as f:
                    image_data = f.read()
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                    print(f"[DEBUG] [KimiApiPlugin] ✓ 图片已转换为 base64，大小: {len(base64_data)} 字符")
                    return True, base64_data, "image", None
            except Exception as e:
                print(f"[ERROR] [KimiApiPlugin] 读取图片文件失败: {e}")
                return False, None, None, f"读取图片文件失败: {str(e)}"
        
        # 如果是文本文件，直接读取
        if ext in TEXT_FILE_EXTENSIONS or not ext:
            print(f"[DEBUG] [KimiApiPlugin] 检测到文本文件，读取内容...")
            try:
                # 尝试使用 UTF-8 编码
                content = path.read_text(encoding='utf-8')
                print(f"[DEBUG] [KimiApiPlugin] ✓ 文本文件已读取，长度: {len(content)} 字符")
                return True, content, "text", None
            except UnicodeDecodeError:
                # 如果 UTF-8 失败，尝试其他编码
                print(f"[DEBUG] [KimiApiPlugin] UTF-8 解码失败，尝试其他编码...")
                try:
                    content = path.read_text(encoding='gbk')
                    print(f"[DEBUG] [KimiApiPlugin] ✓ 使用 GBK 编码读取成功")
                    return True, content, "text", None
                except:
                    print(f"[ERROR] [KimiApiPlugin] 无法解码文件内容")
                    return False, None, None, "无法解码文件内容，请确保文件是文本格式"
            except Exception as e:
                print(f"[ERROR] [KimiApiPlugin] 读取文件失败: {e}")
                return False, None, None, f"读取文件失败: {str(e)}"
        
        # 其他类型文件，尝试作为二进制读取并转换为 base64
        print(f"[DEBUG] [KimiApiPlugin] 未知文件类型，尝试作为二进制读取...")
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
                base64_data = base64.b64encode(file_data).decode('utf-8')
                print(f"[DEBUG] [KimiApiPlugin] ✓ 文件已转换为 base64，大小: {len(base64_data)} 字符")
                return True, base64_data, "binary", None
        except Exception as e:
            print(f"[ERROR] [KimiApiPlugin] 读取文件失败: {e}")
            return False, None, None, f"读取文件失败: {str(e)}"
            
    except Exception as e:
        print(f"[ERROR] [KimiApiPlugin] 处理文件路径失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False, None, None, f"处理文件失败: {str(e)}"


def process_image_data(image_data, image_type: str = "PNG") -> tuple:
    """
    处理图片数据，转换为 base64 编码
    
    Args:
        image_data: 图片数据（NSData 或 bytes）
        image_type: 图片类型（PNG/TIFF）
        
    Returns:
        tuple: (success: bool, base64_data: str, error_msg: str)
    """
    print(f"[DEBUG] [KimiApiPlugin] 开始处理图片数据，类型: {image_type}")
    try:
        # 如果是 NSData，转换为 bytes
        if hasattr(image_data, 'bytes'):
            print(f"[DEBUG] [KimiApiPlugin] 检测到 NSData，转换为 bytes...")
            image_bytes = bytes(image_data.bytes())
        elif isinstance(image_data, bytes):
            image_bytes = image_data
        else:
            print(f"[ERROR] [KimiApiPlugin] 不支持的图片数据类型: {type(image_data)}")
            return False, None, f"不支持的图片数据类型: {type(image_data)}"
        
        print(f"[DEBUG] [KimiApiPlugin] 图片数据大小: {len(image_bytes)} 字节")
        
        # 转换为 base64
        base64_data = base64.b64encode(image_bytes).decode('utf-8')
        print(f"[DEBUG] [KimiApiPlugin] ✓ 图片已转换为 base64，大小: {len(base64_data)} 字符")
        
        return True, base64_data, None
    except Exception as e:
        print(f"[ERROR] [KimiApiPlugin] 处理图片数据失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False, None, f"处理图片数据失败: {str(e)}"


def _get_api_key() -> str:
    """
    从配置文件读取 Kimi API Key
    
    Returns:
        str: API Key，如果未配置返回 None
    """
    print(f"[DEBUG] [KimiApiPlugin] 读取配置文件: {CONFIG_PATH}")
    try:
        if CONFIG_PATH.exists():
            data = load_config(str(CONFIG_PATH)) or {}
            kimi_config = data.get('kimi_api', {})
            api_key = kimi_config.get('api_key')
            if api_key:
                print(f"[DEBUG] [KimiApiPlugin] ✓ API Key 已读取（长度={len(api_key)}）")
                return api_key
            else:
                print(f"[WARN] [KimiApiPlugin] 配置文件中未找到 API Key")
                return None
        else:
            print(f"[WARN] [KimiApiPlugin] 配置文件不存在: {CONFIG_PATH}")
            return None
    except Exception as e:
        print(f"[ERROR] [KimiApiPlugin] 读取配置失败: {e}")
        return None


def _get_client() -> 'OpenAI':
    """
    创建 OpenAI 客户端实例（使用 Moonshot API）
    
    Returns:
        OpenAI: 客户端实例，如果 API Key 未配置返回 None
    """
    print(f"[DEBUG] [KimiApiPlugin] 创建 OpenAI 客户端...")
    api_key = _get_api_key()
    if not api_key:
        print(f"[ERROR] [KimiApiPlugin] API Key 未配置，无法创建客户端")
        return None
    
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=f"{KIMI_API_BASE_URL}",
        )
        print(f"[DEBUG] [KimiApiPlugin] ✓ OpenAI 客户端已创建")
        return client
    except Exception as e:
        print(f"[ERROR] [KimiApiPlugin] 创建客户端失败: {e}")
        return None


def _get_system_messages() -> list:
    """
    获取 system messages（Kimi 角色描述）
    
    Returns:
        list: system messages 列表
    """
    return [
        {
            "role": "system",
            "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一切涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
        }
    ]


def _select_model(content_type: str, file_type: str = None, has_file_object: bool = False) -> str:
    """
    根据内容类型自动选择模型
    
    Args:
        content_type: 内容类型（text/file/image）
        file_type: 文件类型（text/image/binary，仅当 content_type=file 时有效）
        has_file_object: 是否使用了文件上传 API（file_object）
    
    Returns:
        str: 模型名称
    """
    # 如果使用了文件上传 API（PDF、DOC、图片等），必须使用 kimi-k2-turbo-preview
    if has_file_object:
        model = "kimi-k2-turbo-preview"
        print(f"[DEBUG] [KimiApiPlugin] 选择模型: {model} (文件上传，支持文件提取)")
    elif content_type == "image" or (content_type == "file" and file_type in ["image", "binary"]):
        model = "kimi-k2-turbo-preview"
        print(f"[DEBUG] [KimiApiPlugin] 选择模型: {model} (复杂内容)")
    else:
        # 纯文本内容使用 moonshot-v1-8k
        model = "moonshot-v1-8k"
        print(f"[DEBUG] [KimiApiPlugin] 选择模型: {model} (简单文本内容)")
    
    return model


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
    content_type = None
    
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
                content = (image_data, image_type)
                content_type = "image"
                print(f"[DEBUG] [KimiApiPlugin] ✓ 图片数据已获取，类型: {image_type}")
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
                content = file_list
                content_type = "file"
                print(f"[DEBUG] [KimiApiPlugin] ✓ 获取到 {len(file_list)} 个文件路径")
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
                content_type = "text"
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
    return execute(content, action, content_type)


def execute(content, action: str = "translate", content_type: str = None) -> tuple:
    """
    调用 Kimi API 处理内容（支持文本、文件、图片）
    
    使用 OpenAI SDK 和文件上传 API，支持 PDF、DOC、图片 OCR 等高级功能。
    
    Args:
        content: 要处理的内容，可以是：
            - str: 文本内容或文件路径
            - list: 文件路径列表
            - bytes/NSData: 图片数据
        action: 处理动作，可选值：
            - "translate": 翻译（默认翻译为中文）
            - "explain": 解释
            - "summarize": 总结
            - "analyze": 分析（用于图片和文件）
        content_type: 内容类型，可选值：
            - "text": 文本内容
            - "file": 文件路径
            - "image": 图片数据
            - None: 自动检测
    
    Returns:
        tuple: (success: bool, message: str, result: str)
    """
    print(f"[DEBUG] [KimiApiPlugin] 开始处理内容，action={action}, content_type={content_type}")
    
    # 自动检测内容类型
    if content_type is None:
        print(f"[DEBUG] [KimiApiPlugin] 自动检测内容类型...")
        if isinstance(content, str):
            # 检查是否是文件路径
            path = Path(content)
            if path.exists() and path.is_file():
                content_type = "file"
                print(f"[DEBUG] [KimiApiPlugin] 检测到文件路径")
            else:
                content_type = "text"
                print(f"[DEBUG] [KimiApiPlugin] 检测到文本内容")
        elif isinstance(content, list):
            content_type = "file"
            print(f"[DEBUG] [KimiApiPlugin] 检测到文件路径列表")
        elif hasattr(content, 'bytes') or isinstance(content, bytes) or (isinstance(content, tuple) and len(content) == 2):
            content_type = "image"
            print(f"[DEBUG] [KimiApiPlugin] 检测到图片数据")
        else:
            print(f"[ERROR] [KimiApiPlugin] 无法识别内容类型: {type(content)}")
            return False, f"不支持的内容类型: {type(content)}", None
    
    # 创建客户端
    client = _get_client()
    if not client:
        return False, "Kimi API Key 未配置，请在配置文件中设置 kimi_api.api_key", None
    
    # 根据内容类型处理
    file_type = None
    file_path = None
    file_object = None
    
    if content_type == "text":
        print(f"[DEBUG] [KimiApiPlugin] 处理文本内容，长度={len(content)}")
        if not content or not content.strip():
            print(f"[ERROR] [KimiApiPlugin] 文本内容为空")
            return False, "文本内容为空", None
        print(f"[DEBUG] [KimiApiPlugin] 文本内容预览: {content[:100]}...")
    
    elif content_type == "file":
        print(f"[DEBUG] [KimiApiPlugin] 处理文件内容...")
        # 如果是列表，取第一个文件
        if isinstance(content, list):
            if not content:
                print(f"[ERROR] [KimiApiPlugin] 文件列表为空")
                return False, "文件列表为空", None
            file_path = content[0]
            print(f"[DEBUG] [KimiApiPlugin] 处理文件列表中的第一个文件: {file_path}")
        else:
            file_path = content
        
        file_path = Path(file_path)
        if not file_path.exists() or not file_path.is_file():
            return False, f"文件不存在: {file_path}", None
        
        # 检测文件类型
        ext = file_path.suffix.lower()
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp', '.svg'}
        if ext in image_extensions:
            file_type = "image"
        elif ext in TEXT_FILE_EXTENSIONS or not ext:
            file_type = "text"
        else:
            file_type = "binary"
        
        print(f"[DEBUG] [KimiApiPlugin] 文件类型: {file_type}, 扩展名: {ext}")
        
        # 使用文件上传 API
        try:
            print(f"[DEBUG] [KimiApiPlugin] 上传文件到 Moonshot API...")
            file_object = client.files.create(
                file=file_path,
                purpose="file-extract"
            )
            print(f"[DEBUG] [KimiApiPlugin] ✓ 文件已上传，file_id: {file_object.id}")
            
            # 获取文件内容
            print(f"[DEBUG] [KimiApiPlugin] 获取文件内容...")
            file_content = client.files.content(file_id=file_object.id).text
            print(f"[DEBUG] [KimiApiPlugin] ✓ 文件内容已获取，长度: {len(file_content)} 字符")
            
            # 检查文件内容是否为空
            if not file_content or not file_content.strip():
                print(f"[WARN] [KimiApiPlugin] 文件内容为空，可能文件提取失败")
                return False, "文件内容提取失败，请确保文件格式正确且未被加密", None
        except Exception as e:
            print(f"[ERROR] [KimiApiPlugin] 文件上传失败: {e}")
            import traceback
            print(traceback.format_exc())
            return False, f"文件上传失败: {str(e)}", None
    
    elif content_type == "image":
        print(f"[DEBUG] [KimiApiPlugin] 处理图片数据...")
        # 获取图片类型和数据
        image_type = "PNG"  # 默认
        if isinstance(content, tuple) and len(content) == 2:
            image_data, image_type = content
        else:
            image_data = content
        
        # 将图片数据保存为临时文件
        tmp_file_path = None
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
            
            # 使用文件上传 API
            print(f"[DEBUG] [KimiApiPlugin] 上传图片到 Moonshot API...")
            file_object = client.files.create(
                file=tmp_file_path,
                purpose="file-extract"
            )
            print(f"[DEBUG] [KimiApiPlugin] ✓ 图片已上传，file_id: {file_object.id}")
            
            # 获取文件内容
            print(f"[DEBUG] [KimiApiPlugin] 获取图片内容...")
            file_content = client.files.content(file_id=file_object.id).text
            print(f"[DEBUG] [KimiApiPlugin] ✓ 图片内容已获取，长度: {len(file_content)} 字符")
            
            # 检查文件内容是否为空
            if not file_content or not file_content.strip():
                print(f"[WARN] [KimiApiPlugin] 图片内容为空，可能文件提取失败")
                # 清理临时文件
                if tmp_file_path and tmp_file_path.exists():
                    try:
                        tmp_file_path.unlink()
                    except:
                        pass
                return False, "图片内容提取失败，请确保图片格式正确", None
            
            file_type = "image"
            file_path = tmp_file_path  # 用于后续清理
        except Exception as e:
            print(f"[ERROR] [KimiApiPlugin] 图片处理失败: {e}")
            import traceback
            print(traceback.format_exc())
            # 清理临时文件
            if tmp_file_path and tmp_file_path.exists():
                try:
                    tmp_file_path.unlink()
                    print(f"[DEBUG] [KimiApiPlugin] 临时文件已清理（错误时）")
                except:
                    pass
            return False, f"图片处理失败: {str(e)}", None
    
    else:
        print(f"[ERROR] [KimiApiPlugin] 不支持的内容类型: {content_type}")
        return False, f"不支持的内容类型: {content_type}", None
    
    # 选择模型（如果使用了文件上传 API，必须使用 kimi-k2-turbo-preview）
    model = _select_model(content_type, file_type, has_file_object=(file_object is not None))
    
    # 构建 messages
    messages = _get_system_messages()
    
    # 如果有文件内容，添加为 system message（第二个 system message，包含文件内容）
    if file_object and file_content:
        messages.append({
            "role": "system",
            "content": file_content,
        })
        print(f"[DEBUG] [KimiApiPlugin] 文件内容已添加到 system message，长度: {len(file_content)} 字符")
    
    # 根据 action 构建 user message
    prompts = {
        "translate": "请将以下文本翻译成中文，保持原意和语气，如果已经是中文则翻译成英文：\n\n",
        "explain": "请解释以下内容，用简洁明了的中文说明：\n\n",
        "summarize": "请总结以下内容，用简洁的中文概括要点：\n\n",
        "analyze": "请分析以下内容，用中文详细说明：\n\n",
    }
    
    if content_type == "text":
        prompt = prompts.get(action, prompts["translate"])
        user_message = prompt + content
    elif content_type == "file" or content_type == "image":
        # 对于文件/图片，根据 action 调整提示词
        if file_type == "image":
            if action == "translate":
                action = "analyze"
            prompts = {
                "analyze": "请分析这个图片的内容，用中文详细描述图片中的内容、场景、对象等信息。",
                "explain": "请解释这个图片的内容，用简洁明了的中文说明图片的含义和主要内容。",
            }
        else:
            # 文件类型（PDF、DOC等），使用更明确的提示词
            file_name = Path(file_path).name if file_path else "文件"
            prompts = {
                "analyze": f"请分析这个{file_name}的内容，用中文详细说明文件的主要内容和要点。",
                "explain": f"请解释这个{file_name}的内容，用简洁明了的中文说明文件的含义和主要内容。",
                "summarize": f"请总结这个{file_name}的内容，用简洁的中文概括要点。",
                "translate": f"请将这个{file_name}的内容翻译成中文，保持原意和语气。",
            }
        prompt = prompts.get(action, prompts.get("analyze", "请分析这个文件的内容。"))
        user_message = prompt
    else:
        user_message = prompts.get(action, prompts["translate"])
    
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    print(f"[DEBUG] [KimiApiPlugin] 构建 messages 完成，开始调用 API...")
    print(f"[DEBUG] [KimiApiPlugin] 使用模型: {model}, action: {action}")
    
    try:
        # 调用 API
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.6,
        )
        
        result_text = completion.choices[0].message.content
        print(f"[DEBUG] [KimiApiPlugin] ✓ API 调用成功，结果长度={len(result_text)}")
        
        # 清理临时文件（如果是图片）
        if content_type == "image" and file_path and file_path.exists():
            try:
                file_path.unlink()
                print(f"[DEBUG] [KimiApiPlugin] 临时文件已清理（成功时）")
            except:
                pass
        
        return True, "处理成功", result_text
        
    except Exception as e:
        print(f"[ERROR] [KimiApiPlugin] API 调用失败: {e}")
        import traceback
        print(traceback.format_exc())
        
        # 清理临时文件（如果是图片）
        if content_type == "image" and file_path and file_path.exists():
            try:
                file_path.unlink()
                print(f"[DEBUG] [KimiApiPlugin] 临时文件已清理（错误时）")
            except:
                pass
        
        return False, f"API 调用失败: {str(e)}", None


if __name__ == "__main__":
    """测试代码"""
    print("=" * 60)
    print("[TEST] 测试 Kimi API 插件")
    print("=" * 60)
    print()
    
    # 测试1: 文本处理
    print("[TEST 1] 测试文本处理...")
    test_text = "Hello, world! This is a test."
    print(f"[TEST 1] 测试文本: {test_text}")
    success, msg, result = execute(test_text, "translate")
    print(f"[TEST 1] 转换结果: {msg}")
    if success:
        print(f"[TEST 1] ✓ 测试通过，结果: {result}")
    else:
        print(f"[TEST 1] ✗ 测试失败: {msg}")
    print()
    
    # 测试2: 从剪贴板获取内容并处理
    print("[TEST 2] 测试从剪贴板获取内容并处理...")
    print("[TEST 2] 请确保剪贴板中有内容（文本/文件/图片）")
    success, msg, result = execute_from_clipboard("analyze")
    print(f"[TEST 2] 处理结果: {msg}")
    if success:
        print(f"[TEST 2] ✓ 测试通过，结果: {result}")
    else:
        print(f"[TEST 2] ✗ 测试失败: {msg}")
    print()
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


