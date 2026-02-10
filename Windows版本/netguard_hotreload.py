#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NetGuard 热加载启动器
支持代码修改后自动重启
"""

import sys
import os
import time
import subprocess
from pathlib import Path
from datetime import datetime

# 要监视的文件
WATCH_FILES = [
    'port_manager.py',
    'netguard_logo.py',
]

# 文件修改时间记录
file_mtimes = {}


def get_file_mtime(filepath):
    """获取文件修改时间"""
    try:
        return os.path.getmtime(filepath)
    except:
        return None


def check_files_changed():
    """检查文件是否发生变化"""
    global file_mtimes
    changed = False
    
    for filename in WATCH_FILES:
        filepath = Path(filename)
        if not filepath.exists():
            continue
            
        current_mtime = get_file_mtime(filepath)
        if current_mtime is None:
            continue
            
        if filename not in file_mtimes:
            file_mtimes[filename] = current_mtime
        elif file_mtimes[filename] != current_mtime:
            file_mtimes[filename] = current_mtime
            changed = True
            print(f"[热加载] 检测到文件变化: {filename}")
    
    return changed


def run_app():
    """运行主程序"""
    print("=" * 50)
    print("🛡️ NetGuard 端口管理工具")
    print("热加载模式 - 修改代码后自动重启")
    print("=" * 50)
    print()
    
    # 初始化文件时间
    for filename in WATCH_FILES:
        filepath = Path(filename)
        if filepath.exists():
            file_mtimes[filename] = get_file_mtime(filepath)
    
    while True:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 启动 NetGuard...")
        
        # 启动程序
        process = subprocess.Popen(
            [sys.executable, 'port_manager.py'],
            cwd=os.getcwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        # 监视输出和文件变化
        while process.poll() is None:
            # 检查文件变化
            if check_files_changed():
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 文件变化，正在重启...")
                process.terminate()
                try:
                    process.wait(timeout=2)
                except:
                    process.kill()
                time.sleep(0.5)
                break
            
            # 读取输出
            try:
                line = process.stdout.readline()
                if line:
                    print(line.rstrip())
            except:
                pass
                
            time.sleep(0.1)
        
        # 进程已结束，读取剩余输出确保显示完整错误信息
        try:
            remaining_output = process.stdout.read()
            if remaining_output:
                print(remaining_output.rstrip())
        except:
            pass

        # 如果程序正常退出，询问是否重启
        if process.poll() is not None and not check_files_changed():
            print()
            print("程序已退出")
            choice = input("是否重新启动? (y/n): ").strip().lower()
            if choice != 'y':
                break
        
        time.sleep(0.5)
    
    print("感谢使用 NetGuard!")


if __name__ == '__main__':
    try:
        run_app()
    except KeyboardInterrupt:
        print("\n已退出")
        sys.exit(0)
