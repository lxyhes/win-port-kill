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

class PortManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("端口管理工具")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # 设置图标（如果有的话）
        try:
            if os.path.exists("icon.ico"):
                self.root.iconbitmap("icon.ico")
        except:
            pass

        self.setup_ui()

    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # 标题
        title_label = ttk.Label(main_frame, text="端口管理工具", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20))

        # 输入区域
        input_frame = ttk.LabelFrame(main_frame, text="端口操作", padding="10")
        input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)

        # 端口输入
        ttk.Label(input_frame, text="端口号:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.port_entry = ttk.Entry(input_frame, width=20)
        self.port_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.port_entry.bind('<Return>', lambda e: self.query_port())

        # 按钮区域
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=0, column=2, sticky=(tk.W, tk.E))

        self.query_btn = ttk.Button(button_frame, text="查询端口", command=self.query_port)
        self.query_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.kill_btn = ttk.Button(button_frame, text="终止进程", command=self.kill_process)
        self.kill_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.refresh_btn = ttk.Button(button_frame, text="刷新", command=self.refresh_all)
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 5))

        # 显示区域
        display_frame = ttk.LabelFrame(main_frame, text="结果显示", padding="10")
        display_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        display_frame.columnconfigure(0, weight=1)
        display_frame.rowconfigure(0, weight=1)

        # 结果文本框
        self.result_text = scrolledtext.ScrolledText(display_frame, wrap=tk.WORD, height=20)
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置文本样式
        self.result_text.tag_config("header", font=("Arial", 10, "bold"))
        self.result_text.tag_config("success", foreground="green")
        self.result_text.tag_config("error", foreground="red")
        self.result_text.tag_config("info", foreground="blue")
        self.result_text.tag_config("pid", background="yellow", foreground="black")

        # PID操作区域
        pid_frame = ttk.LabelFrame(main_frame, text="PID快速操作", padding="10")
        pid_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        pid_frame.columnconfigure(1, weight=1)

        # PID输入和提取
        ttk.Label(pid_frame, text="PID:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.pid_entry = ttk.Entry(pid_frame, width=15)
        self.pid_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))

        # PID操作按钮
        pid_button_frame = ttk.Frame(pid_frame)
        pid_button_frame.grid(row=0, column=2, sticky=(tk.W, tk.E))

        self.extract_pid_btn = ttk.Button(pid_button_frame, text="提取PID", command=self.extract_pid)
        self.extract_pid_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.kill_pid_btn = ttk.Button(pid_button_frame, text="快速杀掉", command=self.kill_by_pid)
        self.kill_pid_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.copy_pid_btn = ttk.Button(pid_button_frame, text="复制PID", command=self.copy_pid)
        self.copy_pid_btn.pack(side=tk.LEFT, padx=(0, 5))

        # 存储查询到的PID
        self.current_pids = []

        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        # 初始化时显示所有端口
        self.refresh_all()

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
        self.status_var.set(status)
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

        # 在新线程中执行查询
        threading.Thread(target=self._query_port_thread, args=(port,), daemon=True).start()

    def _query_port_thread(self, port):
        """在线程中查询端口"""
        self.clear_results()
        self.update_status(f"正在查询端口 {port}...")
        self.log_message(f"=== 查询端口 {port} ===", "header")

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

                            # 存储PID
                            self.current_pids.append(pid)

                            self.log_message(f"本地地址: {local_address}", "info")
                            self.log_message(f"远程地址: {foreign_address}")
                            self.log_message(f"状态: {state}")
                            self.log_message(f"PID: ", "info")
                            self.result_text.insert(tk.END, f"{pid}\n", "pid")

                            # 获取进程信息
                            try:
                                process = psutil.Process(int(pid))
                                self.log_message(f"进程名称: {process.name()}")
                                self.log_message(f"进程路径: {process.exe()}")
                                self.log_message(f"命令行: {' '.join(process.cmdline())}")
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                self.log_message("无法获取进程详细信息", "error")

                            self.log_message("-" * 50)

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
                            pids.add(parts[4])

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
        self.log_message("=== 所有监听端口 ===", "header")

        try:
            # 使用 netstat 获取所有监听端口
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, encoding='gbk')
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                listening_ports = []

                for line in lines:
                    if 'LISTENING' in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            local_address = parts[1]
                            pid = parts[3]

                            # 提取端口号
                            if ':' in local_address:
                                port = local_address.split(':')[-1]
                                listening_ports.append((port, local_address, pid))

                if listening_ports:
                    # 按端口号排序
                    listening_ports.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 0)

                    self.log_message(f"共找到 {len(listening_ports)} 个监听端口:\n", "info")

                    for port, address, pid in listening_ports:
                        try:
                            process = psutil.Process(int(pid))
                            process_name = process.name()
                            self.log_message(f"端口 {port:<6} | PID {pid:<8} | {process_name}", "info")
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            self.log_message(f"端口 {port:<6} | PID {pid:<8} | [无法获取进程名]", "error")
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