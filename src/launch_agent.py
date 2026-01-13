#!/usr/bin/env python3
"""开机自启管理 - LaunchAgent"""

import os
import plistlib
import subprocess
import time
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


def _is_app_running() -> bool:
    """检查应用是否正在运行"""
    try:
        # 方法1: 使用 pgrep 检查多种进程名称模式
        patterns = ['CommondX', 'commondx', 'main.py', 'CommondX.app']
        for pattern in patterns:
            result = subprocess.run(
                ['pgrep', '-f', pattern],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"[DEBUG] [LaunchAgent] 应用运行状态: True (通过模式 '{pattern}' 检测到)")
                return True
        
        # 方法2: 使用 ps 命令检查
        ps_result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if ps_result.returncode == 0:
            ps_output = ps_result.stdout.lower()
            # 检查是否包含应用相关的进程
            keywords = ['commondx', 'main.py']
            for keyword in keywords:
                if keyword in ps_output:
                    # 排除 grep 和 ps 命令本身
                    lines = [line for line in ps_output.split('\n') if keyword in line and 'grep' not in line and 'ps aux' not in line]
                    if lines:
                        print(f"[DEBUG] [LaunchAgent] 应用运行状态: True (通过 ps 检测到关键字 '{keyword}')")
                        return True
        
        print(f"[DEBUG] [LaunchAgent] 应用运行状态: False (未检测到进程)")
        return False
    except Exception as e:
        print(f"[WARN] [LaunchAgent] 检查应用运行状态失败: {e}")
        return False


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
    
    # 检查服务是否已加载（使用正确的服务名称格式）
    try:
        # 修复：直接使用 APP_ID，而不是 gui/uid/APP_ID
        result = subprocess.run(
            ['launchctl', 'list', APP_ID],
            capture_output=True,
            text=True,
            timeout=5
        )
        is_loaded = result.returncode == 0
        
        print(f"[DEBUG] [LaunchAgent] launchctl list 返回码: {result.returncode}")
        if result.stdout:
            print(f"[DEBUG] [LaunchAgent] launchctl list 输出: {result.stdout.strip()}")
        if result.stderr:
            print(f"[DEBUG] [LaunchAgent] launchctl list 错误: {result.stderr.strip()}")
        
        if is_loaded:
            print(f"[DEBUG] [LaunchAgent] ✓ 开机自启已启用（服务已加载）")
        else:
            print(f"[DEBUG] [LaunchAgent] ✗ 开机自启未启用（服务未加载）")
        
        return is_loaded
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
        
        # 步骤 2: 检查应用是否已在运行
        app_already_running = _is_app_running()
        
        # 步骤 3: 创建 plist 配置
        print(f"[DEBUG] [LaunchAgent] 步骤 3: 创建 plist 配置...")
        plist_config = _create_plist()
        
        # 修复新实例问题：如果应用已在运行，临时设置 RunAtLoad: False
        if app_already_running:
            print(f"[DEBUG] [LaunchAgent] 应用已在运行，临时设置 RunAtLoad: False 以避免创建新实例")
            plist_config["RunAtLoad"] = False
        
        # 步骤 4: 如果文件已存在，先卸载
        if PLIST_PATH.exists():
            print(f"[DEBUG] [LaunchAgent] 步骤 4: plist 文件已存在，先卸载旧服务...")
            disable_autostart()
        
        # 步骤 5: 写入 plist 文件（可能是 RunAtLoad: False）
        print(f"[DEBUG] [LaunchAgent] 步骤 5: 写入 plist 文件...")
        plist_data = plistlib.dumps(plist_config)
        PLIST_PATH.write_bytes(plist_data)
        print(f"[DEBUG] [LaunchAgent] ✓ plist 文件已写入: {PLIST_PATH}")
        print(f"[DEBUG] [LaunchAgent] plist 文件大小: {len(plist_data)} 字节")
        print(f"[DEBUG] [LaunchAgent] RunAtLoad: {plist_config.get('RunAtLoad', 'N/A')}")
        
        # 步骤 6: 使用 bootstrap 命令加载服务
        print(f"[DEBUG] [LaunchAgent] 步骤 6: 使用 launchctl bootstrap 加载服务...")
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
            
            # 修复新实例问题：无论检测结果如何，bootstrap 后都检查并停止 LaunchAgent 启动的进程
            # 等待一小段时间，让 LaunchAgent 启动的进程开始运行
            time.sleep(0.5)
            
            # 检查当前进程数量
            pgrep_result = subprocess.run(
                ['pgrep', '-f', 'CommondX|commondx|main.py'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            pids = []
            if pgrep_result.returncode == 0:
                pids = [pid for pid in pgrep_result.stdout.strip().split('\n') if pid.strip()]
                
                if len(pids) > 1:
                    print(f"[DEBUG] [LaunchAgent] 检测到 {len(pids)} 个进程，停止 LaunchAgent 启动的进程...")
                    # 停止 LaunchAgent 服务（这会停止它启动的进程，但保留 plist 文件）
                    bootout_result = subprocess.run(
                        ['launchctl', 'bootout', f'gui/{uid}/{APP_ID}'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    # 重新 bootstrap（这次不会立即启动，因为 RunAtLoad 的行为）
                    # 但我们需要确保 plist 中的 RunAtLoad 是 True（这样下次登录时会启动）
                    time.sleep(0.2)
                    rebootstrap_result = subprocess.run(
                        ['launchctl', 'bootstrap', domain, str(PLIST_PATH)],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if rebootstrap_result.returncode == 0:
                        # 立即再次 bootout（保留注册，但不运行）
                        time.sleep(0.2)
                        subprocess.run(
                            ['launchctl', 'bootout', f'gui/{uid}/{APP_ID}'],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        # 最后再次 bootstrap（确保服务已注册，但这次会启动，所以立即停止）
                        time.sleep(0.1)
                        final_bootstrap = subprocess.run(
                            ['launchctl', 'bootstrap', domain, str(PLIST_PATH)],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        if final_bootstrap.returncode == 0:
                            time.sleep(0.2)
                            # 立即停止
                            subprocess.run(
                                ['launchctl', 'bootout', f'gui/{uid}/{APP_ID}'],
                                capture_output=True,
                                text=True,
                                timeout=10
                            )
                            print(f"[DEBUG] [LaunchAgent] ⚠ 已停止 LaunchAgent 启动的实例，保留开机自启设置")
            
            # 如果之前设置了 RunAtLoad: False，现在改回 True（这样下次登录时会自动启动）
            if app_already_running or (len(pids) > 1):
                print(f"[DEBUG] [LaunchAgent] 恢复 RunAtLoad: True（下次登录时会自动启动）...")
                plist_config["RunAtLoad"] = True
                plist_data = plistlib.dumps(plist_config)
                PLIST_PATH.write_bytes(plist_data)
                print(f"[DEBUG] [LaunchAgent] ✓ plist 已更新为 RunAtLoad: True")
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
        
        # 步骤 7: 验证服务是否已加载
        print(f"[DEBUG] [LaunchAgent] 步骤 7: 验证服务状态...")
        
        if is_autostart_enabled():
            print(f"[DEBUG] [LaunchAgent] ========== ✓ 开机自启启用成功 ==========")
            return True
        else:
            print(f"[ERROR] [LaunchAgent] ========== ✗ 开机自启启用失败（服务未加载）==========")
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
        # 修复：bootout 也需要使用正确的格式
        # 尝试两种格式：gui/uid/APP_ID 和 APP_ID
        domain_formats = [f"gui/{uid}/{APP_ID}", APP_ID]
        
        # 步骤 1: 使用 bootout 命令卸载服务
        print(f"[DEBUG] [LaunchAgent] 步骤 1: 使用 launchctl bootout 卸载服务...")
        bootout_success = False
        for domain in domain_formats:
            print(f"[DEBUG] [LaunchAgent] 尝试格式: launchctl bootout {domain}")
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
            
            if result.returncode == 0:
                print(f"[DEBUG] [LaunchAgent] ✓ 服务卸载成功（使用格式: {domain}）")
                bootout_success = True
                break
            elif "could not find specified service" in result.stderr.lower() or "No such process" in result.stderr:
                print(f"[DEBUG] [LaunchAgent] ⚠ 服务不存在（格式: {domain}），尝试下一个格式")
            else:
                print(f"[WARN] [LaunchAgent] ⚠ bootout 返回非零码（格式: {domain}），尝试下一个格式")
        
        # 即使 bootout 失败（服务可能不存在），也继续删除文件
        if not bootout_success:
            print(f"[DEBUG] [LaunchAgent] ⚠ 所有格式都失败，继续删除文件")
        
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
