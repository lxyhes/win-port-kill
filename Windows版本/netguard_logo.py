#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NetGuard 品牌 Logo 生成器
科技风格 + 蓝色系 + 网络端口元素
"""

import tkinter as tk
from tkinter import Canvas, PhotoImage
import math

class NetGuardLogo:
    def __init__(self, master, size=300):
        self.master = master
        self.size = size
        self.center = size // 2
        
        # NetGuard 品牌色 - 科技蓝
        self.colors = {
            'primary': '#007AFF',      # 苹果蓝
            'secondary': '#00C6FF',    # 亮蓝
            'accent': '#5856D6',       # 紫蓝
            'dark': '#1C1C1E',         # 深色
            'light': '#F2F2F7',        # 浅色
            'gradient_start': '#007AFF',
            'gradient_end': '#00C6FF'
        }
        
        self.canvas = Canvas(master, width=size, height=size, 
                            bg='white', highlightthickness=0)
        self.canvas.pack()
        
    def draw_logo(self):
        """绘制 NetGuard Logo"""
        size = self.size
        center = self.center
        
        # 1. 绘制外圈 - 盾牌形状
        shield_points = self._get_shield_points(center, size * 0.4)
        self.canvas.create_polygon(shield_points, 
                                   fill=self.colors['primary'],
                                   outline=self.colors['secondary'],
                                   width=3)
        
        # 2. 绘制内圈 - 科技感圆环
        self._draw_tech_ring(center, size * 0.32)
        
        # 3. 绘制端口符号 - 中心元素
        self._draw_port_symbol(center, size * 0.15)
        
        # 4. 绘制网络连接线
        self._draw_network_lines(center, size * 0.35)
        
        # 5. 添加发光效果
        self._draw_glow_effect(center, size * 0.45)
        
    def _get_shield_points(self, center, radius):
        """获取盾牌形状的点坐标"""
        points = []
        # 上半部分 - 弧形
        for angle in range(180, 361, 10):
            rad = math.radians(angle)
            x = center + radius * 0.8 * math.cos(rad)
            y = center - radius * 0.6 + radius * 0.6 * math.sin(rad)
            points.extend([x, y])
        
        # 底部尖端
        points.extend([center, center + radius * 0.9])
        
        # 右半边
        for angle in range(0, 181, 10):
            rad = math.radians(angle)
            x = center + radius * 0.8 * math.cos(rad)
            y = center - radius * 0.6 + radius * 0.6 * math.sin(rad)
            points.extend([x, y])
            
        return points
    
    def _draw_tech_ring(self, center, radius):
        """绘制科技感圆环"""
        # 外环
        self.canvas.create_oval(center - radius, center - radius,
                               center + radius, center + radius,
                               outline=self.colors['secondary'],
                               width=2)
        
        # 内环
        inner_radius = radius * 0.75
        self.canvas.create_oval(center - inner_radius, center - inner_radius,
                               center + inner_radius, center + inner_radius,
                               outline=self.colors['accent'],
                               width=2)
        
        # 科技刻度
        for i in range(12):
            angle = math.radians(i * 30)
            x1 = center + inner_radius * 0.85 * math.cos(angle)
            y1 = center + inner_radius * 0.85 * math.sin(angle)
            x2 = center + radius * 0.95 * math.cos(angle)
            y2 = center + radius * 0.95 * math.sin(angle)
            self.canvas.create_line(x1, y1, x2, y2, 
                                   fill=self.colors['secondary'], width=2)
    
    def _draw_port_symbol(self, center, size):
        """绘制端口符号"""
        # 端口矩形
        rect_size = size
        self.canvas.create_rectangle(center - rect_size, center - rect_size * 0.6,
                                    center + rect_size, center + rect_size * 0.6,
                                    fill=self.colors['light'],
                                    outline=self.colors['dark'],
                                    width=2)
        
        # 端口针脚
        pin_width = rect_size * 0.15
        pin_height = rect_size * 0.4
        pin_spacing = rect_size * 0.35
        
        for i in range(-1, 2):
            x = center + i * pin_spacing
            y = center + rect_size * 0.1
            self.canvas.create_rectangle(x - pin_width/2, y - pin_height/2,
                                        x + pin_width/2, y + pin_height/2,
                                        fill=self.colors['accent'],
                                        outline=self.colors['dark'])
        
        # 端口编号
        self.canvas.create_text(center, center - rect_size * 0.9,
                               text="://", fill=self.colors['secondary'],
                               font=('Consolas', int(size * 0.4), 'bold'))
    
    def _draw_network_lines(self, center, radius):
        """绘制网络连接线"""
        # 从中心向外辐射的线条
        for i in range(8):
            angle = math.radians(i * 45 + 22.5)
            x1 = center + radius * 0.5 * math.cos(angle)
            y1 = center + radius * 0.5 * math.sin(angle)
            x2 = center + radius * 0.9 * math.cos(angle)
            y2 = center + radius * 0.9 * math.sin(angle)
            
            self.canvas.create_line(x1, y1, x2, y2,
                                   fill=self.colors['secondary'],
                                   width=1, dash=(3, 3))
            
            # 节点点
            self.canvas.create_oval(x2 - 3, y2 - 3, x2 + 3, y2 + 3,
                                   fill=self.colors['accent'],
                                   outline='')
    
    def _draw_glow_effect(self, center, radius):
        """绘制发光效果"""
        # 外发光圈
        for i in range(3):
            r = radius + i * 8
            alpha = 30 - i * 10
            color = self._hex_to_rgb(self.colors['secondary'], alpha)
            self.canvas.create_oval(center - r, center - r,
                                   center + r, center + r,
                                   outline=color, width=1)
    
    def _hex_to_rgb(self, hex_color, alpha=255):
        """将十六进制颜色转换为RGB格式"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f'#{r:02x}{g:02x}{b:02x}'


def create_logo_variations():
    """创建不同尺寸的logo变体"""
    root = tk.Tk()
    root.title("NetGuard Logo 设计")
    root.configure(bg='white')
    
    # 标题
    title = tk.Label(root, text="NetGuard 品牌 Logo", 
                    font=('SF Pro Display', 24, 'bold'),
                    bg='white', fg='#1C1C1E')
    title.pack(pady=20)
    
    # 副标题
    subtitle = tk.Label(root, text="网络端口管理工具 | 科技蓝配色", 
                       font=('SF Pro Text', 12),
                       bg='white', fg='#8E8E93')
    subtitle.pack(pady=(0, 20))
    
    # Logo 展示区域
    frame = tk.Frame(root, bg='white')
    frame.pack(pady=20)
    
    # 大尺寸 Logo (300x300)
    large_label = tk.Label(frame, text="大尺寸 (300x300)", 
                          font=('SF Pro Text', 10),
                          bg='white', fg='#8E8E93')
    large_label.pack()
    
    logo_large = NetGuardLogo(frame, size=300)
    logo_large.draw_logo()
    
    # 分隔
    tk.Frame(root, height=2, bg='#E5E5EA').pack(fill='x', padx=40, pady=20)
    
    # 小尺寸展示
    sizes_frame = tk.Frame(root, bg='white')
    sizes_frame.pack(pady=10)
    
    sizes = [
        ("应用图标 (128x128)", 128),
        ("任务栏图标 (64x64)", 64),
        ("小图标 (32x32)", 32)
    ]
    
    for label_text, size in sizes:
        container = tk.Frame(sizes_frame, bg='white')
        container.pack(side='left', padx=20)
        
        lbl = tk.Label(container, text=label_text,
                      font=('SF Pro Text', 9),
                      bg='white', fg='#8E8E93')
        lbl.pack()
        
        logo = NetGuardLogo(container, size=size)
        logo.draw_logo()
    
    # 品牌信息
    info_frame = tk.Frame(root, bg='#F2F2F7', padx=40, pady=20)
    info_frame.pack(fill='x', padx=40, pady=20)
    
    info_text = """
品牌名称: NetGuard
品牌口号: 守护网络端口安全
主色调: #007AFF (科技蓝)
辅助色: #00C6FF (亮蓝) | #5856D6 (紫蓝)
设计理念: 盾牌 + 端口符号 + 网络节点
"""
    info_label = tk.Label(info_frame, text=info_text,
                         font=('SF Pro Text', 11),
                         bg='#F2F2F7', fg='#1C1C1E',
                         justify='left')
    info_label.pack()
    
    root.mainloop()


if __name__ == '__main__':
    create_logo_variations()
