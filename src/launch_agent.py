#!/usr/bin/env python3
"""开机自启管理 - LaunchAgent"""

import os
import plistlib
import subprocess
from pathlib import Path
from cedar.utils import print

APP_ID = "com.liuns.commondx"
PLIST_PATH = Path.home() / f"Library/LaunchAgents/{APP_ID}.plist"
LOG_DIR = Path.home() / "Library/Logs"

# 应用路径候选
APP_PATHS = [
    Path("/Applications/CommondX.app/Contents/MacOS/CommondX"),
    Path.home() / "Applications/CommondX.app/Contents/MacOS/CommondX",
    Path(__file__).parent.parent.parent / "main.py",  # 开发模式
]


def _get_user_id() -> int:
    """获取当前用户 ID"""
    try:
        uid = os.getuid()
        print(f"[DEBUG] [LaunchAgent] 当前用户 ID: {uid}")
        return uid
    except Exception as e:
        print(f"[ERROR] [LaunchAgent] 获取用户 ID 失败: {e}")
        # 尝试从环境变量获取
        uid_str = os.getenv("UID", "501")
        try:
            uid = int(uid_str)
            print(f"[DEBUG] [LaunchAgent] 从环境变量获取用户 ID: {uid}")
            return uid
        except ValueError:
            print(f"[WARN] [LaunchAgent] 无法解析用户 ID，使用默认值 501")
            return 501


def _get_app_path() -> str:
    """获取应用路径"""
    print(f"[DEBUG] [LaunchAgent] 开始检测应用路径...")
    print(f"[DEBUG] [LaunchAgent] 候选路径数量: {len(APP_PATHS)}")
    
    for idx, p in enumerate(APP_PATHS):
        print(f"[DEBUG] [LaunchAgent] 检查路径 {idx+1}/{len(APP_PATHS)}: {p}")
        if p.exists():
            print(f"[DEBUG] [LaunchAgent] ✓ 找到应用路径: {p}")
            return str(p)
        else:
            print(f"[DEBUG] [LaunchAgent] ✗ 路径不存在: {p}")
    
    # 如果都没找到，返回最后一个作为默认值
    default_path = str(APP_PATHS[-1])
    print(f"[WARN] [LaunchAgent] 所有路径都不存在，使用默认路径: {default_path}")
    return default_path


def _create_plist() -> dict:
    """创建 plist 配置"""
    print(f"[DEBUG] [LaunchAgent] 开始创建 plist 配置...")
    app = _get_app_path()
    print(f"[DEBUG] [LaunchAgent] 应用路径: {app}")
    
    # 判断是否需要使用 python3 运行
    if app.endswith(".py"):
        args = ["/usr/bin/python3", app]
        print(f"[DEBUG] [LaunchAgent] 使用 Python 运行脚本")
    else:
        args = [app]
        print(f"[DEBUG] [LaunchAgent] 直接运行可执行文件")
    
    plist_config = {
        "Label": APP_ID,
        "ProgramArguments": args,
        "RunAtLoad": True,
        "KeepAlive": False,
        "StandardOutPath": str(LOG_DIR / "CommondX.log"),
        "StandardErrorPath": str(LOG_DIR / "CommondX.error.log"),
    }
    
    print(f"[DEBUG] [LaunchAgent] plist 配置内容:")
    print(f"[DEBUG] [LaunchAgent]   Label: {plist_config['Label']}")
    print(f"[DEBUG] [LaunchAgent]   ProgramArguments: {plist_config['ProgramArguments']}")
    print(f"[DEBUG] [LaunchAgent]   RunAtLoad: {plist_config['RunAtLoad']}")
    print(f"[DEBUG] [LaunchAgent]   KeepAlive: {plist_config['KeepAlive']}")
    print(f"[DEBUG] [LaunchAgent]   StandardOutPath: {plist_config['StandardOutPath']}")
    print(f"[DEBUG] [LaunchAgent]   StandardErrorPath: {plist_config['StandardErrorPath']}")
    
    return plist_config


def is_autostart_enabled() -> bool:
    """检查是否已开启"""
    print(f"[DEBUG] [LaunchAgent] 检查开机自启状态...")
    print(f"[DEBUG] [LaunchAgent] plist 文件路径: {PLIST_PATH}")
    
    # 检查 plist 文件是否存在
    file_exists = PLIST_PATH.exists()
    print(f"[DEBUG] [LaunchAgent] plist 文件存在: {file_exists}")
    
    if not file_exists:
        print(f"[DEBUG] [LaunchAgent] ✗ 开机自启未启用（plist 文件不存在）")
        return False
    
    # 检查服务是否真正运行
    try:
        uid = _get_user_id()
        result = subprocess.run(
            ['launchctl', 'list', f'gui/{uid}/{APP_ID}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        is_running = result.returncode == 0
        print(f"[DEBUG] [LaunchAgent] launchctl list 返回码: {result.returncode}")
        if result.stdout:
            print(f"[DEBUG] [LaunchAgent] launchctl list 输出: {result.stdout.strip()}")
        if result.stderr:
            print(f"[DEBUG] [LaunchAgent] launchctl list 错误: {result.stderr.strip()}")
        
        if is_running:
            print(f"[DEBUG] [LaunchAgent] ✓ 开机自启已启用（服务正在运行）")
        else:
            print(f"[DEBUG] [LaunchAgent] ✗ 开机自启未启用（服务未运行）")
        
        return is_running
    except Exception as e:
        print(f"[ERROR] [LaunchAgent] 检查服务状态失败: {e}")
        # 如果检查失败，至少返回文件是否存在
        print(f"[DEBUG] [LaunchAgent] 回退到文件存在检查: {file_exists}")
        return file_exists


def enable_autostart() -> bool:
    """启用开机自启"""
    print(f"[DEBUG] [LaunchAgent] ========== 开始启用开机自启 ==========")
    
    try:
        # 步骤 1: 确保目录存在
        print(f"[DEBUG] [LaunchAgent] 步骤 1: 创建 LaunchAgents 目录...")
        PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        print(f"[DEBUG] [LaunchAgent] ✓ 目录已创建: {PLIST_PATH.parent}")
        
        # 步骤 2: 创建 plist 配置
        print(f"[DEBUG] [LaunchAgent] 步骤 2: 创建 plist 配置...")
        plist_config = _create_plist()
        
        # 步骤 3: 如果文件已存在，先卸载
        if PLIST_PATH.exists():
            print(f"[DEBUG] [LaunchAgent] 步骤 3: plist 文件已存在，先卸载旧服务...")
            disable_autostart()
        
        # 步骤 4: 写入 plist 文件
        print(f"[DEBUG] [LaunchAgent] 步骤 4: 写入 plist 文件...")
        plist_data = plistlib.dumps(plist_config)
        PLIST_PATH.write_bytes(plist_data)
        print(f"[DEBUG] [LaunchAgent] ✓ plist 文件已写入: {PLIST_PATH}")
        print(f"[DEBUG] [LaunchAgent] plist 文件大小: {len(plist_data)} 字节")
        
        # 步骤 5: 使用 bootstrap 命令加载服务
        print(f"[DEBUG] [LaunchAgent] 步骤 5: 使用 launchctl bootstrap 加载服务...")
        uid = _get_user_id()
        domain = f"gui/{uid}"
        print(f"[DEBUG] [LaunchAgent] 使用域: {domain}")
        print(f"[DEBUG] [LaunchAgent] 执行命令: launchctl bootstrap {domain} {PLIST_PATH}")
        
        result = subprocess.run(
            ['launchctl', 'bootstrap', domain, str(PLIST_PATH)],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print(f"[DEBUG] [LaunchAgent] launchctl bootstrap 返回码: {result.returncode}")
        if result.stdout:
            print(f"[DEBUG] [LaunchAgent] launchctl bootstrap 输出: {result.stdout.strip()}")
        if result.stderr:
            print(f"[DEBUG] [LaunchAgent] launchctl bootstrap 错误: {result.stderr.strip()}")
        
        if result.returncode == 0:
            print(f"[DEBUG] [LaunchAgent] ✓ 服务加载成功")
        elif "already bootstrapped" in result.stderr.lower():
            print(f"[DEBUG] [LaunchAgent] ⚠ 服务已存在，尝试先卸载...")
            disable_autostart()
            # 重新加载
            result = subprocess.run(
                ['launchctl', 'bootstrap', domain, str(PLIST_PATH)],
                capture_output=True,
                text=True,
                timeout=10
            )
            print(f"[DEBUG] [LaunchAgent] 重新加载返回码: {result.returncode}")
            if result.returncode != 0:
                print(f"[ERROR] [LaunchAgent] ✗ 重新加载失败: {result.stderr}")
                return False
        
        # 步骤 6: 验证服务是否运行
        print(f"[DEBUG] [LaunchAgent] 步骤 6: 验证服务状态...")
        if is_autostart_enabled():
            print(f"[DEBUG] [LaunchAgent] ========== ✓ 开机自启启用成功 ==========")
            return True
        else:
            print(f"[ERROR] [LaunchAgent] ========== ✗ 开机自启启用失败（服务未运行）==========")
            return False
            
    except Exception as e:
        print(f"[ERROR] [LaunchAgent] ========== ✗ 启用开机自启异常 ==========")
        print(f"[ERROR] [LaunchAgent] 异常信息: {e}")
        import traceback
        print(f"[ERROR] [LaunchAgent] 堆栈跟踪:\n{traceback.format_exc()}")
        return False


def disable_autostart() -> bool:
    """禁用开机自启"""
    print(f"[DEBUG] [LaunchAgent] ========== 开始禁用开机自启 ==========")
    
    try:
        uid = _get_user_id()
        domain = f"gui/{uid}/{APP_ID}"
        print(f"[DEBUG] [LaunchAgent] 使用域: {domain}")
        
        # 步骤 1: 使用 bootout 命令卸载服务
        print(f"[DEBUG] [LaunchAgent] 步骤 1: 使用 launchctl bootout 卸载服务...")
        print(f"[DEBUG] [LaunchAgent] 执行命令: launchctl bootout {domain}")
        
        result = subprocess.run(
            ['launchctl', 'bootout', domain],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print(f"[DEBUG] [LaunchAgent] launchctl bootout 返回码: {result.returncode}")
        if result.stdout:
            print(f"[DEBUG] [LaunchAgent] launchctl bootout 输出: {result.stdout.strip()}")
        if result.stderr:
            print(f"[DEBUG] [LaunchAgent] launchctl bootout 错误: {result.stderr.strip()}")
        
        # 即使 bootout 失败（服务可能不存在），也继续删除文件
        if result.returncode == 0:
            print(f"[DEBUG] [LaunchAgent] ✓ 服务卸载成功")
        elif "could not find specified service" in result.stderr.lower() or "No such process" in result.stderr:
            print(f"[DEBUG] [LaunchAgent] ⚠ 服务不存在或已卸载，继续删除文件")
        else:
            print(f"[WARN] [LaunchAgent] ⚠ bootout 返回非零码，但继续删除文件")
        
        # 步骤 2: 删除 plist 文件
        print(f"[DEBUG] [LaunchAgent] 步骤 2: 删除 plist 文件...")
        if PLIST_PATH.exists():
            PLIST_PATH.unlink()
            print(f"[DEBUG] [LaunchAgent] ✓ plist 文件已删除: {PLIST_PATH}")
        else:
            print(f"[DEBUG] [LaunchAgent] plist 文件不存在，无需删除")
        
        # 步骤 3: 验证服务是否已卸载
        print(f"[DEBUG] [LaunchAgent] 步骤 3: 验证服务状态...")
        if not is_autostart_enabled():
            print(f"[DEBUG] [LaunchAgent] ========== ✓ 开机自启禁用成功 ==========")
            return False
        else:
            print(f"[WARN] [LaunchAgent] ========== ⚠ 开机自启禁用完成，但服务可能仍在运行 ==========")
            return False
            
    except Exception as e:
        print(f"[ERROR] [LaunchAgent] ========== ✗ 禁用开机自启异常 ==========")
        print(f"[ERROR] [LaunchAgent] 异常信息: {e}")
        import traceback
        print(f"[ERROR] [LaunchAgent] 堆栈跟踪:\n{traceback.format_exc()}")
        # 即使出错也尝试删除文件
        try:
            if PLIST_PATH.exists():
                PLIST_PATH.unlink()
                print(f"[DEBUG] [LaunchAgent] 已删除 plist 文件")
        except:
            pass
        return False


def toggle_autostart() -> bool:
    """切换开机自启状态"""
    print(f"[DEBUG] [LaunchAgent] ========== 切换开机自启状态 ==========")
    current_status = is_autostart_enabled()
    print(f"[DEBUG] [LaunchAgent] 当前状态: {'已启用' if current_status else '已禁用'}")
    
    if current_status:
        print(f"[DEBUG] [LaunchAgent] 执行禁用操作...")
        result = disable_autostart()
        print(f"[DEBUG] [LaunchAgent] 切换后状态: 已禁用")
        return False
    else:
        print(f"[DEBUG] [LaunchAgent] 执行启用操作...")
        result = enable_autostart()
        print(f"[DEBUG] [LaunchAgent] 切换后状态: {'已启用' if result else '启用失败'}")
        return result
