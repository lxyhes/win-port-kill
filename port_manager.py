#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端口管理工具 - 可以查询端口占用情况并终止相关进程
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import re
import threading
import psutil
import sys
import os
import json
from pathlib import Path

class PortManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("端口管理工具")
        self.root.geometry("900x700")
        self.root.resizable(True, True)

        # 设置主题色彩
        self.root.configure(bg='#f0f0f0')

        # 设置最小窗口大小
        self.root.minsize(800, 600)

        # 设置图标（如果有的话）
        try:
            if os.path.exists("icon.ico"):
                self.root.iconbitmap("icon.ico")
        except:
            pass

        # 初始化历史记录
        self.history_file = Path("port_history.json")
        self.port_history = self.load_port_history()
        self.max_history = 10  # 最多保存10个历史记录

        # 自定义样式
        self.setup_styles()

        self.setup_ui()

    def setup_styles(self):
        """设置自定义样式"""
        style = ttk.Style()

        # 配置主题
        style.theme_use('clam')

        # 自定义按钮样式
        style.configure('Action.TButton',
                       background='#4CAF50',
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       font=('Microsoft YaHei UI', 9, 'bold'))
        style.map('Action.TButton',
                 background=[('active', '#45a049'),
                           ('pressed', '#3d8b40')])

        style.configure('Danger.TButton',
                       background='#f44336',
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       font=('Microsoft YaHei UI', 9, 'bold'))
        style.map('Danger.TButton',
                 background=[('active', '#da190b'),
                           ('pressed', '#b71c1c')])

        style.configure('Info.TButton',
                       background='#2196F3',
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       font=('Microsoft YaHei UI', 9, 'bold'))
        style.map('Info.TButton',
                 background=[('active', '#0b7dda'),
                           ('pressed', '#0a58ca')])

        style.configure('Warning.TButton',
                       background='#FF9800',
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       font=('Microsoft YaHei UI', 9, 'bold'))
        style.map('Warning.TButton',
                 background=[('active', '#e68900'),
                           ('pressed', '#cc7a00')])

        # 配置输入框样式
        style.configure('Custom.TEntry',
                       fieldbackground='white',
                       borderwidth=1,
                       relief='solid',
                       font=('Microsoft YaHei UI', 10))

        # 配置框架样式
        style.configure('Card.TLabelframe',
                       background='white',
                       relief='solid',
                       borderwidth=1)

        style.configure('Card.TLabelframe.Label',
                       background='white',
                       foreground='#333333',
                       font=('Microsoft YaHei UI', 10, 'bold'))

    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # 标题区域
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 25))

        title_label = tk.Label(title_frame, text="🔌 端口管理工具",
                               font=('Microsoft YaHei UI', 20, 'bold'),
                               fg='#2196F3', bg='#f0f0f0')
        title_label.pack()

        subtitle_label = tk.Label(title_frame, text="查询端口占用 • 管理进程 • 一键终止",
                                 font=('Microsoft YaHei UI', 10),
                                 fg='#666666', bg='#f0f0f0')
        subtitle_label.pack(pady=(5, 0))

        # 操作区域容器
        action_container = ttk.Frame(main_frame)
        action_container.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        action_container.columnconfigure(0, weight=1)
        action_container.columnconfigure(1, weight=1)

        # 端口操作区域
        port_frame = ttk.LabelFrame(action_container, text="🔍 端口操作", padding="15", style='Card.TLabelframe')
        port_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 8))
        port_frame.columnconfigure(1, weight=1)

        # 端口输入区域
        port_input_container = ttk.Frame(port_frame)
        port_input_container.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=8)
        port_input_container.columnconfigure(1, weight=1)

        ttk.Label(port_input_container, text="端口号:", font=('Microsoft YaHei UI', 10)).grid(row=0, column=0, sticky=tk.W, padx=(0, 12))

        # 创建输入框和历史记录下拉框的组合
        self.port_var = tk.StringVar()
        self.port_entry = ttk.Entry(port_input_container, textvariable=self.port_var, width=20, style='Custom.TEntry')
        self.port_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 8))
        self.port_entry.bind('<Return>', lambda e: self.query_port())

        # 历史记录下拉框
        self.port_combo = ttk.Combobox(port_input_container, textvariable=self.port_var, width=10,
                                      values=self.port_history, state='readonly')
        self.port_combo.grid(row=0, column=2, sticky=tk.E)
        self.port_combo.bind('<<ComboboxSelected>>', self.on_history_selected)

        # 历史记录按钮
        self.history_btn = ttk.Button(port_input_container, text="📜", width=3,
                                     command=self.show_history_dialog, style='Info.TButton')
        self.history_btn.grid(row=0, column=3, sticky=tk.E, padx=(5, 0))

        # 端口操作按钮
        port_button_frame = ttk.Frame(port_frame)
        port_button_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        self.query_btn = ttk.Button(port_button_frame, text="🔍 查询端口",
                                   command=self.query_port, style='Action.TButton', width=15)
        self.query_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.kill_btn = ttk.Button(port_button_frame, text="⚠️ 终止进程",
                                  command=self.kill_process, style='Danger.TButton', width=15)
        self.kill_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.refresh_btn = ttk.Button(port_button_frame, text="🔄 刷新列表",
                                     command=self.refresh_all, style='Info.TButton', width=15)
        self.refresh_btn.pack(side=tk.LEFT)

        # PID快速操作区域
        pid_frame = ttk.LabelFrame(action_container, text="⚡ PID快速操作", padding="15", style='Card.TLabelframe')
        pid_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(8, 0))
        pid_frame.columnconfigure(1, weight=1)

        # PID输入
        ttk.Label(pid_frame, text="PID:", font=('Microsoft YaHei UI', 10)).grid(row=0, column=0, sticky=tk.W, padx=(0, 12), pady=8)
        self.pid_entry = ttk.Entry(pid_frame, width=20, style='Custom.TEntry')
        self.pid_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 15), pady=8)

        # PID操作按钮
        pid_button_frame = ttk.Frame(pid_frame)
        pid_button_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        self.extract_pid_btn = ttk.Button(pid_button_frame, text="📋 提取PID",
                                         command=self.extract_pid, style='Info.TButton', width=14)
        self.extract_pid_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.kill_pid_btn = ttk.Button(pid_button_frame, text="🗑️ 快速杀掉",
                                      command=self.kill_by_pid, style='Danger.TButton', width=14)
        self.kill_pid_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.copy_pid_btn = ttk.Button(pid_button_frame, text="📝 复制PID",
                                      command=self.copy_pid, style='Warning.TButton', width=14)
        self.copy_pid_btn.pack(side=tk.LEFT)

        # 显示区域
        display_frame = ttk.LabelFrame(main_frame, text="📊 操作结果", padding="15", style='Card.TLabelframe')
        display_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        display_frame.columnconfigure(0, weight=1)
        display_frame.rowconfigure(0, weight=1)

        # 结果文本框
        self.result_text = scrolledtext.ScrolledText(
            display_frame,
            wrap=tk.WORD,
            height=18,
            font=('Consolas', 9),
            bg='#1e1e1e',
            fg='#d4d4d4',
            insertbackground='#d4d4d4',
            selectbackground='#264f78',
            relief='flat',
            borderwidth=1
        )
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置文本样式
        self.result_text.tag_config("header", font=('Microsoft YaHei UI', 11, 'bold'), foreground='#569cd6')
        self.result_text.tag_config("success", foreground='#4ec9b0')
        self.result_text.tag_config("error", foreground='#f44747')
        self.result_text.tag_config("info", foreground='#9cdcfe')
        self.result_text.tag_config("warning", foreground='#dcdcaa')
        self.result_text.tag_config("pid", background='#264f78', foreground='#ffffff', font=('Consolas', 10, 'bold'))

        # 添加一些帮助文本
        help_text = "💡 提示: 输入端口号查询占用情况，使用PID快速操作区域进行进程管理\n"
        self.result_text.insert(tk.END, help_text, "info")

        # 存储查询到的PID
        self.current_pids = []

        # 状态栏
        status_container = ttk.Frame(main_frame)
        status_container.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(15, 0))
        status_container.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar()
        self.status_var.set("✅ 就绪 - 可以开始操作")

        # 状态标签
        status_label = tk.Label(
            status_container,
            textvariable=self.status_var,
            font=('Microsoft YaHei UI', 9),
            fg='#2196F3',
            bg='#f0f0f0',
            relief='flat',
            pady=8
        )
        status_label.grid(row=0, column=0, sticky=(tk.W, tk.E))

        # 初始化时显示所有端口
        self.refresh_all()

        # 设置焦点
        self.port_entry.focus_set()

        # 绑定回车键快速操作
        self.pid_entry.bind('<Return>', lambda e: self.kill_by_pid())

        # 绑定快捷键
        self.root.bind('<Control-r>', lambda e: self.refresh_all())
        self.root.bind('<F5>', lambda e: self.refresh_all())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        self.root.bind('<F1>', lambda e: self.show_about())

    def log_message(self, message, tag="normal"):
        """在结果框中添加消息"""
        self.result_text.insert(tk.END, message + "\n", tag)
        self.result_text.see(tk.END)
        self.root.update_idletasks()

    def clear_results(self):
        """清空结果"""
        self.result_text.delete(1.0, tk.END)

    def update_status(self, status):
        """更新状态栏"""
        # 添加状态图标
        if "就绪" in status or "完成" in status or "成功" in status:
            icon = "✅"
        elif "正在" in status or "查询" in status or "终止" in status:
            icon = "🔄"
        elif "错误" in status or "失败" in status or "警告" in status:
            icon = "⚠️"
        else:
            icon = "ℹ️"

        self.status_var.set(f"{icon} {status}")
        self.root.update_idletasks()

    def validate_port(self, port_str):
        """验证端口号"""
        try:
            port = int(port_str)
            if 1 <= port <= 65535:
                return port
            else:
                messagebox.showerror("错误", "端口号必须在1-65535之间")
                return None
        except ValueError:
            messagebox.showerror("错误", "请输入有效的端口号")
            return None

    def query_port(self):
        """查询指定端口"""
        port_str = self.port_entry.get().strip()
        if not port_str:
            messagebox.showwarning("警告", "请输入端口号")
            return

        port = self.validate_port(port_str)
        if port is None:
            return

        # 保存到历史记录
        self.add_to_history(port_str)

        # 在新线程中执行查询
        threading.Thread(target=self._query_port_thread, args=(port,), daemon=True).start()

    def _query_port_thread(self, port):
        """在线程中查询端口"""
        self.clear_results()
        self.update_status(f"正在查询端口 {port}...")
        self.log_message(f"🔍 查询端口 {port}", "header")
        self.log_message("=" * 60, "header")

        try:
            # 使用 netstat 查询端口
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, encoding='gbk')
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                found = False
                self.current_pids = []  # 清空当前PID列表

                for line in lines:
                    if f':{port}' in line and ('LISTENING' in line or 'ESTABLISHED' in line):
                        found = True
                        parts = line.split()
                        if len(parts) >= 5:
                            local_address = parts[1]
                            foreign_address = parts[2]
                            state = parts[3]
                            pid = parts[4]

                            # 验证PID是否为数字
                            try:
                                int(pid)  # 验证PID是数字
                                # 存储PID
                                self.current_pids.append(pid)
                            except ValueError:
                                # 如果PID不是数字，跳过这条记录
                                continue

                            self.log_message(f"📍 本地地址: {local_address}", "info")
                            self.log_message(f"🌐 远程地址: {foreign_address}")
                            self.log_message(f"📊 连接状态: {state}")
                            self.log_message(f"🆔 进程PID: ", "info")
                            self.result_text.insert(tk.END, f"{pid}\n", "pid")

                            # 获取进程信息
                            try:
                                process = psutil.Process(int(pid))
                                self.log_message(f"🏷️  进程名称: {process.name()}", "warning")
                                self.log_message(f"📁 进程路径: {process.exe()}")
                                self.log_message(f"💻 命令行: {' '.join(process.cmdline())}")
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                self.log_message("⚠️  无法获取进程详细信息", "error")

                            self.log_message("─" * 60, "info")

                if not found:
                    self.log_message(f"端口 {port} 当前未被占用", "success")
                    self.update_status(f"端口 {port} 未被占用")
                    self.current_pids = []
                else:
                    self.update_status(f"端口 {port} 查询完成 - 找到 {len(self.current_pids)} 个进程")
                    # 自动填入第一个PID
                    if self.current_pids:
                        self.pid_entry.delete(0, tk.END)
                        self.pid_entry.insert(0, self.current_pids[0])
            else:
                self.log_message("查询失败: " + result.stderr, "error")
                self.update_status("查询失败")

        except Exception as e:
            self.log_message(f"查询出错: {str(e)}", "error")
            self.update_status("查询出错")

    def kill_process(self):
        """终止占用端口的进程"""
        port_str = self.port_entry.get().strip()
        if not port_str:
            messagebox.showwarning("警告", "请先查询端口")
            return

        port = self.validate_port(port_str)
        if port is None:
            return

        # 确认对话框
        if not messagebox.askyesno("确认", f"确定要终止占用端口 {port} 的进程吗？\n\n注意：这可能会导致相关应用程序异常退出！"):
            return

        # 在新线程中执行终止操作
        threading.Thread(target=self._kill_process_thread, args=(port,), daemon=True).start()

    def _kill_process_thread(self, port):
        """在线程中终止进程"""
        self.clear_results()
        self.update_status(f"正在终止占用端口 {port} 的进程...")
        self.log_message(f"=== 终止端口 {port} 进程 ===", "header")

        try:
            # 使用 netstat 查找PID
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, encoding='gbk')
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                pids = set()

                for line in lines:
                    if f':{port}' in line and ('LISTENING' in line or 'ESTABLISHED' in line):
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[4]
                            # 验证PID是否为数字
                            try:
                                int(pid)  # 验证PID是数字
                                pids.add(pid)
                            except ValueError:
                                # 如果PID不是数字，跳过这条记录
                                continue

                if not pids:
                    self.log_message(f"端口 {port} 当前未被占用", "info")
                    self.update_status(f"端口 {port} 未被占用")
                    return

                # 终止所有相关进程
                for pid in pids:
                    try:
                        process = psutil.Process(int(pid))
                        process_name = process.name()
                        self.log_message(f"正在终止进程: {process_name} (PID: {pid})")

                        # 尝试正常终止
                        process.terminate()

                        # 等待进程结束
                        try:
                            process.wait(timeout=5)
                            self.log_message(f"进程 {process_name} (PID: {pid}) 已成功终止", "success")
                        except psutil.TimeoutExpired:
                            # 强制终止
                            self.log_message(f"正常终止失败，正在强制终止进程 {process_name} (PID: {pid})", "info")
                            process.kill()
                            process.wait(timeout=3)
                            self.log_message(f"进程 {process_name} (PID: {pid}) 已强制终止", "success")

                    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        self.log_message(f"无法终止进程 PID {pid}: {str(e)}", "error")
                    except Exception as e:
                        self.log_message(f"终止进程 PID {pid} 时出错: {str(e)}", "error")

                # 验证端口是否已释放
                self.log_message("\n正在验证端口是否已释放...", "info")
                import time
                time.sleep(1)

                result2 = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, encoding='gbk')
                if result2.returncode == 0:
                    lines2 = result2.stdout.split('\n')
                    still_occupied = any(f':{port}' in line and ('LISTENING' in line or 'ESTABLISHED' in line)
                                        for line in lines2)

                    if still_occupied:
                        self.log_message(f"警告: 端口 {port} 仍被占用，可能需要重启相关服务", "error")
                    else:
                        self.log_message(f"端口 {port} 已成功释放", "success")

                self.update_status("终止操作完成")
            else:
                self.log_message("查询端口失败: " + result.stderr, "error")
                self.update_status("终止操作失败")

        except Exception as e:
            self.log_message(f"终止进程时出错: {str(e)}", "error")
            self.update_status("终止操作出错")

    def refresh_all(self):
        """刷新显示所有监听端口"""
        threading.Thread(target=self._refresh_all_thread, daemon=True).start()

    def _refresh_all_thread(self):
        """在线程中刷新所有端口"""
        self.clear_results()
        self.update_status("正在获取所有端口信息...")
        self.log_message("🔄 所有监听端口列表", "header")
        self.log_message("=" * 60, "header")

        try:
            # 使用 netstat 获取所有监听端口
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, encoding='gbk')
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                listening_ports = []

                for line in lines:
                    # 跳过空行和标题行
                    if not line.strip() or line.startswith('TCP') or line.startswith('UDP'):
                        continue

                    if 'LISTENING' in line:
                        parts = line.split()
                        # netstat格式：协议 本地地址 外部地址 状态 PID
                        # 确保有足够的字段
                        if len(parts) >= 5:
                            local_address = parts[1]
                            # 确保PID字段存在且不为空
                            if len(parts) >= 5 and parts[4]:
                                pid = parts[4]
                            else:
                                continue

                            # 提取端口号
                            if ':' in local_address:
                                port = local_address.split(':')[-1]
                                # 验证端口号是数字且在有效范围内
                                try:
                                    port_num = int(port)
                                    if 1 <= port_num <= 65535:
                                        listening_ports.append((port, local_address, pid))
                                except ValueError:
                                    # 如果端口不是数字，跳过这一行
                                    continue

                if listening_ports:
                    # 按端口号排序，使用更安全的排序方式
                    listening_ports.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 999999)

                    self.log_message(f"📊 共找到 {len(listening_ports)} 个监听端口:\n", "info")

                    for port, address, pid in listening_ports:
                        try:
                            process = psutil.Process(int(pid))
                            process_name = process.name()
                            self.log_message(f"🔌 端口 {port:<6} | 🆔 PID {pid:<8} | 🏷️  {process_name}", "info")
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            self.log_message(f"🔌 端口 {port:<6} | 🆔 PID {pid:<8} | ❌ [无法获取进程名]", "error")
                else:
                    self.log_message("当前没有监听的端口", "success")

                self.update_status(f"刷新完成 - 共 {len(listening_ports)} 个监听端口")
            else:
                self.log_message("获取端口信息失败: " + result.stderr, "error")
                self.update_status("刷新失败")

        except Exception as e:
            self.log_message(f"刷新时出错: {str(e)}", "error")
            self.update_status("刷新出错")

    def extract_pid(self):
        """提取当前查询到的PID"""
        if self.current_pids:
            if len(self.current_pids) == 1:
                # 只有一个PID，直接填入
                self.pid_entry.delete(0, tk.END)
                self.pid_entry.insert(0, self.current_pids[0])
                self.update_status(f"已提取PID: {self.current_pids[0]}")
            else:
                # 多个PID，创建选择对话框
                self.show_pid_selection_dialog()
        else:
            messagebox.showwarning("警告", "请先查询端口获取PID")
            self.update_status("没有可提取的PID")

    def show_pid_selection_dialog(self):
        """显示PID选择对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("选择PID")
        dialog.geometry("400x300")
        dialog.resizable(True, True)

        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f'+{x}+{y}')

        # 说明标签
        ttk.Label(dialog, text="找到多个PID，请选择要操作的目标:", padding="10").pack()

        # PID列表框架
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # 创建Listbox和Scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        pid_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        pid_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=pid_listbox.yview)

        # 添加PID信息
        for i, pid in enumerate(self.current_pids):
            try:
                process = psutil.Process(int(pid))
                process_name = process.name()
                pid_listbox.insert(tk.END, f"PID {pid} - {process_name}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pid_listbox.insert(tk.END, f"PID {pid} - [未知进程]")

        # 按钮框架
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)

        def select_pid():
            selection = pid_listbox.curselection()
            if selection:
                index = selection[0]
                selected_pid = self.current_pids[index]
                self.pid_entry.delete(0, tk.END)
                self.pid_entry.insert(0, selected_pid)
                self.update_status(f"已选择PID: {selected_pid}")
                dialog.destroy()

        ttk.Button(button_frame, text="选择", command=select_pid).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def kill_by_pid(self):
        """根据PID直接杀掉进程"""
        pid_str = self.pid_entry.get().strip()
        if not pid_str:
            messagebox.showwarning("警告", "请输入PID")
            return

        try:
            pid = int(pid_str)
        except ValueError:
            messagebox.showerror("错误", "请输入有效的PID数字")
            return

        # 确认对话框
        try:
            process = psutil.Process(pid)
            process_name = process.name()
            confirm_msg = f"确定要终止进程 {process_name} (PID: {pid}) 吗？\n\n注意：这可能会导致相关应用程序异常退出！"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            confirm_msg = f"确定要终止进程 PID: {pid} 吗？\n\n注意：无法获取进程详细信息！"

        if not messagebox.askyesno("确认", confirm_msg):
            return

        # 在新线程中执行终止操作
        threading.Thread(target=self._kill_by_pid_thread, args=(pid,), daemon=True).start()

    def _kill_by_pid_thread(self, pid):
        """在线程中根据PID终止进程"""
        self.update_status(f"正在终止进程 PID: {pid}...")
        self.log_message(f"=== 终止进程 PID: {pid} ===", "header")

        try:
            process = psutil.Process(pid)
            process_name = process.name()
            self.log_message(f"目标进程: {process_name} (PID: {pid})")

            # 尝试正常终止
            self.log_message("正在尝试正常终止...", "info")
            process.terminate()

            # 等待进程结束
            try:
                process.wait(timeout=5)
                self.log_message(f"进程 {process_name} (PID: {pid}) 已成功终止", "success")
                self.update_status(f"进程 PID: {pid} 已终止")
            except psutil.TimeoutExpired:
                # 强制终止
                self.log_message("正常终止失败，正在强制终止...", "info")
                process.kill()
                process.wait(timeout=3)
                self.log_message(f"进程 {process_name} (PID: {pid}) 已强制终止", "success")
                self.update_status(f"进程 PID: {pid} 已强制终止")

            # 验证进程是否已终止
            try:
                psutil.Process(pid)
                self.log_message("警告: 进程可能仍在运行", "error")
            except psutil.NoSuchProcess:
                self.log_message("验证: 进程已成功终止", "success")

        except psutil.NoSuchProcess:
            self.log_message(f"进程 PID: {pid} 不存在", "error")
            self.update_status("进程不存在")
        except psutil.AccessDenied:
            self.log_message(f"权限不足，无法终止进程 PID: {pid}", "error")
            self.update_status("权限不足")
        except Exception as e:
            self.log_message(f"终止进程时出错: {str(e)}", "error")
            self.update_status("终止出错")

    def copy_pid(self):
        """复制当前PID到剪贴板"""
        pid_str = self.pid_entry.get().strip()
        if not pid_str:
            messagebox.showwarning("警告", "没有可复制的PID")
            return

        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(pid_str)
            self.update_status(f"PID {pid_str} 已复制到剪贴板")

            # 显示成功提示
            self.log_message(f"PID {pid_str} 已复制到剪贴板", "success")
        except Exception as e:
            messagebox.showerror("错误", f"复制失败: {str(e)}")
            self.update_status("复制失败")

    def show_about(self):
        """显示关于对话框"""
        about_text = """🔌 端口管理工具 v1.1

一个现代化的端口管理和进程监控工具

主要功能:
• 🔍 端口占用查询
• ⚡ PID快速操作
• 🔄 进程管理
• 📊 实时监控
• 📜 端口历史记录

快捷键:
• F5 / Ctrl+R - 刷新端口列表
• Ctrl+Q - 退出程序
• F1 - 显示关于信息

技术栈:
• Python + Tkinter
• psutil 进程管理

安全提醒:
使用前请了解相关进程的作用
避免终止系统关键进程"""

        messagebox.showinfo("关于端口管理工具", about_text)

    def load_port_history(self):
        """加载端口历史记录"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"加载历史记录失败: {e}")
            return []

    def save_port_history(self):
        """保存端口历史记录"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.port_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史记录失败: {e}")

    def add_to_history(self, port):
        """添加端口到历史记录"""
        # 移除重复项
        if port in self.port_history:
            self.port_history.remove(port)

        # 添加到开头
        self.port_history.insert(0, port)

        # 限制历史记录数量
        if len(self.port_history) > self.max_history:
            self.port_history = self.port_history[:self.max_history]

        # 更新下拉框
        self.port_combo['values'] = self.port_history

        # 保存到文件
        self.save_port_history()

    def on_history_selected(self, event):
        """历史记录选择事件"""
        selected_port = self.port_var.get().strip()
        if selected_port:
            self.update_status(f"已选择历史端口: {selected_port}")
            # 自动查询选中的端口
            self.query_port()

    def show_history_dialog(self):
        """显示历史记录管理对话框"""
        if not self.port_history:
            messagebox.showinfo("历史记录", "当前没有历史记录")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("端口历史记录")
        dialog.geometry("400x500")
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()

        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f'+{x}+{y}')

        # 主框架
        main_frame = ttk.Frame(dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text="📜 端口历史记录",
                               font=('Microsoft YaHei UI', 12, 'bold'))
        title_label.pack(pady=(0, 15))

        # 历史记录列表框架
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # 创建Listbox和Scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        history_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                     font=('Consolas', 10))
        history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=history_listbox.yview)

        # 添加历史记录
        for i, port in enumerate(self.port_history):
            history_listbox.insert(tk.END, f"端口 {port}")
            history_listbox.itemconfig(i, fg='#2196F3')

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        def select_port():
            selection = history_listbox.curselection()
            if selection:
                index = selection[0]
                selected_port = self.port_history[index]
                self.port_var.set(selected_port)
                self.update_status(f"已选择历史端口: {selected_port}")
                dialog.destroy()
                # 自动查询选中的端口
                self.query_port()

        def delete_port():
            selection = history_listbox.curselection()
            if selection:
                index = selection[0]
                port_to_delete = self.port_history[index]

                if messagebox.askyesno("确认删除", f"确定要删除端口 {port_to_delete} 的历史记录吗？"):
                    self.port_history.pop(index)
                    history_listbox.delete(index)
                    self.port_combo['values'] = self.port_history
                    self.save_port_history()
                    self.update_status(f"已删除历史记录: {port_to_delete}")

        def clear_all():
            if messagebox.askyesno("确认清空", "确定要清空所有历史记录吗？"):
                self.port_history.clear()
                history_listbox.delete(0, tk.END)
                self.port_combo['values'] = self.port_history
                self.save_port_history()
                self.update_status("已清空所有历史记录")

        def close_dialog():
            dialog.destroy()

        # 按钮布局
        ttk.Button(button_frame, text="📋 选择并查询", command=select_port,
                  style='Action.TButton', width=15).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="🗑️ 删除选中", command=delete_port,
                  style='Danger.TButton', width=15).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="🧹 清空全部", command=clear_all,
                  style='Warning.TButton', width=15).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="❌ 关闭", command=close_dialog,
                  width=10).pack(side=tk.RIGHT)

        # 双击事件
        history_listbox.bind('<Double-Button-1>', lambda e: select_port())

def main():
    """主函数"""
    root = tk.Tk()
    app = PortManagerGUI(root)

    # 居中显示窗口
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    root.mainloop()

if __name__ == "__main__":
    main()