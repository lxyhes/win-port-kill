#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端口管理工具 - 可以查询端口占用情况并终止相关进程
macOS 风格设计 - 完整优化版
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import subprocess
import threading
import psutil
import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
from functools import lru_cache
from collections import deque

# 常量定义
MAX_HISTORY = 10
MONITOR_INTERVAL = 2
REFRESH_INTERVAL = 1000  # ms
MAX_LOG_LINES = 500

class ToolTip:
    """工具提示类"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind('<Enter>', self.show)
        self.widget.bind('<Leave>', self.hide)

    def show(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")

        label = tk.Label(self.tooltip, text=self.text, 
                        font=('SF Pro Text', 10),
                        bg='#333333', fg='white',
                        relief='solid', borderwidth=0,
                        padx=8, pady=4)
        label.pack()

    def hide(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class PortManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NetGuard - 端口管理工具")
        self.root.geometry("1400x900")
        self.root.resizable(True, True)

        # 设置 macOS 风格背景色
        self.root.configure(bg='#f5f5f7')

        # 设置最小窗口大小
        self.root.minsize(1200, 800)

        # 网络连接监控相关变量
        self.monitoring_active = False
        self.current_connections = []
        self.monitor_thread = None

        # 缓存变量
        self._process_cache = {}
        self._cache_timestamp = 0
        self._cache_ttl = 5  # 缓存有效期5秒

        # 存储所有端口数据用于搜索
        self.all_ports_data = []

        # 设置窗口图标
        try:
            if os.path.exists("icon.ico"):
                self.root.iconbitmap("icon.ico")
        except:
            pass

        # 初始化历史记录
        self.history_file = Path("port_history.json")
        self.port_history = self.load_port_history()

        # 日志缓冲区 - 限制内存使用
        self.log_buffer = deque(maxlen=MAX_LOG_LINES)

        # 自定义样式
        self.setup_styles()

        self.setup_ui()

    def setup_styles(self):
        """设置现代化 UI 风格"""
        style = ttk.Style()
        style.theme_use('clam')

        # === 字体配置 ===
        # Windows 首选 Segoe UI，备选 Microsoft YaHei
        self.fonts = {
            'h1': ('Microsoft YaHei UI', 16, 'bold'),
            'h2': ('Microsoft YaHei UI', 12, 'bold'),
            'body': ('Microsoft YaHei UI', 10),
            'mono': ('Consolas', 10),
            'icon': ('Segoe UI Symbol', 12)
        }

        # === 现代配色方案 (扁平化/柔和) ===
        self.colors = {
            # 品牌色 - 更加稳重的深蓝
            'primary': '#2563EB',        # Modern Blue
            'primary_hover': '#1D4ED8',
            'primary_active': '#1E40AF',
            'primary_light': '#EFF6FF',
            
            # 功能色
            'danger': '#EF4444',         # Soft Red
            'danger_hover': '#DC2626',
            'success': '#10B981',        # Emerald Green
            'success_hover': '#059669',
            'warning': '#F59E0B',        # Amber
            'warning_hover': '#D97706',
            'info': '#3B82F6',           # Sky Blue
            'info_hover': '#2563EB',
            
            # 界面底色
            'bg': '#F3F4F6',             # Cool Gray 100
            'card_bg': '#FFFFFF',
            'sidebar_bg': '#FFFFFF',
            
            # 文本颜色
            'text': '#111827',           # Gray 900
            'text_secondary': '#6B7280', # Gray 500
            'text_tertiary': '#9CA3AF',  # Gray 400
            
            # 边框和分割线
            'border': '#E5E7EB',         # Gray 200
            'divider': '#E5E7EB',
            
            # 终端/日志区域 - 深蓝灰风格 (Dracula/Nord 混合)
            'terminal_bg': '#1E293B',    # Slate 800
            'terminal_fg': '#E2E8F0',    # Slate 200
            'terminal_green': '#34D399',
            'terminal_red': '#F87171',
            'terminal_blue': '#60A5FA',
            'terminal_yellow': '#FBBF24',
            'terminal_purple': '#A78BFA',
            'terminal_cyan': '#22D3EE',
        }

        # === 样式配置 ===
        
        # 通用按钮样式
        for btn_type, color_key in [
            ('Action', 'primary'),
            ('Danger', 'danger'),
            ('Info', 'info'),
            ('Warning', 'warning'),
            ('Success', 'success')
        ]:
            style.configure(f'{btn_type}.TButton',
                           background=self.colors[color_key],
                           foreground='white',
                           borderwidth=0,
                           focuscolor='none',
                           font=self.fonts['body'],
                           relief='flat',
                           padding=(15, 8))
                           
            style.map(f'{btn_type}.TButton',
                     background=[('active', self.colors[f'{color_key}_hover']),
                               ('pressed', self.colors[f'{color_key}'])])

        # 输入框样式
        style.configure('Custom.TEntry',
                       fieldbackground='white',
                       borderwidth=1,
                       relief='solid',
                       font=self.fonts['body'],
                       insertcolor=self.colors['primary'])

        # 下拉框样式
        style.configure('Custom.TCombobox',
                       fieldbackground='white',
                       borderwidth=1,
                       relief='solid',
                       arrowsize=12,
                       font=self.fonts['body'])

    def setup_ui(self):
        """设置UI界面 - 现代化布局"""
        # 主容器
        main_container = tk.Frame(self.root, bg=self.colors['bg'])
        main_container.pack(fill=tk.BOTH, expand=True)

        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=1)

        # === 顶部工具栏 ===
        toolbar = tk.Frame(main_container, bg=self.colors['card_bg'], height=70)
        toolbar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=0, pady=0)
        toolbar.grid_propagate(False)
        
        # 底部阴影模拟 (使用细边框)
        tk.Frame(toolbar, bg=self.colors['border'], height=1).pack(side=tk.BOTTOM, fill=tk.X)

        # Logo 和品牌区域
        brand_frame = tk.Frame(toolbar, bg=self.colors['card_bg'])
        brand_frame.pack(side=tk.LEFT, padx=24, pady=10)

        # 绘制 NetGuard Logo
        self.logo_canvas = tk.Canvas(brand_frame, width=48, height=48,
                                     bg=self.colors['card_bg'], highlightthickness=0)
        self.logo_canvas.pack(side=tk.LEFT)
        self.draw_netguard_logo(self.logo_canvas, 24, 24, 20)

        # 品牌名称和标语
        brand_text_frame = tk.Frame(brand_frame, bg=self.colors['card_bg'])
        brand_text_frame.pack(side=tk.LEFT, padx=(12, 0))

        title_label = tk.Label(brand_text_frame, text="NetGuard",
                               font=self.fonts['h1'],
                               fg=self.colors['primary'], bg=self.colors['card_bg'])
        title_label.pack(anchor=tk.W)

        subtitle_label = tk.Label(brand_text_frame, text="端口管理工具",
                                  font=('Microsoft YaHei UI', 9),
                                  fg=self.colors['text_secondary'], bg=self.colors['card_bg'])
        subtitle_label.pack(anchor=tk.W)

        # 工具栏按钮区域
        toolbar_buttons = tk.Frame(toolbar, bg=self.colors['card_bg'])
        toolbar_buttons.pack(side=tk.RIGHT, padx=24)

        # 导出按钮
        export_btn = tk.Button(toolbar_buttons, text="导出",
                              command=self.export_results,
                              bg=self.colors['card_bg'], fg=self.colors['primary'],
                              font=self.fonts['body'],
                              relief='flat', cursor='hand2',
                              padx=12, pady=4,
                              activebackground=self.colors['bg'],
                              activeforeground=self.colors['primary_active'])
        export_btn.pack(side=tk.RIGHT, padx=(0, 10))
        ToolTip(export_btn, "导出结果到文件")

        # 快捷键提示按钮
        shortcut_btn = tk.Button(toolbar_buttons, text="⌘",
                                command=self.show_shortcuts,
                                bg=self.colors['card_bg'], fg=self.colors['text_secondary'],
                                font=self.fonts['icon'],
                                relief='flat', cursor='hand2',
                                width=3,
                                activebackground=self.colors['bg'])
        shortcut_btn.pack(side=tk.RIGHT, padx=(0, 10))
        ToolTip(shortcut_btn, "显示快捷键")

        # 关于按钮
        about_btn = tk.Button(toolbar_buttons, text="?",
                              command=self.show_about,
                              bg=self.colors['card_bg'], fg=self.colors['text_secondary'],
                              font=self.fonts['icon'],
                              relief='flat', cursor='hand2',
                              width=3)
        about_btn.pack(side=tk.RIGHT)
        ToolTip(about_btn, "关于")

        # === 内容区域 ===
        content_frame = tk.Frame(main_container, bg=self.colors['bg'])
        content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=24, pady=24)
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(2, weight=1)

        # 操作区域容器 - 三列布局
        action_container = tk.Frame(content_frame, bg=self.colors['bg'])
        action_container.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 24))
        action_container.columnconfigure(0, weight=1)
        action_container.columnconfigure(1, weight=1)
        action_container.columnconfigure(2, weight=1)

        # === 端口操作卡片 ===
        port_frame = self.create_mac_card(action_container, "端口操作", 0, 0)

        # 端口输入区域
        port_input_container = tk.Frame(port_frame, bg=self.colors['card_bg'])
        port_input_container.pack(fill=tk.X, pady=(0, 16))

        input_label = tk.Label(port_input_container, text="端口号 / 范围 (如: 8080 或 8000-9000)",
                              font=self.fonts['body'],
                              fg=self.colors['text_secondary'], bg=self.colors['card_bg'])
        input_label.pack(anchor=tk.W, pady=(0, 8))

        # 输入框容器
        input_frame = tk.Frame(port_input_container, bg=self.colors['card_bg'])
        input_frame.pack(fill=tk.X)

        self.port_var = tk.StringVar()
        self.port_entry = tk.Entry(input_frame, textvariable=self.port_var,
                                    font=('Consolas', 12),
                                    bg='white', fg=self.colors['text'],
                                    relief='solid', borderwidth=1,
                                    highlightthickness=2,
                                    highlightcolor=self.colors['primary_light'],
                                    highlightbackground=self.colors['border'])
        self.port_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=4)
        self.port_entry.bind('<Return>', lambda e: self.query_port())

        # 历史记录下拉框
        self.history_var = tk.StringVar()
        self.port_combo = ttk.Combobox(input_frame, textvariable=self.history_var, width=15,
                                      values=self.port_history, state='readonly', style='Custom.TCombobox')
        self.port_combo.pack(side=tk.LEFT, padx=(0, 8), ipady=4)
        self.port_combo.bind('<<ComboboxSelected>>', self.on_history_selected)

        # 历史记录按钮
        self.history_btn = tk.Button(input_frame, text="◷",
                                     command=self.show_history_dialog,
                                     bg=self.colors['bg'], fg=self.colors['text_secondary'],
                                     font=self.fonts['icon'],
                                     relief='flat', cursor='hand2',
                                     activebackground=self.colors['border'],
                                     width=3)
        self.history_btn.pack(side=tk.LEFT)
        ToolTip(self.history_btn, "历史记录")

        # 按钮区域
        button_container = tk.Frame(port_frame, bg=self.colors['card_bg'])
        button_container.pack(fill=tk.X, pady=(4, 0))

        self.query_btn = self.create_mac_button(button_container, "查询", self.query_port, self.colors['primary'])
        self.query_btn.pack(side=tk.LEFT, padx=(0, 12))
        ToolTip(self.query_btn, "查询端口占用情况")

        self.kill_btn = self.create_mac_button(button_container, "终止", self.kill_process, self.colors['danger'])
        self.kill_btn.pack(side=tk.LEFT, padx=(0, 12))
        ToolTip(self.kill_btn, "终止占用端口的进程")

        self.refresh_btn = self.create_mac_button(button_container, "刷新", self.refresh_all, self.colors['success'])
        self.refresh_btn.pack(side=tk.LEFT)
        ToolTip(self.refresh_btn, "刷新所有端口列表")

        # === PID 快速操作卡片 ===
        pid_frame = self.create_mac_card(action_container, "PID 快速操作", 0, 1)

        pid_input_container = tk.Frame(pid_frame, bg=self.colors['card_bg'])
        pid_input_container.pack(fill=tk.X, pady=(0, 16))

        pid_label = tk.Label(pid_input_container, text="进程 ID",
                            font=self.fonts['body'],
                            fg=self.colors['text_secondary'], bg=self.colors['card_bg'])
        pid_label.pack(anchor=tk.W, pady=(0, 8))

        pid_input_frame = tk.Frame(pid_input_container, bg=self.colors['card_bg'])
        pid_input_frame.pack(fill=tk.X)

        self.pid_entry = tk.Entry(pid_input_frame, font=('Consolas', 12),
                                   bg='white', fg=self.colors['text'],
                                   relief='solid', borderwidth=1,
                                   highlightthickness=2,
                                   highlightcolor=self.colors['primary_light'],
                                   highlightbackground=self.colors['border'])
        self.pid_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=4)
        self.pid_entry.bind('<Return>', lambda e: self.kill_by_pid())

        # 复制按钮
        self.copy_pid_btn = tk.Button(pid_input_frame, text=" 复制 ",
                                      command=self.copy_pid,
                                      bg=self.colors['primary'], fg='white',
                                      font=self.fonts['body'],
                                      relief='flat', cursor='hand2',
                                      padx=12, pady=4,
                                      borderwidth=0,
                                      activebackground=self.colors['primary_hover'],
                                      activeforeground='white')
        self.copy_pid_btn.pack(side=tk.LEFT, ipadx=5)
        self.copy_pid_btn.bind('<Enter>', lambda e: self.copy_pid_btn.config(bg=self.colors['primary_hover']))
        self.copy_pid_btn.bind('<Leave>', lambda e: self.copy_pid_btn.config(bg=self.colors['primary']))
        ToolTip(self.copy_pid_btn, "复制PID到剪贴板")

        pid_button_container = tk.Frame(pid_frame, bg=self.colors['card_bg'])
        pid_button_container.pack(fill=tk.X, pady=(4, 0))

        self.extract_pid_btn = self.create_mac_button(pid_button_container, "提取", self.extract_pid, self.colors['info'], width=6)
        self.extract_pid_btn.pack(side=tk.LEFT, padx=(0, 12))
        ToolTip(self.extract_pid_btn, "从查询结果提取PID")

        self.kill_pid_btn = self.create_mac_button(pid_button_container, "杀掉", self.kill_by_pid, self.colors['danger'], width=6)
        self.kill_pid_btn.pack(side=tk.LEFT)
        ToolTip(self.kill_pid_btn, "杀掉指定PID的进程")

        self.details_btn = self.create_mac_button(pid_button_container, "详情", self.show_process_details_dialog, self.colors['warning'], width=6)
        self.details_btn.pack(side=tk.LEFT, padx=(12, 0))
        ToolTip(self.details_btn, "查看进程详细信息")

        # === 网络连接监控卡片 ===
        monitor_frame = self.create_mac_card(action_container, "连接监控", 0, 2)

        monitor_control_container = tk.Frame(monitor_frame, bg=self.colors['card_bg'])
        monitor_control_container.pack(fill=tk.X, pady=(0, 12))

        status_frame = tk.Frame(monitor_control_container, bg=self.colors['card_bg'])
        status_frame.pack(fill=tk.X, pady=(0, 8))

        status_label = tk.Label(status_frame, text="状态",
                              font=self.fonts['body'],
                              fg=self.colors['text_secondary'], bg=self.colors['card_bg'])
        status_label.pack(side=tk.LEFT)

        self.monitor_status_label = tk.Label(status_frame, text="未监控",
                                           font=self.fonts['h2'],
                                           fg=self.colors['text_tertiary'], bg=self.colors['card_bg'])
        self.monitor_status_label.pack(side=tk.RIGHT)

        monitor_button_container = tk.Frame(monitor_frame, bg=self.colors['card_bg'])
        monitor_button_container.pack(fill=tk.X)

        self.start_monitor_btn = self.create_mac_button(monitor_button_container, "开始", self.start_monitoring, self.colors['success'])
        self.start_monitor_btn.pack(side=tk.LEFT, padx=(0, 8))
        ToolTip(self.start_monitor_btn, "开始监控网络连接")

        self.stop_monitor_btn = self.create_mac_button(monitor_button_container, "停止", self.stop_monitoring, self.colors['warning'])
        self.stop_monitor_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.stop_monitor_btn.config(state='disabled')
        ToolTip(self.stop_monitor_btn, "停止监控")

        self.refresh_connections_btn = self.create_mac_button(monitor_button_container, "刷新", self.refresh_connections, self.colors['info'])
        self.refresh_connections_btn.pack(side=tk.LEFT)
        ToolTip(self.refresh_connections_btn, "刷新连接信息")

        # 连接信息显示区域
        connections_frame = tk.Frame(monitor_frame, bg=self.colors['terminal_bg'])
        connections_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        self.connections_text = scrolledtext.ScrolledText(
            connections_frame,
            wrap=tk.WORD,
            height=10,
            font=self.fonts['mono'],
            bg=self.colors['terminal_bg'],
            fg=self.colors['terminal_fg'],
            insertbackground='white',
            selectbackground=self.colors['primary'],
            relief='flat',
            borderwidth=0,
            padx=12,
            pady=12
        )
        self.connections_text.pack(fill=tk.BOTH, expand=True)

        # 配置连接监控文本样式
        self.connections_text.tag_config("header", font=self.fonts['h2'], foreground=self.colors['terminal_blue'])
        self.connections_text.tag_config("success", foreground=self.colors['terminal_green'])
        self.connections_text.tag_config("error", foreground=self.colors['terminal_red'])
        self.connections_text.tag_config("info", foreground=self.colors['terminal_fg'])
        self.connections_text.tag_config("warning", foreground=self.colors['terminal_yellow'])
        self.connections_text.tag_config("highlight", background=self.colors['text_secondary'], foreground='#ffffff')

        # 添加监控说明文本
        monitor_info = "网络连接监控\n" + "─"*40 + "\n"
        monitor_info += "点击「开始」实时查看网络连接\n"
        monitor_info += "支持监控指定端口的连接详情\n"
        monitor_info += "─"*40 + "\n\n"
        self.connections_text.insert(tk.END, monitor_info, "info")

        # === 搜索和结果显示区域 ===
        result_section = tk.Frame(content_frame, bg=self.colors['card_bg'])
        result_section.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        result_section.columnconfigure(0, weight=1)
        result_section.rowconfigure(1, weight=1)
        
        # 给结果区域添加一点阴影效果 (通过边框模拟)
        result_section.config(highlightbackground=self.colors['border'], highlightthickness=1)

        # 搜索栏
        search_frame = tk.Frame(result_section, bg=self.colors['card_bg'], height=60)
        search_frame.pack(fill=tk.X, padx=20, pady=(16, 0))
        search_frame.pack_propagate(False)

        search_label = tk.Label(search_frame, text="搜索:",
                               font=self.fonts['body'],
                               fg=self.colors['text_secondary'], bg=self.colors['card_bg'])
        search_label.pack(side=tk.LEFT, padx=(0, 12))

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                     font=self.fonts['body'],
                                     bg='white', fg=self.colors['text'],
                                     relief='solid', borderwidth=1,
                                     highlightthickness=1,
                                     highlightcolor=self.colors['primary'],
                                     highlightbackground=self.colors['border'])
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12), ipady=4)
        self.search_entry.bind('<KeyRelease>', self.on_search)

        search_btn = tk.Button(search_frame, text="🔍",
                              command=self.filter_ports,
                              bg=self.colors['card_bg'], fg=self.colors['primary'],
                              font=self.fonts['icon'],
                              relief='flat', cursor='hand2',
                              activebackground=self.colors['card_bg'])
        search_btn.pack(side=tk.LEFT)
        ToolTip(search_btn, "搜索端口或进程")

        clear_search_btn = tk.Button(search_frame, text="清除",
                                    command=self.clear_search,
                                    bg=self.colors['card_bg'], fg=self.colors['text_secondary'],
                                    font=self.fonts['body'],
                                    relief='flat', cursor='hand2',
                                    activebackground=self.colors['card_bg'])
        clear_search_btn.pack(side=tk.LEFT, padx=(8, 0))

        # 结果标题栏
        result_header = tk.Frame(result_section, bg=self.colors['card_bg'], height=40)
        result_header.pack(fill=tk.X, padx=20, pady=(8, 0))
        result_header.pack_propagate(False)

        result_title = tk.Label(result_header, text="操作日志",
                               font=self.fonts['h2'],
                               fg=self.colors['text'], bg=self.colors['card_bg'])
        result_title.pack(side=tk.LEFT)

        # 结果文本框 - 现代编辑器风格
        self.result_text = scrolledtext.ScrolledText(
            result_section,
            wrap=tk.WORD,
            height=12,
            font=self.fonts['mono'],
            bg=self.colors['terminal_bg'],
            fg=self.colors['terminal_fg'],
            insertbackground='white',
            selectbackground=self.colors['primary'],
            relief='flat',
            borderwidth=0,
            padx=16,
            pady=16
        )
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # 配置文本样式
        self.result_text.tag_config("header", font=('Consolas', 11, 'bold'), foreground=self.colors['terminal_blue'])
        self.result_text.tag_config("success", foreground=self.colors['terminal_green'])
        self.result_text.tag_config("error", foreground=self.colors['terminal_red'])
        self.result_text.tag_config("info", foreground=self.colors['terminal_fg'])
        self.result_text.tag_config("warning", foreground=self.colors['terminal_yellow'])
        self.result_text.tag_config("pid", background='#334155', foreground=self.colors['terminal_cyan'], font=('Consolas', 10, 'bold'))

        # 添加欢迎文本
        welcome_text = "端口管理工具 v2.0\n" + "─"*60 + "\n"
        welcome_text += "快速开始:\n"
        welcome_text += "  • 输入端口号查询占用情况\n"
        welcome_text += "  • 使用 PID 区域管理进程\n"
        welcome_text += "  • 使用连接监控实时查看网络连接\n"
        welcome_text += "  • 查看历史记录快速操作\n"
        welcome_text += "\n"
        welcome_text += "快捷键:\n"
        welcome_text += "  ⌘R / F5  - 刷新端口列表\n"
        welcome_text += "  ⌘Q       - 退出程序\n"
        welcome_text += "  F1       - 显示关于信息\n"
        welcome_text += "  ⌘E       - 导出结果\n"
        welcome_text += "  ⌘F       - 聚焦搜索框\n"
        welcome_text += "─"*60 + "\n\n"
        self.result_text.insert(tk.END, welcome_text, "info")

        # 存储查询到的PID
        self.current_pids = []

        # 底部状态栏 - 极简风格
        status_container = tk.Frame(content_frame, bg=self.colors['divider'], height=1)
        status_container.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(24, 0))

        status_bar = tk.Frame(content_frame, bg=self.colors['bg'])
        status_bar.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(12, 0))

        self.status_var = tk.StringVar()
        self.status_var.set("就绪")

        status_label = tk.Label(status_bar, textvariable=self.status_var,
                              font=self.fonts['body'],
                              fg=self.colors['text_secondary'], bg=self.colors['bg'])
        status_label.pack(side=tk.LEFT)

        version_label = tk.Label(status_bar, text="v2.0",
                               font=self.fonts['body'],
                               fg=self.colors['text_tertiary'], bg=self.colors['bg'])
        version_label.pack(side=tk.RIGHT)

        # 设置窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 初始化时显示所有端口
        self.refresh_all()

        # 设置焦点
        self.port_entry.focus_set()

        # 绑定快捷键
        self.root.bind('<Control-r>', lambda e: self.refresh_all())
        self.root.bind('<F5>', lambda e: self.refresh_all())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        self.root.bind('<F1>', lambda e: self.show_about())
        self.root.bind('<Control-e>', lambda e: self.export_results())
        self.root.bind('<Control-f>', lambda e: self.search_entry.focus_set())

    def create_mac_card(self, parent, title, row, column):
        """创建现代风格卡片 - 带阴影效果模拟"""
        # 外层容器用于模拟边框/阴影
        outer_frame = tk.Frame(parent, bg=self.colors['border'], padx=1, pady=1)
        outer_frame.grid(row=row, column=column, sticky=(tk.W, tk.E, tk.N, tk.S), padx=12, pady=8)
        
        # 内层内容
        frame = tk.Frame(outer_frame, bg=self.colors['card_bg'])
        frame.pack(fill=tk.BOTH, expand=True)
        frame.configure(padx=24, pady=24)

        # 卡片标题
        title_label = tk.Label(frame, text=title,
                              font=self.fonts['h2'],
                              fg=self.colors['text'], bg=self.colors['card_bg'])
        title_label.pack(anchor=tk.W, pady=(0, 16))

        # 分隔线
        divider = tk.Frame(frame, height=1, bg=self.colors['divider'])
        divider.pack(fill=tk.X, pady=(0, 20))

        return frame

    def create_mac_button(self, parent, text, command, color, width=None):
        """创建现代扁平风格按钮"""
        btn = tk.Button(parent, text=text,
                       command=command,
                       bg=color, fg='white',
                       font=self.fonts['body'],
                       relief='flat', cursor='hand2',
                       padx=20, pady=8,
                       activebackground=self._darken_color(color),
                       activeforeground='white',
                       borderwidth=0,
                       width=width)
        
        # 添加悬停效果
        btn.bind('<Enter>', lambda e: btn.config(bg=self._lighten_color(color)))
        btn.bind('<Leave>', lambda e: btn.config(bg=color))
        
        return btn

    def _darken_color(self, color):
        """将颜色变暗用于按钮按下效果"""
        # 简单实现，如果未定义hover色则保持原色
        return color

    def _lighten_color(self, color):
        """将颜色变亮用于悬停效果"""
        # 简单实现，查找对应的 hover 颜色
        for key, value in self.colors.items():
            if value == color and f"{key}_hover" in self.colors:
                return self.colors[f"{key}_hover"]
        return color

    def draw_netguard_logo(self, canvas, cx, cy, size):
        """绘制 NetGuard Logo - 扁平化设计"""
        import math

        # 品牌色
        primary = self.colors['primary']
        secondary = self.colors['info']
        accent = self.colors['warning']
        light = '#FFFFFF'
        dark = '#111827'

        # 1. 绘制盾牌外框 - 简化为圆润的盾牌
        shield_points = []
        for angle in range(180, 361, 10):
            rad = math.radians(angle)
            x = cx + size * 0.8 * math.cos(rad)
            y = cy - size * 0.2 + size * 0.6 * math.sin(rad)
            shield_points.extend([x, y])
        shield_points.extend([cx, cy + size * 1.0]) # 尖端
        for angle in range(0, 181, 10):
            rad = math.radians(angle)
            x = cx + size * 0.8 * math.cos(rad)
            y = cy - size * 0.2 + size * 0.6 * math.sin(rad)
            shield_points.extend([x, y])

        canvas.create_polygon(shield_points, fill=primary, outline='', width=0)

        # 2. 绘制内部符号 - 更简洁的端口标志
        # 冒号
        canvas.create_text(cx - size * 0.2, cy, text=":",
                          fill=light, font=('Consolas', int(size * 0.5), 'bold'))
        # 斜杠
        canvas.create_text(cx + size * 0.1, cy, text="//",
                          fill=light, font=('Consolas', int(size * 0.45), 'bold'))

    def log_message(self, message, tag="normal", scroll=True):
        """在结果框中添加消息 - 优化性能"""
        self.log_buffer.append((message, tag))
        self.result_text.insert(tk.END, message + "\n", tag)
        
        # 单条插入时，如果需要滚动，则执行清理和滚动
        if scroll:
            self._trim_log_lines()
            self.result_text.see(tk.END)

    def _trim_log_lines(self):
        """清理多余的日志行 - 独立出来以便批量操作时控制"""
        try:
            lines_str = self.result_text.index('end-1c').split('.')[0]
            total_lines = int(lines_str) if lines_str else 0
            if total_lines > MAX_LOG_LINES:
                self.result_text.delete(1.0, f"{total_lines - MAX_LOG_LINES + 1}.0")
        except Exception:
            pass

    def batch_log_messages(self, messages, batch_size=20, interval=5):
        """
        分片批量插入日志，彻底解决大量数据插入导致的卡顿问题
        :param messages: [(text, tag), ...] 列表
        :param batch_size: 每次插入的行数
        :param interval: 下一次插入的间隔(ms)
        """
        # 如果有正在进行的任务，先取消
        if hasattr(self, '_batch_job') and self._batch_job:
            self.root.after_cancel(self._batch_job)
            self._batch_job = None

        if not messages:
            return

        total = len(messages)
        
        def _process_chunk(start_index):
            end_index = min(start_index + batch_size, total)
            chunk = messages[start_index:end_index]
            
            # 批量插入当前分片
            for text, tag in chunk:
                self.result_text.insert(tk.END, text + "\n", tag)
                self.log_buffer.append((text, tag))
            
            # 最后一个分片处理完后，执行清理和滚动
            if end_index >= total:
                self._trim_log_lines()
                self.result_text.see(tk.END)
                # 更新状态但不显示 "..."
                current_status = self.status_var.get()
                if "..." in current_status:
                    self.update_status(current_status.replace("...", "") + " (显示完成)")
                self._batch_job = None
            else:
                # 还有剩余数据，调度下一次插入
                self._batch_job = self.root.after(interval, lambda: _process_chunk(end_index))

        # 启动第一个分片
        _process_chunk(0)

    def clear_results(self):
        """清空结果 - 同时取消正在进行的批量任务"""
        if hasattr(self, '_batch_job') and self._batch_job:
            self.root.after_cancel(self._batch_job)
            self._batch_job = None
            
        self.result_text.delete(1.0, tk.END)
        self.log_buffer.clear()

    def update_status(self, status):
        """更新状态栏 - 简化图标逻辑"""
        self.status_var.set(status)

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

    def parse_port_range(self, port_str):
        """解析端口范围 - 返回None时错误信息通过after显示"""
        port_str = port_str.strip()
        if '-' in port_str:
            try:
                start, end = port_str.split('-', 1)
                start_port = int(start.strip())
                end_port = int(end.strip())
                if 1 <= start_port <= 65535 and 1 <= end_port <= 65535:
                    return (start_port, end_port)
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", "端口号必须在1-65535之间"))
                    return None
            except ValueError:
                self.root.after(0, lambda: messagebox.showerror("错误", "端口范围格式错误，请使用如: 8000-9000"))
                return None
        else:
            try:
                port = int(port_str)
                if 1 <= port <= 65535:
                    return (port, port)
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", "端口号必须在1-65535之间"))
                    return None
            except ValueError:
                self.root.after(0, lambda: messagebox.showerror("错误", "请输入有效的端口号"))
                return None

    def query_port(self):
        """查询指定端口或端口范围"""
        port_str = self.port_entry.get().strip()
        if not port_str:
            messagebox.showwarning("警告", "请输入端口号")
            return

        port_range = self.parse_port_range(port_str)
        if port_range is None:
            return

        start_port, end_port = port_range
        
        # 如果是单个端口，保存到历史记录
        if start_port == end_port:
            self.add_to_history(str(start_port))

        # 在新线程中执行查询
        threading.Thread(target=self._query_port_thread, args=(start_port, end_port), daemon=True).start()

    def _query_port_thread(self, start_port, end_port):
        """在线程中查询端口 - 批量更新UI以提高性能"""
        # 在主线程清空结果
        self.root.after(0, self.clear_results)
        
        if start_port == end_port:
            self.root.after(0, lambda: self.update_status(f"正在查询端口 {start_port}..."))
            self.root.after(0, lambda: self.log_message(f"查询端口 {start_port}", "header"))
        else:
            self.root.after(0, lambda: self.update_status(f"正在查询端口范围 {start_port}-{end_port}..."))
            self.root.after(0, lambda: self.log_message(f"查询端口范围 {start_port}-{end_port}", "header"))
        
        self.root.after(0, lambda: self.log_message("─" * 60, "header"))

        try:
            # 使用 netstat 查询端口 - 使用更高效的参数
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, encoding='gbk', timeout=10)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                found = False
                current_pids = []
                
                # 收集所有匹配的结果，最后统一更新
                all_results_msg = []

                for line in lines:
                    # 检查是否匹配端口范围
                    for port in range(start_port, end_port + 1):
                        port_pattern = f':{port}'
                        if port_pattern in line and ('LISTENING' in line or 'ESTABLISHED' in line):
                            found = True
                            parts = line.split()
                            if len(parts) >= 5:
                                local_address = parts[1]
                                foreign_address = parts[2]
                                state = parts[3]
                                pid = parts[4]

                                try:
                                    int(pid)
                                    if pid not in current_pids:
                                        current_pids.append(pid)
                                except ValueError:
                                    continue

                                # 收集进程信息
                                process_info = self._get_process_info_cached(pid)
                                info_msg = [
                                    (f"本地地址: {local_address}", "info"),
                                    (f"远程地址: {foreign_address}", "normal"),
                                    (f"连接状态: {state}", "normal"),
                                    (f"进程PID: ", "info"),
                                    (f"{pid}", "pid"),
                                ]
                                
                                if process_info:
                                    info_msg.append((f"进程名称: {process_info['name']}", "warning"))
                                    info_msg.append((f"进程路径: {process_info['exe']}", "normal"))
                                    info_msg.append((f"命令行: {process_info['cmdline']}", "normal"))
                                else:
                                    info_msg.append(("无法获取进程详细信息", "error"))
                                
                                info_msg.append(("─" * 60, "info"))
                                all_results_msg.append(info_msg)
                            break

                # 批量将结果发送到主线程
                def batch_update(results, pids, is_found):
                    # 扁平化所有消息以便于分片处理
                    flat_msgs = []
                    for msg_group in results:
                        for text, tag in msg_group:
                            flat_msgs.append((text, tag))
                    
                    # 使用分片插入代替一次性循环
                    self.batch_log_messages(flat_msgs, batch_size=50)
                    
                    self.current_pids = pids
                    if not is_found:
                        if start_port == end_port:
                            self.log_message(f"端口 {start_port} 当前未被占用", "success")
                            self.update_status(f"端口 {start_port} 未被占用")
                        else:
                            self.log_message(f"端口范围 {start_port}-{end_port} 内没有端口被占用", "success")
                            self.update_status(f"端口范围内没有端口被占用")
                    else:
                        self.update_status(f"查询完成 - 找到 {len(pids)} 个进程")
                        if pids:
                            self.pid_entry.delete(0, tk.END)
                            self.pid_entry.insert(0, pids[0])

                self.root.after(0, lambda: batch_update(all_results_msg, current_pids, found))
                
            else:
                self.root.after(0, lambda: self.log_message("查询失败: " + result.stderr, "error"))
                self.root.after(0, lambda: self.update_status("查询失败"))

        except subprocess.TimeoutExpired:
            self.root.after(0, lambda: self.log_message("查询超时，请重试", "error"))
            self.root.after(0, lambda: self.update_status("查询超时"))
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"查询出错: {str(e)}", "error"))
            self.root.after(0, lambda: self.update_status("查询出错"))

    def _get_process_info_cached(self, pid):
        """获取进程信息 - 带缓存优化"""
        current_time = time.time()

        # 检查缓存是否有效
        if pid in self._process_cache:
            cache_entry = self._process_cache[pid]
            if current_time - cache_entry['timestamp'] < self._cache_ttl:
                return cache_entry['data']

        try:
            process = psutil.Process(int(pid))
            info = {
                'name': process.name(),
                'exe': process.exe(),
                'cmdline': ' '.join(process.cmdline())
            }

            # 更新缓存
            self._process_cache[pid] = {
                'data': info,
                'timestamp': current_time
            }
            return info
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    def kill_process(self):
        """终止占用端口的进程"""
        port_str = self.port_entry.get().strip()
        if not port_str:
            messagebox.showwarning("警告", "请先查询端口")
            return

        port_range = self.parse_port_range(port_str)
        if port_range is None:
            return

        start_port, end_port = port_range

        if not messagebox.askyesno("确认", f"确定要终止占用端口 {start_port if start_port == end_port else f'{start_port}-{end_port}'} 的进程吗？\n\n注意：这可能会导致相关应用程序异常退出！"):
            return

        threading.Thread(target=self._kill_process_thread, args=(start_port, end_port), daemon=True).start()

    def _kill_process_thread(self, start_port, end_port):
        """在线程中终止进程 - 优化性能"""
        self.clear_results()
        
        if start_port == end_port:
            self.update_status(f"正在终止占用端口 {start_port} 的进程...")
            self.log_message(f"终止端口 {start_port} 进程", "header")
        else:
            self.update_status(f"正在终止端口范围 {start_port}-{end_port} 的进程...")
            self.log_message(f"终止端口范围 {start_port}-{end_port} 进程", "header")
        
        self.log_message("─" * 60, "header")

        try:
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, encoding='gbk', timeout=10)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                pids = set()

                for line in lines:
                    for port in range(start_port, end_port + 1):
                        port_pattern = f':{port}'
                        if port_pattern in line and ('LISTENING' in line or 'ESTABLISHED' in line):
                            parts = line.split()
                            if len(parts) >= 5:
                                pid = parts[4]
                                try:
                                    int(pid)
                                    pids.add(pid)
                                except ValueError:
                                    continue
                            break

                if not pids:
                    if start_port == end_port:
                        self.log_message(f"端口 {start_port} 当前未被占用", "info")
                        self.update_status(f"端口 {start_port} 未被占用")
                    else:
                        self.log_message(f"端口范围 {start_port}-{end_port} 内没有端口被占用", "info")
                        self.update_status(f"端口范围内没有端口被占用")
                    return

                for pid in pids:
                    self._terminate_process(pid)

                # 验证端口是否已释放
                self.log_message("\n正在验证端口是否已释放...", "info")
                time.sleep(1)

                result2 = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, encoding='gbk', timeout=10)
                if result2.returncode == 0:
                    lines2 = result2.stdout.split('\n')
                    still_occupied = False
                    for port in range(start_port, end_port + 1):
                        port_pattern = f':{port}'
                        if any(port_pattern in line and ('LISTENING' in line or 'ESTABLISHED' in line) for line in lines2):
                            still_occupied = True
                            break

                    if still_occupied:
                        self.log_message(f"警告: 端口仍被占用，可能需要重启相关服务", "error")
                    else:
                        self.log_message(f"端口已成功释放", "success")

                self.update_status("终止操作完成")
            else:
                self.log_message("查询端口失败: " + result.stderr, "error")
                self.update_status("终止操作失败")

        except subprocess.TimeoutExpired:
            self.log_message("操作超时，请重试", "error")
            self.update_status("操作超时")
        except Exception as e:
            self.log_message(f"终止进程时出错: {str(e)}", "error")
            self.update_status("终止操作出错")

    def _terminate_process(self, pid):
        """终止单个进程 - 线程安全版本"""
        try:
            process = psutil.Process(int(pid))
            process_name = process.name()
            self.root.after(0, lambda: self.log_message(f"正在终止进程: {process_name} (PID: {pid})"))

            process.terminate()

            try:
                process.wait(timeout=5)
                self.root.after(0, lambda: self.log_message(f"进程 {process_name} (PID: {pid}) 已成功终止", "success"))
            except psutil.TimeoutExpired:
                self.root.after(0, lambda: self.log_message(f"正常终止失败，正在强制终止进程 {process_name} (PID: {pid})", "info"))
                process.kill()
                process.wait(timeout=3)
                self.root.after(0, lambda: self.log_message(f"进程 {process_name} (PID: {pid}) 已强制终止", "success"))

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            self.root.after(0, lambda: self.log_message(f"无法终止进程 PID {pid}: {str(e)}", "error"))
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"终止进程 PID {pid} 时出错: {str(e)}", "error"))

    def refresh_all(self):
        """刷新显示所有监听端口"""
        threading.Thread(target=self._refresh_all_thread, daemon=True).start()

    def _refresh_all_thread(self):
        """在线程中刷新所有端口 - 优化性能，减少UI回调次数"""
        self.root.after(0, self.clear_results)
        self.root.after(0, lambda: self.update_status("正在获取所有端口信息..."))
        self.root.after(0, lambda: self.log_message("刷新 所有监听端口列表", "header"))
        self.root.after(0, lambda: self.log_message("─" * 60, "header"))

        try:
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, encoding='gbk', timeout=10)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                seen = set()  # 用于去重
                listening_ports = []
                all_ports_data = []  # 存储用于搜索的数据

                for line in lines:
                    if not line.strip() or line.startswith('TCP') or line.startswith('UDP'):
                        continue

                    if 'LISTENING' in line:
                        parts = line.split()
                        if len(parts) >= 5 and parts[4]:
                            pid = parts[4]
                            local_address = parts[1]

                            if ':' in local_address:
                                port = local_address.split(':')[-1]
                                try:
                                    port_num = int(port)
                                    if 1 <= port_num <= 65535:
                                        # 使用 (port, pid) 作为唯一键去重
                                        key = (port, pid)
                                        if key not in seen:
                                            seen.add(key)
                                            listening_ports.append((port, local_address, pid))
                                            
                                            # 获取进程信息用于搜索
                                            process_info = self._get_process_info_cached(pid)
                                            all_ports_data.append({
                                                'port': port,
                                                'pid': pid,
                                                'address': local_address,
                                                'name': process_info['name'] if process_info else '[无法获取]'
                                            })
                                except ValueError:
                                    continue

                def update_ui(ports, data):
                    self.all_ports_data = data
                    if ports:
                        ports.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 999999)
                        self.log_message(f"共找到 {len(ports)} 个监听端口:\n", "info")
                        
                        # 构建所有消息列表
                        batch_msg = []
                        for port, address, pid in ports:
                            # 从 data 中找已获取的信息
                            p_name = next((d['name'] for d in data if d['port'] == port and d['pid'] == pid), "[无法获取进程名]")
                            tag = "info" if p_name != "[无法获取进程名]" else "error"
                            batch_msg.append((f"端口 {port:<6} | PID {pid:<8} | {p_name}", tag))
                        
                        # 使用分片插入，避免卡顿
                        self.batch_log_messages(batch_msg)
                    else:
                        self.log_message("当前没有监听的端口", "success")
                    
                    self.update_status(f"刷新完成 - 共 {len(ports)} 个监听端口")

                self.root.after(0, lambda: update_ui(listening_ports, all_ports_data))
            else:
                self.root.after(0, lambda: self.log_message("获取端口信息失败: " + result.stderr, "error"))
                self.root.after(0, lambda: self.update_status("刷新失败"))

        except subprocess.TimeoutExpired:
            self.root.after(0, lambda: self.log_message("刷新超时，请重试", "error"))
            self.root.after(0, lambda: self.update_status("刷新超时"))
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"刷新时出错: {str(e)}", "error"))
            self.root.after(0, lambda: self.update_status("刷新出错"))

    def on_search(self, event=None):
        """搜索框内容变化时触发 - 增加防抖处理"""
        if hasattr(self, '_search_timer'):
            self.root.after_cancel(self._search_timer)
        self._search_timer = self.root.after(300, self.filter_ports)

    def clear_search(self):
        """清除搜索"""
        self.search_var.set('')
        self.filter_ports()

    def filter_ports(self):
        """根据搜索关键词过滤端口 - 分片加载以提高性能"""
        keyword = self.search_var.get().strip().lower()
        if not keyword:
            return

        # 在已加载的数据中搜索
        matching_ports = []
        for data in self.all_ports_data:
            if (keyword in data['port'].lower() or 
                keyword in data['pid'].lower() or 
                keyword in data['name'].lower()):
                matching_ports.append(data)

        if matching_ports:
            # 先清除
            self.result_text.delete(1.0, tk.END)
            
            # 构建消息列表
            msgs = []
            msgs.append((f"搜索结果: 找到 {len(matching_ports)} 个匹配的端口", "header"))
            msgs.append(("─" * 60, "header"))
            
            for data in matching_ports:
                msg = f"端口 {data['port']:<6} | PID {data['pid']:<8} | {data['name']}"
                msgs.append((msg, "info"))
            
            # 使用分片加载
            self.batch_log_messages(msgs, batch_size=50)
            
        else:
            # 清除并显示未找到
            self.result_text.delete(1.0, tk.END)
            self.log_message(f"搜索结果: 未找到匹配的端口 '{keyword}'", "warning")

    def export_results(self):
        """导出结果到文件"""
        try:
            # 获取当前结果文本
            content = self.result_text.get(1.0, tk.END)
            
            if not content.strip():
                messagebox.showwarning("警告", "没有可导出的内容")
                return

            # 选择保存路径
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
                title="导出结果"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.update_status(f"结果已导出到: {file_path}")
                self.log_message(f"\n结果已导出到: {file_path}", "success")
                messagebox.showinfo("导出成功", f"结果已成功导出到:\n{file_path}")

        except Exception as e:
            messagebox.showerror("导出失败", f"导出时出错: {str(e)}")
            self.update_status("导出失败")

    def show_process_details_dialog(self):
        """显示进程详细信息弹窗"""
        pid_str = self.pid_entry.get().strip()
        if not pid_str:
            messagebox.showwarning("警告", "请先输入PID")
            return

        try:
            pid = int(pid_str)
        except ValueError:
            messagebox.showerror("错误", "请输入有效的PID数字")
            return

        try:
            process = psutil.Process(pid)
            
            # 创建详细信息弹窗
            dialog = tk.Toplevel(self.root)
            dialog.title(f"进程详情 - PID {pid}")
            dialog.geometry("500x600")
            dialog.resizable(True, True)
            dialog.configure(bg=self.colors['card_bg'])
            dialog.transient(self.root)
            dialog.grab_set()

            # 居中显示
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
            y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
            dialog.geometry(f'+{x}+{y}')

            # 标题
            title = tk.Label(dialog, text=f"进程详细信息", 
                           font=('SF Pro Display', 18, 'bold'),
                           fg=self.colors['text'], bg=self.colors['card_bg'])
            title.pack(pady=(20, 10))

            # 信息框架
            info_frame = tk.Frame(dialog, bg=self.colors['card_bg'])
            info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

            # 获取详细信息
            details = [
                ("PID", str(pid)),
                ("名称", process.name()),
                ("可执行文件", process.exe()),
                ("命令行", ' '.join(process.cmdline())),
                ("创建时间", datetime.fromtimestamp(process.create_time()).strftime('%Y-%m-%d %H:%M:%S')),
                ("状态", process.status()),
                ("CPU 使用率", f"{process.cpu_percent(interval=0.1):.1f}%"),
                ("内存使用", f"{process.memory_info().rss / 1024 / 1024:.2f} MB"),
                ("线程数", str(process.num_threads())),
                ("父进程", str(process.ppid())),
            ]

            for label, value in details:
                row = tk.Frame(info_frame, bg=self.colors['card_bg'])
                row.pack(fill=tk.X, pady=5)
                
                lbl = tk.Label(row, text=f"{label}:", 
                             font=('SF Pro Text', 12, 'bold'),
                             fg=self.colors['text_secondary'], bg=self.colors['card_bg'],
                             width=12, anchor='w')
                lbl.pack(side=tk.LEFT)
                
                val = tk.Label(row, text=value, 
                             font=('SF Pro Text', 12),
                             fg=self.colors['text'], bg=self.colors['card_bg'],
                             wraplength=350, anchor='w')
                val.pack(side=tk.LEFT, fill=tk.X, expand=True)

            # 按钮
            btn_frame = tk.Frame(dialog, bg=self.colors['card_bg'])
            btn_frame.pack(pady=20)
            
            close_btn = tk.Button(btn_frame, text="关闭", 
                                command=dialog.destroy,
                                bg=self.colors['primary'], fg='white',
                                font=('SF Pro Text', 12),
                                relief='flat', cursor='hand2',
                                padx=30, pady=8)
            close_btn.pack()

        except psutil.NoSuchProcess:
            messagebox.showerror("错误", f"进程 PID {pid} 不存在")
        except psutil.AccessDenied:
            messagebox.showerror("错误", f"无法访问进程 PID {pid} 的信息")
        except Exception as e:
            messagebox.showerror("错误", f"获取进程信息时出错: {str(e)}")

    def extract_pid(self):
        """提取当前查询到的PID"""
        if self.current_pids:
            if len(self.current_pids) == 1:
                self.pid_entry.delete(0, tk.END)
                self.pid_entry.insert(0, self.current_pids[0])
                self.update_status(f"已提取PID: {self.current_pids[0]}")
            else:
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
        dialog.configure(bg=self.colors['card_bg'])

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f'+{x}+{y}')

        ttk.Label(dialog, text="找到多个PID，请选择要操作的目标:", padding="10").pack()

        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        pid_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=('SF Mono', 11))
        pid_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=pid_listbox.yview)

        for i, pid in enumerate(self.current_pids):
            process_info = self._get_process_info_cached(pid)
            if process_info:
                pid_listbox.insert(tk.END, f"PID {pid} - {process_info['name']}")
            else:
                pid_listbox.insert(tk.END, f"PID {pid} - [未知进程]")

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
        """根据PID直接杀掉进程 - 修复卡顿问题"""
        pid_str = self.pid_entry.get().strip()
        if not pid_str:
            messagebox.showwarning("警告", "请输入PID")
            return

        try:
            pid = int(pid_str)
        except ValueError:
            messagebox.showerror("错误", "请输入有效的PID数字")
            return

        # 获取进程信息用于确认对话框
        try:
            process = psutil.Process(pid)
            process_name = process.name()
            confirm_msg = f"确定要终止进程 {process_name} (PID: {pid}) 吗？\n\n注意：这可能会导致相关应用程序异常退出！"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            confirm_msg = f"确定要终止进程 PID: {pid} 吗？\n\n注意：无法获取进程详细信息！"

        # 使用after延迟执行确认对话框，避免阻塞UI
        self.root.after(10, lambda: self._confirm_and_kill(pid, confirm_msg))

    def _confirm_and_kill(self, pid, confirm_msg):
        """显示确认对话框并执行终止"""
        if messagebox.askyesno("确认", confirm_msg):
            # 立即更新UI状态
            self.update_status(f"正在终止进程 PID: {pid}...")
            self.log_message(f"终止进程 PID: {pid}", "header")
            self.log_message("─" * 60, "header")
            # 启动后台线程执行终止操作
            threading.Thread(target=self._kill_by_pid_thread, args=(pid,), daemon=True).start()

    def _kill_by_pid_thread(self, pid):
        """在线程中根据PID终止进程 - 只执行终止操作，UI更新在主线程完成"""
        self._terminate_process(str(pid))

        # 验证进程是否已终止
        try:
            psutil.Process(pid)
            self.root.after(0, lambda: self.log_message("警告: 进程可能仍在运行", "error"))
        except psutil.NoSuchProcess:
            self.root.after(0, lambda: self.log_message("验证: 进程已成功终止", "success"))

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
            self.log_message(f"PID {pid_str} 已复制到剪贴板", "success")
        except Exception as e:
            messagebox.showerror("错误", f"复制失败: {str(e)}")
            self.update_status("复制失败")

    def show_shortcuts(self):
        """显示快捷键提示 - NetGuard 品牌版"""
        shortcuts_text = """🛡️ NetGuard 快捷键指南

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

文件操作:
Ctrl+E   - 导出查询结果
Ctrl+Q   - 退出程序

查询操作:
Ctrl+R   - 刷新端口列表
F5       - 刷新端口列表
Enter    - 执行查询（在输入框中）

导航操作:
Ctrl+F   - 聚焦搜索框
Esc      - 清除搜索内容

帮助:
F1       - 显示关于信息
?        - 显示快捷键

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

提示: 所有快捷键在任意界面均可使用"""

        messagebox.showinfo("NetGuard 快捷键", shortcuts_text)

    def show_about(self):
        """显示关于对话框 - NetGuard 品牌版"""
        about_text = """🛡️ NetGuard 端口管理工具 v2.0

守护网络端口安全

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

主要功能:
• 🔍 端口占用查询（支持范围查询）
• ⚡ PID快速操作
• 🔧 进程管理
• 📊 实时监控
• 🌐 网络连接监控
• 📜 端口历史记录
• 💾 搜索结果导出
• ℹ️ 进程详细信息查看

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

快捷键:
• Ctrl+R / F5 - 刷新端口列表
• Ctrl+Q - 退出程序
• Ctrl+E - 导出结果
• Ctrl+F - 聚焦搜索框
• F1 - 显示关于信息

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

技术栈:
• Python 3.x + Tkinter
• psutil 进程和网络管理
• 多线程实时监控
• macOS 风格 UI 设计

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ 安全提醒:
使用前请了解相关进程的作用
避免终止系统关键进程
监控网络连接时请遵守相关法律法规

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

© 2024 NetGuard. All rights reserved."""

        messagebox.showinfo("关于 NetGuard", about_text)

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
        if port in self.port_history:
            self.port_history.remove(port)

        self.port_history.insert(0, port)

        if len(self.port_history) > MAX_HISTORY:
            self.port_history = self.port_history[:MAX_HISTORY]

        self.port_combo['values'] = self.port_history
        self.save_port_history()

    def on_history_selected(self, event):
        """历史记录选择事件 - 增加防抖"""
        selected_port = self.history_var.get().strip()
        if selected_port:
            # 将选中的历史端口填入输入框
            self.port_var.set(selected_port)
            self.update_status(f"已选择历史端口: {selected_port}")
            
            # 取消之前的定时任务
            if hasattr(self, '_history_timer'):
                self.root.after_cancel(self._history_timer)
            
            # 延迟执行查询，避免频繁触发
            self._history_timer = self.root.after(300, self.query_port)

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
        dialog.configure(bg=self.colors['card_bg'])

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f'+{x}+{y}')

        main_frame = ttk.Frame(dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(main_frame, text="端口历史记录",
                               font=('SF Pro Display', 16, 'bold'))
        title_label.pack(pady=(0, 15))

        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        history_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                     font=('SF Mono', 12))
        history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=history_listbox.yview)

        for i, port in enumerate(self.port_history):
            history_listbox.insert(tk.END, f"端口 {port}")
            history_listbox.itemconfig(i, fg=self.colors['primary'])

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

        ttk.Button(button_frame, text="选择并查询", command=select_port,
                  style='Action.TButton', width=15).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="删除选中", command=delete_port,
                  style='Danger.TButton', width=15).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="清空全部", command=clear_all,
                  style='Warning.TButton', width=15).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="关闭", command=close_dialog,
                  width=10).pack(side=tk.RIGHT)

        history_listbox.bind('<Double-Button-1>', lambda e: select_port())

    def start_monitoring(self):
        """开始网络连接监控"""
        if self.monitoring_active:
            return

        port_str = self.port_var.get().strip()
        if not port_str:
            messagebox.showwarning("警告", "请先输入要监控的端口号")
            return

        # 解析端口
        port_range = self.parse_port_range(port_str)
        if port_range is None:
            return
        
        start_port, end_port = port_range
        if start_port != end_port:
            messagebox.showwarning("警告", "监控功能只支持单个端口")
            return
        
        port = start_port

        self.monitoring_active = True
        self.monitor_status_label.config(text="监控中", fg=self.colors['success'])
        self.start_monitor_btn.config(state='disabled')
        self.stop_monitor_btn.config(state='normal')
        self.refresh_connections_btn.config(state='disabled')

        self.monitor_thread = threading.Thread(target=self._monitor_connections, args=(port,), daemon=True)
        self.monitor_thread.start()

        self.log_message(f"开始监控端口 {port} 的网络连接", "info")
        self.update_status(f"正在监控端口 {port} 的网络连接")

    def stop_monitoring(self):
        """停止网络连接监控"""
        if not self.monitoring_active:
            return

        self.monitoring_active = False
        self.monitor_status_label.config(text="未监控", fg=self.colors['text_tertiary'])
        self.start_monitor_btn.config(state='normal')
        self.stop_monitor_btn.config(state='disabled')
        self.refresh_connections_btn.config(state='normal')

        self.log_message("网络连接监控已停止", "warning")
        self.update_status("网络连接监控已停止")

    def refresh_connections(self):
        """手动刷新连接信息"""
        port_str = self.port_var.get().strip()
        if not port_str:
            messagebox.showwarning("警告", "请先输入端口号")
            return

        port_range = self.parse_port_range(port_str)
        if port_range is None:
            return
        
        start_port, end_port = port_range
        if start_port != end_port:
            messagebox.showwarning("警告", "刷新连接功能只支持单个端口")
            return

        threading.Thread(target=self._get_connections_info, args=(start_port,), daemon=True).start()

    def _monitor_connections(self, port):
        """监控网络连接的主循环"""
        try:
            while self.monitoring_active:
                self._get_connections_info(port)
                time.sleep(MONITOR_INTERVAL)
        except Exception as e:
            self.log_message(f"监控出错: {str(e)}", "error")

    def _get_connections_info(self, port):
        """获取指定端口的连接信息 - 优化性能"""
        try:
            connections = []

            # 使用psutil获取网络连接
            for conn in psutil.net_connections():
                if conn.laddr.port == port:
                    local_ip = conn.laddr.ip
                    local_port = conn.laddr.port
                    status = conn.status
                    pid = conn.pid

                    remote_addr = "N/A"
                    if conn.raddr:
                        remote_addr = f"{conn.raddr.ip}:{conn.raddr.port}"

                    process_name = "Unknown"
                    if pid:
                        process_info = self._get_process_info_cached(str(pid))
                        if process_info:
                            process_name = process_info['name']

                    connections.append({
                        'local_addr': f"{local_ip}:{local_port}",
                        'remote_addr': remote_addr,
                        'status': status,
                        'pid': pid,
                        'process_name': process_name
                    })

            self.current_connections = connections
            self._display_connections(connections, port)

        except Exception as e:
            self.log_message(f"获取连接信息出错: {str(e)}", "error")

    def _display_connections(self, connections, port):
        """显示连接信息"""
        self.root.after(0, self._update_connections_display, connections, port)

    def _update_connections_display(self, connections, port):
        """更新连接显示UI"""
        self.connections_text.delete(1.0, tk.END)

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.connections_text.insert(tk.END, f"端口 {port} 连接监控 - {timestamp}\n", "header")
        self.connections_text.insert(tk.END, "─" * 50 + "\n", "header")

        if not connections:
            self.connections_text.insert(tk.END, f"端口 {port} 当前没有活动连接\n", "info")
        else:
            self.connections_text.insert(tk.END, f"找到 {len(connections)} 个连接:\n\n", "info")

            for i, conn in enumerate(connections, 1):
                self.connections_text.insert(tk.END, f"连接 #{i}\n", "highlight")
                self.connections_text.insert(tk.END, f"本地地址: {conn['local_addr']}\n", "info")
                self.connections_text.insert(tk.END, f"远程地址: {conn['remote_addr']}\n", "info")
                self.connections_text.insert(tk.END, f"连接状态: {conn['status']}\n", "info")

                if conn['pid']:
                    self.connections_text.insert(tk.END, f"进程PID: {conn['pid']}\n", "info")
                    self.connections_text.insert(tk.END, f"进程名称: {conn['process_name']}\n", "warning")
                else:
                    self.connections_text.insert(tk.END, f"进程PID: [系统进程]\n", "warning")

                self.connections_text.insert(tk.END, "─" * 40 + "\n", "info")

    def on_closing(self):
        """窗口关闭时的清理工作"""
        if self.monitoring_active:
            self.monitoring_active = False

        self.root.destroy()

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
