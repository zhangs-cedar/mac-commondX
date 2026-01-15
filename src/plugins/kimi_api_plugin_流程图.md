# Kimi API 插件流程图

## 文件概述

`kimi_api_plugin.py` 是调用 Kimi API（Moonshot AI）的插件，支持处理文本、文件和图片，实现翻译、解释、总结、分析等功能。

## 主要函数结构

### 入口函数
- `execute_from_clipboard(action)` - 从剪贴板获取内容并处理
- `execute(content, action, content_type)` - 主要执行函数，处理各种类型的内容

### 辅助函数
- `detect_clipboard_content_type()` - 检测剪贴板内容类型
- `_get_api_key()` - 从配置文件读取 API Key
- `_get_client()` - 创建 OpenAI 客户端实例
- `_get_system_messages()` - 获取系统消息（Kimi 角色描述）
- `_select_model()` - 根据内容类型选择模型

### 已废弃函数（待删除）
- `read_file_content()` - 不再使用，已改用文件上传 API
- `process_image_data()` - 不再使用，已改用文件上传 API

## 执行流程图

```mermaid
graph TB
    Start([开始]) --> Entry{入口函数}
    
    Entry -->|从剪贴板| Clipboard[execute_from_clipboard]
    Entry -->|直接调用| Execute[execute]
    
    Clipboard --> Detect[detect_clipboard_content_type]
    Detect -->|检测类型| TypeCheck{内容类型}
    
    TypeCheck -->|图片| GetImage[获取图片数据<br/>PNG/TIFF]
    TypeCheck -->|文件| GetFile[获取文件路径列表]
    TypeCheck -->|文本| GetText[获取文本内容]
    TypeCheck -->|无支持类型| Error1[返回错误]
    
    GetImage --> Execute
    GetFile --> Execute
    GetText --> Execute
    
    Execute --> AutoDetect{自动检测<br/>内容类型?}
    AutoDetect -->|是| DetectType[检测内容类型<br/>str/list/bytes/tuple]
    AutoDetect -->|否| UseType[使用指定类型]
    
    DetectType --> UseType
    UseType --> GetClient[_get_client]
    
    GetClient --> GetKey[_get_api_key]
    GetKey -->|读取配置| ConfigFile[config.yaml]
    ConfigFile -->|API Key存在?| KeyCheck{API Key}
    KeyCheck -->|否| Error2[返回错误:<br/>API Key未配置]
    KeyCheck -->|是| CreateClient[创建OpenAI客户端<br/>base_url=Moonshot]
    
    CreateClient --> ContentType{内容类型}
    
    ContentType -->|文本| TextProcess[处理文本内容<br/>验证非空]
    ContentType -->|文件| FileProcess[处理文件]
    ContentType -->|图片| ImageProcess[处理图片]
    ContentType -->|其他| Error3[返回错误:<br/>不支持的类型]
    
    FileProcess --> FileCheck{文件存在?}
    FileCheck -->|否| Error4[返回错误:<br/>文件不存在]
    FileCheck -->|是| FileType[检测文件类型<br/>image/text/binary]
    FileType --> UploadFile[上传文件到API<br/>client.files.create]
    UploadFile --> GetFileContent[获取文件内容<br/>client.files.content]
    GetFileContent --> FileContentCheck{内容为空?}
    FileContentCheck -->|是| Error5[返回错误:<br/>文件提取失败]
    FileContentCheck -->|否| FileContent[file_content]
    
    ImageProcess --> ImageData[获取图片数据<br/>NSData/bytes]
    ImageData --> SaveTemp[保存为临时文件<br/>.png/.tiff]
    SaveTemp --> UploadImage[上传图片到API<br/>client.files.create]
    UploadImage --> GetImageContent[获取图片内容<br/>client.files.content]
    GetImageContent --> ImageContentCheck{内容为空?}
    ImageContentCheck -->|是| CleanTemp1[清理临时文件]
    CleanTemp1 --> Error6[返回错误:<br/>图片提取失败]
    ImageContentCheck -->|否| ImageContent[file_content]
    
    TextProcess --> SelectModel
    FileContent --> SelectModel
    ImageContent --> SelectModel
    
    SelectModel[_select_model] --> ModelCheck{选择模型}
    ModelCheck -->|有file_object| Model1[kimi-k2-turbo-preview<br/>文件上传]
    ModelCheck -->|图片/复杂文件| Model1
    ModelCheck -->|纯文本| Model2[moonshot-v1-8k<br/>简单文本]
    
    Model1 --> BuildMessages
    Model2 --> BuildMessages
    
    BuildMessages[_get_system_messages] --> SystemMsg[添加系统消息<br/>Kimi角色描述]
    SystemMsg --> FileMsgCheck{有file_content?}
    FileMsgCheck -->|是| AddFileMsg[添加文件内容<br/>作为system message]
    FileMsgCheck -->|否| BuildUserMsg
    
    AddFileMsg --> BuildUserMsg[构建user message]
    BuildUserMsg --> ActionType{action类型}
    
    ActionType -->|translate| Prompt1[翻译提示词]
    ActionType -->|explain| Prompt2[解释提示词]
    ActionType -->|summarize| Prompt3[总结提示词]
    ActionType -->|analyze| Prompt4[分析提示词]
    
    Prompt1 --> AddUserMsg
    Prompt2 --> AddUserMsg
    Prompt3 --> AddUserMsg
    Prompt4 --> AddUserMsg
    
    AddUserMsg[添加user message] --> CallAPI[调用API<br/>client.chat.completions.create]
    CallAPI --> APICheck{API调用成功?}
    
    APICheck -->|否| CleanTemp2[清理临时文件<br/>如果存在]
    CleanTemp2 --> Error7[返回错误:<br/>API调用失败]
    
    APICheck -->|是| GetResult[获取结果文本<br/>completion.choices[0].message.content]
    GetResult --> CleanTemp3[清理临时文件<br/>如果存在]
    CleanTemp3 --> Success[返回成功<br/>result_text]
    
    Error1 --> End([结束])
    Error2 --> End
    Error3 --> End
    Error4 --> End
    Error5 --> End
    Error6 --> End
    Error7 --> End
    Success --> End
    
    style Start fill:#90EE90
    style End fill:#FFB6C1
    style Error1 fill:#FF6B6B
    style Error2 fill:#FF6B6B
    style Error3 fill:#FF6B6B
    style Error4 fill:#FF6B6B
    style Error5 fill:#FF6B6B
    style Error6 fill:#FF6B6B
    style Error7 fill:#FF6B6B
    style Success fill:#90EE90
    style Model1 fill:#87CEEB
    style Model2 fill:#87CEEB
```

## 详细流程说明

### 1. 入口流程

#### execute_from_clipboard(action)
1. 调用 `detect_clipboard_content_type()` 检测剪贴板类型
2. 按优先级获取内容：图片 > 文件 > 文本
3. 调用 `execute()` 处理内容

#### execute(content, action, content_type)
1. 如果 `content_type` 为 `None`，自动检测内容类型
2. 创建 OpenAI 客户端（调用 `_get_client()`）
3. 根据内容类型分别处理

### 2. 内容处理流程

#### 文本处理
- 验证文本非空
- 直接使用文本内容

#### 文件处理
1. 验证文件存在
2. 检测文件类型（image/text/binary）
3. 上传文件到 Moonshot API：`client.files.create(file=file_path, purpose="file-extract")`
4. 获取文件内容：`client.files.content(file_id=file_object.id).text`
5. 验证文件内容非空
6. 将文件内容添加到 system message

#### 图片处理
1. 转换图片数据（NSData -> bytes）
2. 保存为临时文件（.png 或 .tiff）
3. 上传图片到 Moonshot API：`client.files.create(file=tmp_file_path, purpose="file-extract")`
4. 获取图片内容：`client.files.content(file_id=file_object.id).text`
5. 验证图片内容非空
6. 将图片内容添加到 system message
7. 在成功/失败后清理临时文件

### 3. 模型选择流程

`_select_model(content_type, file_type, has_file_object)`

- **有 file_object**（使用了文件上传 API）→ `kimi-k2-turbo-preview`
- **图片或复杂文件**（image/binary）→ `kimi-k2-turbo-preview`
- **纯文本** → `moonshot-v1-8k`

### 4. 消息构建流程

1. 获取系统消息：`_get_system_messages()` - Kimi 角色描述
2. 如果有文件内容，添加为第二个 system message
3. 根据 action 和内容类型构建 user message：
   - **文本**：提示词 + 文本内容
   - **文件/图片**：根据文件类型和 action 调整提示词

### 5. API 调用流程

1. 调用 `client.chat.completions.create(model, messages, temperature=0.6)`
2. 获取结果：`completion.choices[0].message.content`
3. 清理临时文件（如果是图片）
4. 返回结果

## 关键配置

- **API Base URL**: `https://api.moonshot.cn/v1`
- **配置文件路径**: 从环境变量 `CONFIG_PATH` 读取
- **API Key 配置**: `config.yaml` → `kimi_api.api_key`
- **支持的文本文件扩展名**: `.txt`, `.md`, `.py`, `.js`, `.ts`, `.java`, `.cpp`, `.c`, `.h`, `.html`, `.css`, `.json`, `.xml`, `.yaml`, `.yml`, `.sh`, `.bat`, `.go`, `.rs`, `.php`, `.rb`, `.swift`, `.kt`, `.scala`, `.sql`, `.log`, `.conf`, `.config`, `.ini`, `.csv`, `.tsv`

## 支持的操作类型

- **translate**: 翻译（默认翻译为中文）
- **explain**: 解释
- **summarize**: 总结
- **analyze**: 分析（用于图片和文件）

## 错误处理

所有函数都包含详细的错误处理和调试输出：
- 文件不存在/无法读取
- API Key 未配置
- 文件上传失败
- 文件内容提取失败
- API 调用失败
- 临时文件清理失败（记录警告但不影响主流程）

## 注意事项

1. **已废弃函数**：`read_file_content()` 和 `process_image_data()` 不再使用，应删除
2. **临时文件管理**：图片处理会创建临时文件，需要在成功/失败时清理
3. **文件内容验证**：上传文件后需要验证提取的内容非空
4. **模型选择**：根据内容类型和是否使用文件上传 API 自动选择合适模型
5. **调试输出**：所有关键步骤都有详细的 `print` 调试输出
