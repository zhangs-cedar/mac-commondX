import requests
import os
from cedar.utils import print

def execute(content, action="translate"):
    """
    调用 Kimi API 进行内容处理
    
    优化点：
    1. 增加严格的超时控制，防止 UI 卡死。
    2. 使用 System Role 约束 AI 行为，确保返回结果纯净。
    3. 增加多层级错误捕获与详细日志。
    """
    
    # --- 配置读取开始 ---
    # 优先从环境变量读取，如果没有则使用硬编码的 Key
    api_key = os.getenv("KIMI_API_KEY") 
    if not api_key:
        # 如果你之前是在这里直接写字符串的，请替换下面的 "YOUR_KIMI_API_KEY"
        api_key = "YOUR_KIMI_API_KEY" 
    
    url = "https://api.moonshot.cn/v1/chat/completions"
    # --- 配置读取结束 ---

    if not content or not content.strip():
        return False, "内容为空", None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 动态构建指令
    instruction = "翻译成中文" if action == "translate" else "总结要点"
    
    # 构造消息体：通过 system 角色强制 AI 只输出干货
    messages = [
        {
            "role": "system", 
            "content": "你是一个专业的助手。请直接返回处理后的结果，不要包含任何多余的开场白、解释或结束语（如‘好的’、‘翻译如下’）。"
        },
        {
            "role": "user", 
            "content": f"请对以下内容进行{instruction}：\n\n{content}"
        }
    ]
    
    data = {
        "model": "moonshot-v1-8k",
        "messages": messages,
        "temperature": 0.3, # 降低随机性，输出更精准
    }

    try:
        # 连接超时 3.5秒，读取（等待生成）超时 15秒
        response = requests.post(
            url, 
            headers=headers, 
            json=data, 
            timeout=(3.5, 15.0)
        )
        
        # 检查 HTTP 响应状态
        response.raise_for_status()
        
        res_json = response.json()
        
        if "choices" in res_json and len(res_json["choices"]) > 0:
            answer = res_json['choices'][0]['message']['content'].strip()
            if not answer:
                return False, "AI 返回内容为空", None
            return True, "成功", answer
        else:
            return False, "API 响应格式解析失败", None

    except requests.exceptions.Timeout:
        print("[Kimi Plugin] 请求超时，请检查网络")
        return False, "网络请求超时，请检查你的网络连接", None
        
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        if status_code == 401:
            error_msg = "API Key 无效，请检查配置"
        elif status_code == 429:
            error_msg = "请求太频繁，触发了 API 限流"
        else:
            error_msg = f"服务器错误 (HTTP {status_code})"
        print(f"[Kimi Plugin] HTTP 错误: {error_msg}")
        return False, error_msg, None
        
    except Exception as e:
        print(f"[Kimi Plugin] 发生未知错误: {str(e)}")
        return False, f"异常: {str(e)}", None