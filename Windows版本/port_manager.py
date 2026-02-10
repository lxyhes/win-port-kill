#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NetGuard Pro v3.5 - 终极增强版
集成：侧边栏布局、标签筛选、批量管理、实时监控、深度进程探测
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

# 常量配置
MAX_HISTORY = 20
MONITOR_INTERVAL = 2
MAX_LOG_LINES = 200

class ToolTip:
    def __init__(self, widget, text):
        self.widget, self.text, self.tip = widget, text, None
        self.widget.bind('<Enter>', self.show)
        self.widget.bind('<Leave>', self.hide)
    def show(self, e=None):
        if self.tip: return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, font=('Microsoft YaHei UI', 9), bg='#333333', fg='white', padx=8, pady=4).pack()
    def hide(self, e=None):
        if self.tip: self.tip.destroy(); self.tip = None

class PortManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NetGuard Pro - 端口管理助手")
        self.root.geometry("1500x950")
        self.root.configure(bg='#F3F4F6')

        # 核心数据
        self.all_ports_data = []
        self.selected_ports_tags = set()
        self.monitoring_active = False
        self._process_cache = {}
        self._cache_ttl = 10
        self.history_file = Path("port_history.json")
        self.port_history = self.load_port_history()
        
        # 自定义标签组配置
        self.groups_file = Path("port_groups.json")
        self.custom_groups = self.load_custom_groups()
        # 如果是首次运行，初始化默认组
        if not self.custom_groups:
            self.custom_groups = {
                "Web服务": "80,443", 
                "数据库": "3306,5432,6379,27017", 
                "开发调试": "3000,5000,8000,8080"
            }
            self.save_custom_groups()

        self.setup_styles()
        self.setup_ui()

    def load_custom_groups(self):
        """加载自定义端口组"""
        try:
            if self.groups_file.exists():
                with open(self.groups_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except: pass
        return {}

    def save_custom_groups(self):
        """保存自定义端口组"""
        try:
            with open(self.groups_file, 'w', encoding='utf-8') as f:
                json.dump(self.custom_groups, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Save groups error: {e}")

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        self.colors = {
            'primary': '#2563EB', 'primary_hover': '#1D4ED8', 'primary_light': '#EFF6FF',
            'success': '#10B981', 'danger': '#EF4444', 'warning': '#F59E0B', 
            'info': '#3B82F6', 'bg': '#F3F4F6', 'card_bg': '#FFFFFF', 
            'text': '#111827', 'text_secondary': '#6B7280', 'text_tertiary': '#9CA3AF', 
            'border': '#E5E7EB'
        }
        self.fonts = {
            'h1': ('Microsoft YaHei UI', 16, 'bold'), 'h2': ('Microsoft YaHei UI', 11, 'bold'),
            'body': ('Microsoft YaHei UI', 10), 'mono': ('Consolas', 10), 'icon': ('Segoe UI Symbol', 12)
        }
        style.configure('Treeview', background='white', font=self.fonts['body'], rowheight=40, borderwidth=0)
        style.configure('Treeview.Heading', font=self.fonts['h2'], background='#F9FAFB', relief='flat')
        style.map('Treeview', background=[('selected', '#DBEAFE')], foreground=[('selected', self.colors['primary'])])

    def setup_ui(self):
        # 1. 顶部导航栏
        header = tk.Frame(self.root, bg='white', height=75)
        header.pack(side="top", fill="x")
        tk.Frame(header, bg=self.colors['border'], height=1).pack(side="bottom", fill="x")

        tk.Label(header, text="🛡️ NetGuard Pro", font=self.fonts['h1'], fg=self.colors['primary'], bg='white').pack(side="left", padx=35)
        
        top_ops = tk.Frame(header, bg='white')
        top_ops.pack(side="right", padx=35)
        self.create_top_btn(top_ops, "📥 导出数据", self.export_results).pack(side="right", padx=10)
        self.create_top_btn(top_ops, "⚙️ 快捷键", self.show_shortcuts).pack(side="right", padx=10)
        self.create_top_btn(top_ops, "ℹ️ 关于", self.show_about).pack(side="right", padx=10)

        # 2. 主体容器
        container = tk.Frame(self.root, bg=self.colors['bg'])
        container.pack(fill="both", expand=True, padx=35, pady=25)
        
        # --- 左侧: 控制面板 ---
        sidebar = tk.Frame(container, bg=self.colors['bg'], width=380)
        sidebar.pack(side="left", fill="y", padx=(0, 25))
        sidebar.pack_propagate(False)

        # 2.1 端口查询卡片
        c1 = self.create_card(sidebar, "端口筛选与控制")
        tk.Label(c1, text="手动查询 (支持 80, 8000-9000)", font=self.fonts['body'], bg='white', fg=self.colors['text_secondary']).pack(anchor="w", pady=(0,10))
        self.port_var = tk.StringVar()
        self.port_entry = ttk.Combobox(c1, textvariable=self.port_var, font=self.fonts['mono'], values=self.port_history)
        self.port_entry.pack(fill="x", pady=(0,15))
        self.port_entry.bind('<Return>', lambda e: self.query_port())

        # 自定义标签组区域
        self.group_frame = tk.Frame(c1, bg='white')
        self.group_frame.pack(fill="x", pady=(0,15))
        self.render_custom_groups()

        # 动态标签区
        tk.Label(c1, text="活跃端口 (点击即选):", font=self.fonts['body'], bg='white', fg=self.colors['text_secondary']).pack(anchor="w", pady=(5,8))
        self.tag_container = tk.Frame(c1, bg='white')
        self.tag_container.pack(fill="both", expand=True)
        
        self.create_btn(c1, "全量刷新列表 (F5)", self.refresh_all, self.colors['success']).pack(fill="x", pady=(20,0))

        # 2.2 进程管理卡片
        c2 = self.create_card(sidebar, "进程管理中心")
        tk.Label(c2, text="选中进程 PID", font=self.fonts['body'], bg='white', fg=self.colors['text_secondary']).pack(anchor="w", pady=(0,10))
        
        pid_f = tk.Frame(c2, bg='white')
        pid_f.pack(fill="x", pady=(0,15))
        self.pid_entry = tk.Entry(pid_f, font=self.fonts['mono'], relief="solid", borderwidth=1)
        self.pid_entry.pack(side="left", fill="x", expand=True, ipady=6)
        tk.Button(pid_f, text="提取", font=self.fonts['body'], bg=self.colors['info'], fg='white', relief='flat', command=self.extract_pid_manual).pack(side="right", padx=(5,0), ipady=3)

        self.create_btn(c2, "🚀 重启选中的服务", self.restart_process, self.colors['success']).pack(fill="x", pady=5)
        self.create_btn(c2, "🛑 终止选中的进程", self.kill_by_pid, self.colors['danger']).pack(fill="x", pady=5)
        
        link_f = tk.Frame(c2, bg='white')
        link_f.pack(fill="x", pady=(12,0))
        tk.Button(link_f, text="复制 PID", font=self.fonts['body'], bg='white', fg=self.colors['primary'], relief="flat", command=self.copy_pid).pack(side="left")
        tk.Button(link_f, text="性能详情", font=self.fonts['body'], bg='white', fg=self.colors['primary'], relief="flat", command=self.show_process_details_dialog).pack(side="right")

        # 2.3 监控卡片
        c3 = self.create_card(sidebar, "连接实时监控")
        m_stat = tk.Frame(c3, bg='white')
        m_stat.pack(fill="x", pady=(0,15))
        tk.Label(m_stat, text="监控状态:", font=self.fonts['body'], bg='white').pack(side="left")
        self.monitor_status_label = tk.Label(m_stat, text="Idle", font=self.fonts['h2'], fg=self.colors['text_tertiary'], bg='white')
        self.monitor_status_label.pack(side="right")
        
        m_btns = tk.Frame(c3, bg='white')
        m_btns.pack(fill="x")
        self.start_monitor_btn = self.create_btn(m_btns, "开启监控", self.start_monitoring, self.colors['info'])
        self.start_monitor_btn.pack(side="left", fill="x", expand=True, padx=(0,5))
        self.stop_monitor_btn = self.create_btn(m_btns, "停止", self.stop_monitoring, self.colors['warning'])
        self.stop_monitor_btn.pack(side="left", fill="x", expand=True, padx=(5,0))
        self.stop_monitor_btn.config(state="disabled")

        # --- 右侧: 数据展示中心 ---
        right_panel = tk.Frame(container, bg='white', relief="solid", borderwidth=1)
        right_panel.pack(side="right", fill="both", expand=True)
        right_panel.config(highlightbackground=self.colors['border'])

        # 搜索与过滤
        s_bar = tk.Frame(right_panel, bg='white', height=65)
        s_bar.pack(fill="x", padx=30, pady=(20, 10))
        tk.Label(s_bar, text="🔍", font=self.fonts['icon'], bg='white').pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(s_bar, textvariable=self.search_var, font=self.fonts['body'], relief="flat", bg="#F9FAFB")
        self.search_entry.pack(side="left", fill="x", expand=True, padx=15, ipady=10)
        self.search_entry.bind('<KeyRelease>', self.on_search)

        # --- 新增: 快捷操作工具栏 ---
        actions_bar = tk.Frame(right_panel, bg='white', height=50)
        actions_bar.pack(fill="x", padx=30, pady=(0, 15))
        
        # 1. 重启服务
        self.create_action_btn(actions_bar, "🚀 重启服务", self.restart_process, self.colors['success']).pack(side="left", padx=(0, 10))
        # 2. 终止进程
        self.create_action_btn(actions_bar, "🛑 终止进程", self.kill_by_pid, self.colors['danger']).pack(side="left", padx=10)
        # 3. 性能详情
        self.create_action_btn(actions_bar, "📊 性能详情", self.show_process_details_dialog, self.colors['info']).pack(side="left", padx=10)
        # 4. 开启监控
        self.create_action_btn(actions_bar, "🔍 开启监控", self.start_monitoring_selected, self.colors['warning']).pack(side="left", padx=10)
        
        # 5. 复制组 (小按钮)
        tk.Frame(actions_bar, bg=self.colors['border'], width=1).pack(side="left", fill="y", padx=15)
        self.create_text_link(actions_bar, "📋 复制PID", self.copy_pid).pack(side="left", padx=5)
        self.create_text_link(actions_bar, "📋 复制端口", self.copy_port_selected).pack(side="left", padx=5)

        # 表格视图
        tree_f = tk.Frame(right_panel, bg='white')
        tree_f.pack(fill="both", expand=True, padx=30)
        cols = ("port", "pid", "name", "local", "remote", "status")
        self.tree = ttk.Treeview(tree_f, columns=cols, show="headings", selectmode="extended")
        for col, head, w in [("port", "端口", 100), ("pid", "PID", 100), ("name", "进程名称", 280), ("local", "本地地址", 220), ("remote", "远程地址", 220), ("status", "状态", 130)]:
            self.tree.heading(col, text=head, anchor="w", command=lambda c=col: self.sort_tree(c, False))
            self.tree.column(col, width=w)
        
        vsb = ttk.Scrollbar(tree_f, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Double-1>", lambda e: self.show_process_details_dialog())

        # 底部日志反馈
        self.status_var = tk.StringVar(value="就绪")
        fb_f = tk.Frame(right_panel, bg="#F9FAFB", height=150)
        fb_f.pack(fill="x")
        fb_f.pack_propagate(False)
        tk.Label(fb_f, textvariable=self.status_var, font=('Microsoft YaHei UI', 9, 'bold'), bg="#F9FAFB", fg=self.colors['text_tertiary']).pack(anchor="w", padx=30, pady=8)
        self.result_text = scrolledtext.ScrolledText(fb_f, font=self.fonts['mono'], bg='#F9FAFB', borderwidth=0, padx=30, undo=False)
        self.result_text.pack(fill="both", expand=True)
        self.result_text.tag_config("success", foreground=self.colors['success'])
        self.result_text.tag_config("error", foreground=self.colors['danger'])
        self.result_text.tag_config("warning", foreground=self.colors['warning'])

        # 注册快捷键
        self.root.bind('<F5>', lambda e: self.refresh_all())
        self.root.bind('<Control-f>', lambda e: self.search_entry.focus_set())
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.refresh_all()

    # --- 自定义标签组逻辑 ---
    def render_custom_groups(self):
        """渲染自定义标签组按钮 (带醒目的新增入口)"""
        if not hasattr(self, 'group_frame'): return
        for widget in self.group_frame.winfo_children(): widget.destroy()
        
        # 1. 标题行
        header = tk.Frame(self.group_frame, bg='white')
        header.pack(fill="x", pady=(0, 10))
        tk.Label(header, text="我的常用分组:", font=self.fonts['h2'], bg='white', fg=self.colors['text']).pack(side="left")
        # 管理链接
        tk.Button(header, text="⚙️ 管理列表", font=('Microsoft YaHei UI', 8), bg='white', fg=self.colors['text_secondary'], 
                 relief="flat", cursor="hand2", command=self.show_group_editor).pack(side="right")
        
        # 2. 标签胶囊区
        tag_container = tk.Frame(self.group_frame, bg='white')
        tag_container.pack(fill="x", pady=(0, 15))
        
        current_row = None
        for i, (name, ports) in enumerate(self.custom_groups.items()):
            if i % 3 == 0:
                current_row = tk.Frame(tag_container, bg='white')
                current_row.pack(fill="x", pady=2)
            
            btn = tk.Button(current_row, text=name, font=('Microsoft YaHei UI', 8), bg=self.colors['bg'], 
                           relief="flat", cursor="hand2", padx=10, pady=4,
                           command=lambda p=ports: [self.port_var.set(p), self.query_port()])
            btn.pack(side="left", padx=2)

        # 3. 醒目的“新增”大按钮 (放在卡片底部)
        add_btn = tk.Button(self.group_frame, text="➕ 添加自定义筛选分组", font=self.fonts['body'], 
                           bg=self.colors['primary_light'], fg=self.colors['primary'], 
                           relief="flat", cursor="hand2", pady=8,
                           command=lambda: self.show_group_editor(start_new=True))
        add_btn.pack(fill="x", pady=(5, 0))
        add_btn.bind('<Enter>', lambda e: add_btn.config(bg='#DBEAFE'))
        add_btn.bind('<Leave>', lambda e: add_btn.config(bg=self.colors['primary_light']))

    def show_group_editor(self, start_new=False):
        """显示绝对可见的标签组编辑器"""
        d = tk.Toplevel(self.root)
        d.title("管理我的端口组")
        d.geometry("600x550")
        d.configure(bg='white')
        d.transient(self.root)
        d.grab_set()
        
        # 居中显示
        d.update_idletasks()
        x = (self.root.winfo_x() + (self.root.winfo_width() // 2)) - 300
        y = (self.root.winfo_y() + (self.root.winfo_height() // 2)) - 275
        d.geometry(f"+{x}+{y}")

        # === 布局分层：先 pack 底部，再 pack 顶部，最后 pack 中间 ===
        
        # 1. 底部操作按钮栏 (最先 pack，锁死在底部)
        btn_f = tk.Frame(d, bg='#F3F4F6', pady=20, borderwidth=1, relief="solid", highlightthickness=0)
        btn_f.config(highlightbackground=self.colors['border'])
        btn_f.pack(side="bottom", fill="x")

        # 2. 顶部表单区
        input_f = tk.Frame(d, bg='white', padx=30, pady=20)
        input_f.pack(side="top", fill="x")
        
        tk.Label(input_f, text="分组名称:", font=self.fonts['body'], bg='white').pack(anchor="w")
        name_var = tk.StringVar()
        name_ent = tk.Entry(input_f, textvariable=name_var, font=self.fonts['body'], relief="solid", borderwidth=1)
        name_ent.pack(fill="x", pady=(5, 15), ipady=5)
        
        tk.Label(input_f, text="端口列表 (逗号分隔):", font=self.fonts['body'], bg='white').pack(anchor="w")
        ports_var = tk.StringVar()
        ports_ent = tk.Entry(input_f, textvariable=ports_var, font=self.fonts['body'], relief="solid", borderwidth=1)
        ports_ent.pack(fill="x", pady=(5, 5), ipady=5)
        tk.Label(input_f, text="例如: 80, 443, 8080-8090", font=('Arial', 8), bg='white', fg=self.colors['text_tertiary']).pack(anchor="w")

        # 3. 中间列表区 (自动填满剩余空间)
        tk.Label(d, text=" 已有分组列表 (点击可编辑):", font=self.fonts['h2'], bg='white', fg=self.colors['text_secondary']).pack(anchor="w", padx=30)
        list_f = tk.Frame(d, bg='white', padx=30, pady=10)
        list_f.pack(fill="both", expand=True)
        
        cols = ("name", "ports")
        tree = ttk.Treeview(list_f, columns=cols, show="headings", height=5)
        tree.heading("name", text="名称"); tree.column("name", width=150)
        tree.heading("ports", text="端口定义"); tree.column("ports", width=300)
        tree.pack(side="left", fill="both", expand=True)
        
        vsb = ttk.Scrollbar(list_f, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set); vsb.pack(side="right", fill="y")

        # --- 内部逻辑函数 ---
        def refresh_list():
            for i in tree.get_children(): tree.delete(i)
            for n in sorted(self.custom_groups.keys()):
                tree.insert("", "end", values=(n, self.custom_groups[n]))

        def reset_form():
            name_var.set(""); ports_var.set("")
            tree.selection_remove(tree.selection())
            name_ent.focus_set()

        def save_action():
            n, p = name_var.get().strip(), ports_var.get().strip().replace('，', ',')
            if not n or not p: return messagebox.showwarning("提示", "请完整填写名称和端口")
            self.custom_groups[n] = p
            self.save_custom_groups()
            self.render_custom_groups()
            refresh_list()
            messagebox.showinfo("成功", f"分组 '{n}' 已保存")

        def delete_action():
            n = name_var.get().strip()
            if n in self.custom_groups and messagebox.askyesno("确认", f"确定删除 '{n}'?"):
                del self.custom_groups[n]
                self.save_custom_groups()
                self.render_custom_groups()
                refresh_list()
                reset_form()

        tree.bind("<<TreeviewSelect>>", lambda e: [name_var.set(tree.item(tree.selection()[0], "values")[0]), 
                                                  ports_var.set(tree.item(tree.selection()[0], "values")[1])] if tree.selection() else None)
        
        # 按钮摆放 (由于 btn_f 是 side="bottom"，这里的按钮会整齐排列在最下方)
        tk.Button(btn_f, text="✨ 新建清空", command=reset_form, bg=self.colors['info'], fg='white', relief="flat", font=self.fonts['body'], padx=15, pady=8).pack(side="left", padx=(50, 10))
        tk.Button(btn_f, text="💾 保存/更新", command=save_action, bg=self.colors['primary'], fg='white', relief="flat", font=self.fonts['body'], padx=20, pady=8).pack(side="left", padx=10)
        tk.Button(btn_f, text="🗑️ 删除选中", command=delete_action, bg=self.colors['danger'], fg='white', relief="flat", font=self.fonts['body'], padx=15, pady=8).pack(side="left", padx=10)

        refresh_list()
        if start_new: reset_form()
        name_ent.focus_set()

    def create_action_btn(self, parent, text, cmd, color):
        """创建带 Emoji 的圆角感动作按钮"""
        btn = tk.Button(parent, text=text, command=cmd, bg=color, fg='white', 
                       font=self.fonts['h2'], relief='flat', cursor='hand2', padx=15, pady=6)
        btn.bind('<Enter>', lambda e: btn.config(bg=self._lighten_color(color)))
        btn.bind('<Leave>', lambda e: btn.config(bg=color))
        return btn

    def _lighten_color(self, color):
        """颜色亮度调节辅助函数"""
        # 针对当前 UI 配色的悬停亮度映射
        cmap = {
            self.colors['primary']: '#3B82F6',   # 亮蓝
            self.colors['success']: '#34D399',   # 亮绿
            self.colors['danger']: '#F87171',    # 亮红
            self.colors['info']: '#60A5FA',      # 亮天蓝
            self.colors['warning']: '#FBBF24',   # 亮橙
            '#F3F4F6': '#DBEAFE'                 # 浅灰变浅蓝
        }
        return cmap.get(color, color)

    def create_text_link(self, parent, text, cmd):
        """创建文本链接样式的按钮"""
        btn = tk.Button(parent, text=text, command=cmd, bg='white', fg=self.colors['primary'], 
                       font=self.fonts['body'], relief='flat', cursor='hand2')
        btn.bind('<Enter>', lambda e: btn.config(fg=self.colors['primary_hover']))
        btn.bind('<Leave>', lambda e: btn.config(fg=self.colors['primary']))
        return btn

    def start_monitoring_selected(self):
        """快捷操作：监控表格选中的端口"""
        sel = self.tree.selection()
        if sel:
            port = self.tree.item(sel[0], "values")[0]
            self.port_var.set(port)
            self.start_monitoring()
        else:
            messagebox.showinfo("提示", "请先在表格中选中要监控的行")

    def copy_port_selected(self):
        """快捷操作：复制表格选中的端口"""
        sel = self.tree.selection()
        port = self.tree.item(sel[0], "values")[0] if sel else self.port_var.get().strip()
        if port:
            self.root.clipboard_clear()
            self.root.clipboard_append(port)
            self.update_status(f"已复制端口: {port}")
        else:
            messagebox.showinfo("提示", "没有可复制的端口")

    # --- 辅助 UI 函数 ---
    def create_card(self, parent, title):
        outer = tk.Frame(parent, bg=self.colors['border'], padx=1, pady=1)
        outer.pack(fill="x", pady=(0, 20))
        inner = tk.Frame(outer, bg='white', padx=25, pady=25)
        inner.pack(fill="both", expand=True)
        tk.Label(inner, text=title, font=self.fonts['h2'], bg='white', fg=self.colors['text']).pack(anchor="w", pady=(0,15))
        tk.Frame(inner, bg=self.colors['border'], height=1).pack(fill="x", pady=(0,15))
        return inner

    def create_btn(self, parent, text, cmd, color):
        btn = tk.Button(parent, text=text, command=cmd, bg=color, fg='white', font=self.fonts['body'], relief='flat', cursor='hand2', pady=10)
        return btn

    def create_top_btn(self, parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd, bg='white', fg=self.colors['text_secondary'], font=self.fonts['body'], relief='flat', cursor='hand2')

    def log_message(self, msg, tag="info"):
        self.result_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n", tag)
        self.result_text.see(tk.END)

    # --- 核心逻辑 ---
    def refresh_all(self):
        self.status_var.set("正在扫描全量网络端口...")
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self):
        try:
            res = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, encoding='gbk')
            lines = res.stdout.splitlines()
            data, seen = [], set()
            for line in lines:
                parts = line.split()
                if len(parts) >= 5 and ('LISTENING' in line or 'ESTABLISHED' in line):
                    local = parts[1]
                    port = local.split(':')[-1]
                    pid = parts[4]
                    if (port, pid) in seen: continue
                    seen.add((port, pid))
                    p_info = self._get_proc_cached(pid)
                    data.append({'port': port, 'pid': pid, 'name': p_info['name'], 'address': local, 'remote': parts[2], 'status': parts[3]})
            self.root.after(0, lambda: self._render_tree(data))
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"刷新失败: {e}", "error"))

    def _render_tree(self, data):
        self.all_ports_data = data
        self._update_port_tags(data)
        target = self.port_var.get().strip()
        if target: self._apply_smart_filter(target)
        else: self._exec_filter()

    def _update_port_tags(self, data):
        for w in self.tag_container.winfo_children(): w.destroy()
        ports = sorted(list(set(d['port'] for d in data)), key=lambda x: int(x) if x.isdigit() else 0)
        row_f = None
        for i, p in enumerate(ports):
            if i % 4 == 0: row_f = tk.Frame(self.tag_container, bg='white'); row_f.pack(fill="x")
            is_sel = p in self.selected_ports_tags
            tk.Button(row_f, text=p, font=('Arial', 8), relief="flat", cursor="hand2", padx=6, pady=2,
                      bg=("#DBEAFE" if is_sel else "#F3F4F6"), fg=("#2563EB" if is_sel else "#6B7280"),
                      command=lambda x=p: self._toggle_tag(x)).pack(side="left", padx=2, pady=2)

    def _toggle_tag(self, p):
        if p in self.selected_ports_tags: self.selected_ports_tags.remove(p)
        else: self.selected_ports_tags.add(p)
        self.port_var.set(", ".join(sorted(list(self.selected_ports_tags), key=lambda x: int(x) if x.isdigit() else 0)))
        self._render_tree(self.all_ports_data)

    def _apply_smart_filter(self, target_str):
        target_ports = set()
        try:
            parts = target_str.replace('，', ',').split(',')
            for part in parts:
                part = part.strip()
                if not part: continue
                if '-' in part:
                    s, e = map(int, part.split('-'))
                    target_ports.update(range(s, e + 1))
                else: target_ports.add(int(part))
        except:
            self.search_var.set(target_str); self._exec_filter(); return

        for item in self.tree.get_children(): self.tree.delete(item)
        match = [d for d in self.all_ports_data if d['port'].isdigit() and int(d['port']) in target_ports]
        for d in sorted(match, key=lambda x: int(x['port'])):
            self.tree.insert("", tk.END, values=(d['port'], d['pid'], d['name'], d['address'], d['remote'], d['status']))
        self.status_var.set(f"筛选结果: {len(match)} 个项目")

    def query_port(self):
        p = self.port_var.get().strip()
        self.add_to_history(p)
        self.refresh_all()

    def _exec_filter(self):
        k = self.search_var.get().lower()
        for item in self.tree.get_children(): self.tree.delete(item)
        match = [d for d in self.all_ports_data if not k or k in d['port'] or k in d['pid'] or k in d['name'].lower()]
        for d in sorted(match, key=lambda x: int(x['port'])):
            self.tree.insert("", tk.END, values=(d['port'], d['pid'], d['name'], d['address'], d['remote'], d['status']))
        self.status_var.set(f"发现 {len(match)} 个活跃端口")

    def on_search(self, e=None):
        if hasattr(self, '_sj'): self.root.after_cancel(self._sj)
        self._sj = self.root.after(300, self._exec_filter)

    def _get_selected_pids(self):
        pids = [self.tree.item(i, "values")[1] for i in self.tree.selection()]
        if not pids and self.pid_entry.get(): pids = [self.pid_entry.get().strip()]
        return list(set(pids))

    def extract_pid_manual(self):
        pids = self._get_selected_pids()
        if pids:
            self.pid_entry.delete(0, tk.END)
            self.pid_entry.insert(0, pids[0])
            self.update_status(f"已提取 PID: {pids[0]}")
        else:
            messagebox.showinfo("提示", "请先在表格中选中一行")

    def kill_by_pid(self):
        targets = self._get_selected_pids()
        if not targets or not messagebox.askyesno("终止进程", f"确定终止选中的 {len(targets)} 个进程吗？"): return
        for pid in targets:
            try: 
                p = psutil.Process(int(pid))
                n = p.name()
                p.kill()
                self.log_message(f"成功终止: {n} (PID: {pid})", "success")
            except Exception as e: self.log_message(f"终止失败 {pid}: {e}", "error")
        self.root.after(1500, self.refresh_all)

    def restart_process(self):
        targets = self._get_selected_pids()
        if not targets or not messagebox.askyesno("重启服务", f"确定重启选中的 {len(targets)} 个服务吗？"): return
        for pid in targets:
            try:
                p = psutil.Process(int(pid))
                cmd, cwd, name = p.cmdline(), p.cwd(), p.name()
                p.kill()
                time.sleep(0.5)
                subprocess.Popen(cmd, cwd=cwd, creationflags=subprocess.CREATE_NEW_CONSOLE)
                self.log_message(f"已重启服务: {name}", "success")
            except Exception as e: self.log_message(f"重启失败 {pid}: {e}", "error")
        self.root.after(2000, self.refresh_all)

    def start_monitoring(self):
        p = self.port_var.get().strip()
        try:
            tp = int(p.split(',')[0]) # 取第一个
            self.monitoring_active = True
            self.monitor_status_label.config(text=f"Live: {tp}", fg=self.colors['success'])
            self.start_monitor_btn.config(state="disabled"); self.stop_monitor_btn.config(state="normal")
            self.log_message(f"正在监控端口 {tp} 的异常连接...")
            threading.Thread(target=self._monitor_loop, args=(tp,), daemon=True).start()
        except: messagebox.showerror("错误", "监控需输入单个端口号")

    def _monitor_loop(self, port):
        while self.monitoring_active:
            try:
                for c in psutil.net_connections():
                    if c.laddr.port == port:
                        r = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "Local"
                        msg = f"检测到连接: {r} -> PID {c.pid} [{c.status}]"
                        self.root.after(0, lambda m=msg: self.log_message(m, "warning"))
            except: pass
            time.sleep(MONITOR_INTERVAL)

    def stop_monitoring(self):
        self.monitoring_active = False
        self.monitor_status_label.config(text="Idle", fg=self.colors['text_tertiary'])
        self.start_monitor_btn.config(state="normal"); self.stop_monitor_btn.config(state="disabled")

    def on_tree_select(self, e):
        sel = self.tree.selection()
        if not sel: return
        v = self.tree.item(sel[0], "values")
        self.pid_entry.delete(0, tk.END); self.pid_entry.insert(0, v[1])

    def show_context_menu(self, e):
        i = self.tree.identify_row(e.y)
        if not i: return
        self.tree.selection_set(i)
        v = self.tree.item(i, "values")
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="🚀 重启此服务", command=self.restart_process)
        m.add_command(label="🛑 终止此进程", command=self.kill_by_pid, foreground="red")
        m.add_separator()
        m.add_command(label="🔍 监控此端口", command=lambda: [self.port_var.set(v[0]), self.start_monitoring()])
        m.add_command(label="📊 性能详情", command=self.show_process_details_dialog)
        m.add_separator()
        m.add_command(label="📋 复制 PID", command=lambda: [self.root.clipboard_clear(), self.root.clipboard_append(v[1])])
        m.add_command(label="📋 复制端口", command=lambda: [self.root.clipboard_clear(), self.root.clipboard_append(v[0])])
        m.post(e.x_root, e.y_root)

    def copy_pid(self):
        """将当前输入的 PID 复制到剪贴板"""
        pid = self.pid_entry.get().strip()
        if pid:
            self.root.clipboard_clear()
            self.root.clipboard_append(pid)
            self.log_message(f"PID {pid} 已成功复制到剪贴板", "success")
            self.status_var.set(f"已复制 PID: {pid}")
        else:
            messagebox.showinfo("提示", "当前没有可复制的 PID")

    def show_process_details_dialog(self):
        pid_s = self.pid_entry.get().strip()
        if not pid_s: return
        try:
            pid = int(pid_s)
            p = psutil.Process(pid)
            d = tk.Toplevel(self.root); d.title(f"PID {pid} 详情"); d.geometry("500x600"); d.configure(bg='white')
            tk.Label(d, text="进程实时指标", font=self.fonts['h1'], bg='white', fg=self.colors['primary']).pack(pady=20)
            f = tk.Frame(d, bg='white', padx=30); f.pack(fill="both")
            items = [("进程名", p.name()), ("状态", p.status()), ("CPU", f"{p.cpu_percent(0.1)}%"), 
                     ("内存", f"{p.memory_info().rss/1024/1024:.2f} MB"), ("路径", p.exe()), ("命令", " ".join(p.cmdline()))]
            for l, v in items:
                r = tk.Frame(f, bg='white', pady=5); r.pack(fill="x")
                tk.Label(r, text=f"{l}:", font=self.fonts['h2'], bg='white', width=10, anchor="w").pack(side="left")
                tk.Label(r, text=v, font=self.fonts['body'], bg='white', wraplength=350, justify="left").pack(side="left")
            tk.Button(d, text="关闭", command=d.destroy, bg=self.colors['primary'], fg='white', relief="flat", padx=30, pady=8).pack(pady=20)
        except: messagebox.showerror("错误", "无法访问该进程")

    def sort_tree(self, col, rev):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try: l.sort(key=lambda t: int(t[0]) if t[0].isdigit() else t[0], reverse=rev)
        except: l.sort(reverse=rev)
        for i, (v, k) in enumerate(l): self.tree.move(k, '', i)
        self.tree.heading(col, command=lambda: self.sort_tree(col, not rev))

    def load_port_history(self):
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r') as f: return json.load(f)
        except: pass
        return []

    def add_to_history(self, p):
        if not p or p in self.port_history: return
        self.port_history.insert(0, p); self.port_history = self.port_history[:MAX_HISTORY]
        try:
            with open(self.history_file, 'w') as f: json.dump(self.port_history, f)
            self.port_entry['values'] = self.port_history
        except: pass

    def export_results(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if not path: return
        with open(path, 'w', encoding='utf-8') as f:
            for i in self.tree.get_children(): f.write(str(self.tree.item(i, "values")) + "\n")
        messagebox.showinfo("成功", "数据已成功导出")

    def show_shortcuts(self): messagebox.showinfo("快捷键说明", "F5: 刷新列表\nCtrl+F: 快速搜索\nDouble Click: 查看进程详情\nRight Click: 快捷管理菜单")
    def show_about(self): messagebox.showinfo("关于 NetGuard", "NetGuard Pro v3.5\n由 Gemini AI 深度优化\n打造最流畅的 Windows 端口管理体验")
    def update_status(self, s): self.status_var.set(s)
    def _get_proc_cached(self, pid):
        now = time.time()
        if pid in self._process_cache:
            e = self._process_cache[pid]
            if now - e['t'] < self._cache_ttl: return e['d']
        try:
            p = psutil.Process(int(pid)); d = {'name': p.name()}
        except: d = {'name': '[Unknown]'}
        self._process_cache[pid] = {'d': d, 't': now}; return d
    def on_closing(self): self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk(); app = PortManagerGUI(root); root.mainloop()