"""
GUI界面模块 - 现代化C盘清理工具图形界面
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
from typing import List, Dict
from pathlib import Path

from utils import (
    is_admin, get_size, format_size, safe_delete,
    get_drive_free_space, get_drive_total_space
)
from cleaner_core import CleanerCore
from scanner import FileScanner
from backup_manager import BackupManager


class ModernButton(tk.Canvas):
    """现代化圆角按钮"""
    def __init__(self, parent, text, command=None, width=140, height=38,
                 color="#2196F3", hover_color="#1976D2", text_color="white",
                 font_size=11, **kwargs):
        super().__init__(parent, width=width, height=height,
                        highlightthickness=0, bg=parent.cget("bg"), **kwargs)
        self.command = command
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.font_size = font_size
        self.width = width
        self.height = height
        self._enabled = True
        self.bind("<Enter>", lambda e: self._draw(self.hover_color) if self._enabled else None)
        self.bind("<Leave>", lambda e: self._draw(self.color) if self._enabled else None)
        self.bind("<Button-1>", lambda e: self.command() if self._enabled and self.command else None)
        self._draw(self.color)

    def _draw(self, color):
        self.delete("all")
        r, w, h = 8, self.width, self.height
        pts = [r,0, w-r,0, w,0, w,r, w,h-r, w,h, w-r,h, r,h, 0,h, 0,h-r, 0,r, 0,0]
        self.create_polygon(pts, smooth=True, fill=color, outline="")
        self.create_text(w//2, h//2, text=self.text, fill=self.text_color,
                        font=("Microsoft YaHei", self.font_size, "bold"))

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        self._draw(self.color if enabled else "#BDBDBD")


class ModernCheckbox(tk.Frame):
    """现代化复选框"""
    def __init__(self, parent, text, desc="", variable=None, **kwargs):
        super().__init__(parent, bg="#ffffff", highlightbackground="#e8e8e8",
                        highlightthickness=1, **kwargs)
        self.var = variable if variable else tk.BooleanVar(value=True)
        # 跟踪点击状态，防止重复触发
        self._clicking = False
        self.check_cv = tk.Canvas(self, width=28, height=28, highlightthickness=0, bg="#ffffff")
        self.check_cv.pack(side=tk.LEFT, padx=(14, 10), pady=14)
        self._draw_check()
        # 只在顶层Frame绑定点击事件，子组件不再单独绑定
        self.bind("<Button-1>", self._on_click)
        # 让canvas也触发父级的点击
        self.check_cv.bind("<Button-1>", self._on_click)
        tf = tk.Frame(self, bg="#ffffff")
        tf.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=12)
        tk.Label(tf, text=text, font=("Microsoft YaHei", 10, "bold"),
                bg="#ffffff", fg="#333333", anchor=tk.W).pack(fill=tk.X)
        if desc:
            tk.Label(tf, text=desc, font=("Microsoft YaHei", 8),
                    bg="#ffffff", fg="#999999", anchor=tk.W).pack(fill=tk.X)
        # 文本区域的点击也触发切换
        tf.bind("<Button-1>", self._on_click)
        # 监听变量变化，自动更新UI（支持外部调用 set() 修改）
        self.var.trace_add("write", lambda *args: self._draw_check())

    def _on_click(self, event=None):
        """统一点击处理，防止重复触发"""
        if self._clicking:
            return
        self._clicking = True
        self.var.set(not self.var.get())
        self.after(100, self._reset_click_flag)

    def _reset_click_flag(self):
        self._clicking = False

    def _draw_check(self):
        self.check_cv.delete("all")
        if self.var.get():
            pts = [2,2, 26,2, 26,2, 26,2, 26,26, 2,26, 2,26, 2,2]
            self.check_cv.create_polygon(pts, smooth=True, fill="#2196F3", outline="")
            self.check_cv.create_line(8,14, 12,18, 20,9, fill="white", width=2.5,
                                     capstyle=tk.ROUND, joinstyle=tk.ROUND)
        else:
            pts = [2,2, 26,2, 26,2, 26,2, 26,26, 2,26, 2,26, 2,2]
            self.check_cv.create_polygon(pts, smooth=True, fill="white", outline="#CCCCCC")


class CategoryCard(tk.Frame):
    """统计卡片"""
    def __init__(self, parent, icon, title, value, color="#2196F3", **kwargs):
        super().__init__(parent, bg="#ffffff", highlightbackground="#e8e8e8",
                        highlightthickness=1, **kwargs)
        tk.Frame(self, bg=color, width=4).pack(side=tk.LEFT, fill=tk.Y)
        ct = tk.Frame(self, bg="#ffffff", padx=15, pady=12)
        ct.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        hd = tk.Frame(ct, bg="#ffffff")
        hd.pack(fill=tk.X)
        tk.Label(hd, text=icon, font=("Segoe UI Emoji", 16), bg="#ffffff").pack(side=tk.LEFT, padx=(0,8))
        tk.Label(hd, text=title, font=("Microsoft YaHei", 9), bg="#ffffff", fg="#666666").pack(side=tk.LEFT)
        self.vl = tk.Label(ct, text=value, font=("Microsoft YaHei", 16, "bold"),
                          bg="#ffffff", fg=color, anchor=tk.W)
        self.vl.pack(fill=tk.X, pady=(4,0))

    def update_value(self, v):
        self.vl.config(text=v)


class CCleanerApp:
    """C盘清理工具主界面"""
    COLORS = {
        "bg": "#f5f6fa", "card_bg": "#ffffff",
        "primary": "#2196F3", "primary_dark": "#1565C0",
        "success": "#4CAF50", "warning": "#FF9800",
        "danger": "#f44336", "dark": "#2c3e50",
        "text": "#2c3e50", "text_secondary": "#7f8c8d", "border": "#e8e8e8",
    }

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("C盘清理大师 v2.0")
        self.root.geometry("1050x750")
        self.root.minsize(900, 650)
        self.root.configure(bg=self.COLORS["bg"])
        try:
            self.root.iconbitmap(default="")
        except:
            pass

        self.backup_manager = BackupManager()
        self.cleaner_core = CleanerCore(progress_callback=self._on_progress)
        self.scanner = FileScanner(progress_callback=self._on_progress)
        self.is_running = False
        self.large_files = []
        self.duplicate_files = {}
        self.clean_vars = {}

        self._build_ui()
        self._update_disk_info()
        self._check_admin_status()

    def _build_ui(self):
        # 顶部导航
        hdr = tk.Frame(self.root, bg=self.COLORS["primary"], height=56)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Frame(hdr, bg=self.COLORS["primary_dark"], width=200, height=56).pack(side=tk.LEFT)
        tf = tk.Frame(hdr, bg=self.COLORS["primary"])
        tf.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(tf, text="🧹  C盘清理大师", font=("Microsoft YaHei", 17, "bold"),
                bg=self.COLORS["primary"], fg="white").pack(side=tk.LEFT)
        tk.Label(tf, text="v2.0", font=("Microsoft YaHei", 9),
                bg=self.COLORS["primary"], fg="#BBDEFB").pack(side=tk.LEFT, padx=(8,0), pady=(6,0))
        self.admin_indicator = tk.Label(hdr, text="", font=("Microsoft YaHei", 9),
                                       bg=self.COLORS["primary"], fg="#FFEB3B")
        self.admin_indicator.place(relx=0.95, rely=0.5, anchor="e")

        # 主区域
        main = tk.Frame(self.root, bg=self.COLORS["bg"])
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 5))
        self._build_sidebar(main)
        self.content_frame = tk.Frame(main, bg=self.COLORS["bg"])
        self.content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 状态栏
        sbar = tk.Frame(self.root, bg=self.COLORS["dark"], height=30)
        sbar.pack(fill=tk.X, side=tk.BOTTOM)
        sbar.pack_propagate(False)
        self.status_label = tk.Label(sbar, text="✨ 就绪", font=("Microsoft YaHei", 9),
                                    bg=self.COLORS["dark"], fg="white", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, padx=12, fill=tk.X, expand=True)
        self.status_right = tk.Label(sbar, text="", font=("Microsoft YaHei", 9),
                                    bg=self.COLORS["dark"], fg="#90CAF9", anchor=tk.E)
        self.status_right.pack(side=tk.RIGHT, padx=12)

        self._show_home()

    def _build_sidebar(self, parent):
        sb = tk.Frame(parent, bg=self.COLORS["card_bg"], width=200,
                     highlightbackground=self.COLORS["border"], highlightthickness=1)
        sb.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        sb.pack_propagate(False)

        dc = tk.Frame(sb, bg=self.COLORS["card_bg"], padx=15, pady=15)
        dc.pack(fill=tk.X)
        tk.Label(dc, text="💾 磁盘状态", font=("Microsoft YaHei", 11, "bold"),
                bg=self.COLORS["card_bg"], fg=self.COLORS["dark"]).pack(anchor=tk.W)
        tk.Frame(dc, bg=self.COLORS["border"], height=1).pack(fill=tk.X, pady=8)
        self.disk_progress_bar = ttk.Progressbar(dc, length=170, mode="determinate")
        self.disk_progress_bar.pack(pady=(5,5))
        self.disk_percent_label = tk.Label(dc, text="", font=("Microsoft YaHei", 20, "bold"),
                                          bg=self.COLORS["card_bg"], fg=self.COLORS["primary"])
        self.disk_percent_label.pack()
        self.disk_space_label = tk.Label(dc, text="正在获取...", font=("Microsoft YaHei", 8),
                                        bg=self.COLORS["card_bg"], fg=self.COLORS["text_secondary"],
                                        wraplength=170)
        self.disk_space_label.pack(pady=(5,0))
        tk.Frame(sb, bg=self.COLORS["border"], height=1).pack(fill=tk.X, padx=15, pady=10)

        navs = [
            ("🏠", "首页概览", self._show_home),
            ("🧹", "系统清理", self._show_clean),
            ("🔍", "大文件扫描", self._show_scan),
            ("📋", "重复文件", self._show_duplicate),
            ("📦", "备份管理", self._show_backup),
        ]
        self.nav_buttons = []
        for icon, text, cmd in navs:
            btn = tk.Label(sb, text=f"  {icon}  {text}", font=("Microsoft YaHei", 10),
                          bg=self.COLORS["card_bg"], fg=self.COLORS["text"],
                          padx=15, pady=10, anchor=tk.W, cursor="hand2")
            btn.pack(fill=tk.X, padx=10, pady=1)
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg="#f0f0f0", fg=self.COLORS["primary"]))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=self.COLORS["card_bg"], fg=self.COLORS["text"]))
            btn.bind("<Button-1>", lambda e, c=cmd: c())
            self.nav_buttons.append(btn)
        tk.Label(sb, text="C盘清理大师 v2.0", font=("Microsoft YaHei", 8),
                bg=self.COLORS["card_bg"], fg=self.COLORS["text_secondary"]).pack(side=tk.BOTTOM, pady=10)

    def _clear_content(self):
        for w in self.content_frame.winfo_children():
            w.destroy()

    def _highlight_nav(self, idx):
        for i, btn in enumerate(self.nav_buttons):
            btn.configure(bg="#e3f2fd" if i == idx else self.COLORS["card_bg"],
                         fg=self.COLORS["primary"] if i == idx else self.COLORS["text"])

    def _reset_buttons(self):
        """重置当前页面的所有按钮状态（页面切换时调用，防止按钮卡死）"""
        btn_names = ["clean_btn", "scan_btn", "dup_scan_btn",
                     "btn_analyze", "btn_clean_all"]
        for name in btn_names:
            btn = getattr(self, name, None)
            if btn is not None:
                try:
                    btn.set_enabled(not self.is_running)
                except:
                    pass
        # 额外处理停止按钮
        for name in ["stop_scan_btn", "stop_dup_btn"]:
            btn = getattr(self, name, None)
            if btn is not None:
                try:
                    btn.set_enabled(False)
                except:
                    pass

    # ========== 首页 ==========
    def _show_home(self):
        self._clear_content()
        self._highlight_nav(0)
        c = tk.Frame(self.content_frame, bg=self.COLORS["bg"])
        c.pack(fill=tk.BOTH, expand=True)
        tk.Label(c, text="👋 欢迎使用 C盘清理大师", font=("Microsoft YaHei", 16, "bold"),
                bg=self.COLORS["bg"], fg=self.COLORS["dark"]).pack(anchor=tk.W, pady=(0,5))
        tk.Label(c, text="一键扫描 · 智能分析 · 安全清理 · 让C盘重获新生",
                font=("Microsoft YaHei", 9), bg=self.COLORS["bg"],
                fg=self.COLORS["text_secondary"]).pack(anchor=tk.W, pady=(0,15))

        sf = tk.Frame(c, bg=self.COLORS["bg"])
        sf.pack(fill=tk.X, pady=(0,15))
        self.card_temp = CategoryCard(sf, "📁", "可清理垃圾", "分析中...", color=self.COLORS["danger"])
        self.card_temp.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,8))
        self.card_large = CategoryCard(sf, "📄", "大文件(>50MB)", "分析中...", color=self.COLORS["warning"])
        self.card_large.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.card_dup = CategoryCard(sf, "📋", "重复文件", "分析中...", color=self.COLORS["primary"])
        self.card_dup.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.card_backup = CategoryCard(sf, "📦", "备份占用", "分析中...", color=self.COLORS["success"])
        self.card_backup.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8,0))

        # 进度条区域
        pf = tk.Frame(c, bg=self.COLORS["card_bg"], highlightbackground=self.COLORS["border"],
                     highlightthickness=1, padx=20, pady=10)
        pf.pack(fill=tk.X, pady=(0,10))
        self.home_progress = ttk.Progressbar(pf, length=900, mode="determinate")
        self.home_progress.pack(fill=tk.X)
        self.home_progress_label = tk.Label(pf, text="", font=("Microsoft YaHei", 8),
                                           bg=self.COLORS["card_bg"], fg=self.COLORS["text_secondary"])
        self.home_progress_label.pack(anchor=tk.W, pady=(2,0))
        self.home_progress_frame = pf  # 保存引用以便隐藏

        af = tk.Frame(c, bg=self.COLORS["card_bg"], highlightbackground=self.COLORS["border"],
                     highlightthickness=1, padx=20, pady=18)
        af.pack(fill=tk.X, pady=(0,15))
        tk.Label(af, text="⚡ 快速操作", font=("Microsoft YaHei", 12, "bold"),
                bg=self.COLORS["card_bg"], fg=self.COLORS["dark"]).pack(anchor=tk.W)
        tk.Frame(af, bg=self.COLORS["border"], height=1).pack(fill=tk.X, pady=10)
        br = tk.Frame(af, bg=self.COLORS["card_bg"])
        br.pack()
        self.btn_analyze = ModernButton(br, "🔍 一键扫描", command=self._start_quick_analyze,
                                       color="#2196F3", hover_color="#1565C0", width=160, height=42, font_size=11)
        self.btn_analyze.pack(side=tk.LEFT, padx=5)
        self.btn_clean_all = ModernButton(br, "🧹 一键清理", command=self._start_onekey_clean,
                                         color="#f44336", hover_color="#c62828", width=160, height=42, font_size=11)
        self.btn_clean_all.pack(side=tk.LEFT, padx=5)
        ModernButton(br, "📦 备份管理", command=self._show_backup,
                    color="#4CAF50", hover_color="#388E3C", width=160, height=42, font_size=11).pack(side=tk.LEFT, padx=5)

        sf2 = tk.Frame(c, bg=self.COLORS["card_bg"], highlightbackground=self.COLORS["border"],
                      highlightthickness=1, padx=20, pady=15)
        sf2.pack(fill=tk.BOTH, expand=True)
        tk.Label(sf2, text="💡 智能分析建议", font=("Microsoft YaHei", 12, "bold"),
                bg=self.COLORS["card_bg"], fg=self.COLORS["dark"]).pack(anchor=tk.W)
        tk.Frame(sf2, bg=self.COLORS["border"], height=1).pack(fill=tk.X, pady=8)
        self.suggest_text = scrolledtext.ScrolledText(sf2, font=("Microsoft YaHei", 9),
            bg="#fafafa", fg=self.COLORS["text"], relief=tk.FLAT, height=8, padx=10, pady=10, state=tk.DISABLED)
        self.suggest_text.pack(fill=tk.BOTH, expand=True)
        self._show_welcome_suggestions()
        self._reset_buttons()

    def _show_welcome_suggestions(self):
        self.suggest_text.config(state=tk.NORMAL)
        self.suggest_text.delete(1.0, tk.END)
        self.suggest_text.insert(tk.END, "📌 使用建议：\n\n")
        self.suggest_text.insert(tk.END, "1️⃣  点击「一键扫描」分析C盘空间使用情况\n")
        self.suggest_text.insert(tk.END, "2️⃣  查看分析结果，了解哪些文件占用了空间\n")
        self.suggest_text.insert(tk.END, "3️⃣  点击「一键清理」自动清理系统垃圾文件\n")
        self.suggest_text.insert(tk.END, "4️⃣  定期清理可保持C盘健康状态\n\n")
        self.suggest_text.insert(tk.END, "💡 提示：建议以管理员身份运行以获得最佳清理效果\n")
        self.suggest_text.insert(tk.END, "💡 提示：清理前会自动备份，可在「备份管理」中恢复\n")
        self.suggest_text.config(state=tk.DISABLED)

    # ========== 系统清理 ==========
    def _show_clean(self):
        self._clear_content()
        self._highlight_nav(1)
        c = tk.Frame(self.content_frame, bg=self.COLORS["bg"])
        c.pack(fill=tk.BOTH, expand=True)
        tk.Label(c, text="🧹 系统清理", font=("Microsoft YaHei", 16, "bold"),
                bg=self.COLORS["bg"], fg=self.COLORS["dark"]).pack(anchor=tk.W)
        tk.Label(c, text="选择要清理的项目，点击「开始清理」安全释放磁盘空间",
                font=("Microsoft YaHei", 9), bg=self.COLORS["bg"],
                fg=self.COLORS["text_secondary"]).pack(anchor=tk.W, pady=(0,12))
        main = tk.Frame(c, bg=self.COLORS["bg"])
        main.pack(fill=tk.BOTH, expand=True)
        left = tk.Frame(main, bg=self.COLORS["bg"])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,10))
        sf = tk.Frame(left, bg=self.COLORS["bg"])
        sf.pack(fill=tk.X, pady=(0,8))
        canvas = tk.Canvas(left, bg=self.COLORS["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(left, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=self.COLORS["bg"])
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)
        scrollable.bind("<Enter>", _bind_mousewheel)
        scrollable.bind("<Leave>", _unbind_mousewheel)
        items = [
            ("temp_files", "📁 临时文件", "清理Windows系统和用户临时文件夹"),
            ("recycle_bin", "🗑️ 回收站", "清空回收站中的所有文件"),
            ("browser_cache", "🌐 浏览器缓存", "清理Chrome、Edge、Firefox等浏览器缓存"),
            ("system_logs", "📋 系统日志", "清理Windows系统日志和调试文件"),
            ("windows_update", "🔄 更新缓存", "清理Windows更新下载缓存和旧组件"),
            ("prefetch", "⚡ 预取文件", "清理系统预取文件"),
            ("thumbnails", "🖼️ 缩略图缓存", "清理文件资源管理器缩略图缓存"),
            ("dns_cache", "🌍 DNS缓存", "刷新DNS解析缓存"),
            ("recent_files", "📄 最近文件记录", "清理最近使用的文件列表"),
        ]
        for key, label, desc in items:
            var = tk.BooleanVar(value=True)
            self.clean_vars[key] = var
            ModernCheckbox(scrollable, label, desc, variable=var).pack(fill=tk.X, pady=3)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        right = tk.Frame(main, bg=self.COLORS["bg"], width=380)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False)
        right.pack_propagate(False)
        ac = tk.Frame(right, bg=self.COLORS["card_bg"], highlightbackground=self.COLORS["border"],
                     highlightthickness=1, padx=15, pady=15)
        ac.pack(fill=tk.X)
        tk.Label(ac, text="⚡ 执行清理", font=("Microsoft YaHei", 11, "bold"),
                bg=self.COLORS["card_bg"], fg=self.COLORS["dark"]).pack(anchor=tk.W)
        tk.Frame(ac, bg=self.COLORS["border"], height=1).pack(fill=tk.X, pady=8)
        self.clean_btn = ModernButton(ac, "🚀 开始清理", command=self._start_cleaning,
                                     color="#f44336", hover_color="#c62828", width=200, height=42, font_size=12)
        self.clean_btn.pack(pady=5)
        lc = tk.Frame(right, bg=self.COLORS["card_bg"], highlightbackground=self.COLORS["border"],
                     highlightthickness=1, padx=15, pady=15)
        lc.pack(fill=tk.BOTH, expand=True, pady=(10,0))
        tk.Label(lc, text="📝 清理日志", font=("Microsoft YaHei", 11, "bold"),
                bg=self.COLORS["card_bg"], fg=self.COLORS["dark"]).pack(anchor=tk.W)
        tk.Frame(lc, bg=self.COLORS["border"], height=1).pack(fill=tk.X, pady=8)
        self.result_text = scrolledtext.ScrolledText(lc, font=("Consolas", 9),
            bg="#1e1e1e", fg="#d4d4d4", relief=tk.FLAT, height=15, state=tk.DISABLED)
        self._reset_buttons()

    # ========== 大文件扫描 ==========
    def _show_scan(self):
        self._clear_content()
        self._highlight_nav(2)
        c = tk.Frame(self.content_frame, bg=self.COLORS["bg"])
        c.pack(fill=tk.BOTH, expand=True)
        tk.Label(c, text="🔍 大文件扫描", font=("Microsoft YaHei", 16, "bold"),
                bg=self.COLORS["bg"], fg=self.COLORS["dark"]).pack(anchor=tk.W)
        tk.Label(c, text="扫描C盘中的大文件，帮助您找到可以清理或迁移的文件",
                font=("Microsoft YaHei", 9), bg=self.COLORS["bg"],
                fg=self.COLORS["text_secondary"]).pack(anchor=tk.W, pady=(0,12))
        sc = tk.Frame(c, bg=self.COLORS["card_bg"], highlightbackground=self.COLORS["border"],
                     highlightthickness=1, padx=15, pady=12)
        sc.pack(fill=tk.X, pady=(0,10))
        tk.Label(sc, text="⚙️ 扫描设置", font=("Microsoft YaHei", 10, "bold"),
                bg=self.COLORS["card_bg"], fg=self.COLORS["dark"]).pack(anchor=tk.W)
        sr = tk.Frame(sc, bg=self.COLORS["card_bg"])
        sr.pack(fill=tk.X, pady=(8,0))
        tk.Label(sr, text="最小文件大小:", font=("Microsoft YaHei", 9),
                bg=self.COLORS["card_bg"]).pack(side=tk.LEFT, padx=(0,5))
        self.min_size_var = tk.StringVar(value="50")
        sp = tk.Spinbox(sr, from_=10, to=1000, increment=10, textvariable=self.min_size_var,
                       width=6, font=("Microsoft YaHei", 9), relief=tk.GROOVE, bd=1)
        sp.pack(side=tk.LEFT, padx=5)
        tk.Label(sr, text="MB", font=("Microsoft YaHei", 9),
                bg=self.COLORS["card_bg"]).pack(side=tk.LEFT, padx=(0,20))
        self.scan_btn = ModernButton(sr, "🔍 开始扫描", command=self._start_scan,
                                    color="#2196F3", hover_color="#1565C0", width=130, height=34, font_size=10)
        self.scan_btn.pack(side=tk.LEFT, padx=5)
        self.stop_scan_btn = ModernButton(sr, "⏹ 停止", command=self._stop_scan,
                                         color="#9E9E9E", hover_color="#757575", width=90, height=34, font_size=10)
        self.stop_scan_btn.pack(side=tk.LEFT, padx=5)
        self.stop_scan_btn.set_enabled(False)
        tc = tk.Frame(c, bg=self.COLORS["card_bg"], highlightbackground=self.COLORS["border"],
                     highlightthickness=1, padx=15, pady=12)
        tc.pack(fill=tk.BOTH, expand=True)
        ir = tk.Frame(tc, bg=self.COLORS["card_bg"])
        ir.pack(fill=tk.X, pady=(0,8))
        tk.Label(ir, text="📊 扫描结果", font=("Microsoft YaHei", 10, "bold"),
                bg=self.COLORS["card_bg"], fg=self.COLORS["dark"]).pack(side=tk.LEFT)
        self.scan_info_label = tk.Label(ir, text="", font=("Microsoft YaHei", 9),
                                       bg=self.COLORS["card_bg"], fg=self.COLORS["text_secondary"])
        self.scan_info_label.pack(side=tk.RIGHT)
        cols = ("name", "size", "path")
        self.scan_tree = ttk.Treeview(tc, columns=cols, show="headings", height=12)
        self.scan_tree.heading("name", text="文件名")
        self.scan_tree.heading("size", text="大小")
        self.scan_tree.heading("path", text="完整路径")
        self.scan_tree.column("name", width=200, minwidth=150)
        self.scan_tree.column("size", width=100, minwidth=80, anchor=tk.E)
        self.scan_tree.column("path", width=500, minwidth=300)
        ts = ttk.Scrollbar(tc, orient="vertical", command=self.scan_tree.yview)
        self.scan_tree.configure(yscrollcommand=ts.set)
        self.scan_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ts.pack(side=tk.RIGHT, fill=tk.Y)
        # 如果已有扫描结果，直接显示
        if self.large_files:
            self._update_scan_results()
        self._reset_buttons()

    # ========== 重复文件 ==========
    def _show_duplicate(self):
        self._clear_content()
        self._highlight_nav(3)
        c = tk.Frame(self.content_frame, bg=self.COLORS["bg"])
        c.pack(fill=tk.BOTH, expand=True)
        tk.Label(c, text="📋 重复文件检测", font=("Microsoft YaHei", 16, "bold"),
                bg=self.COLORS["bg"], fg=self.COLORS["dark"]).pack(anchor=tk.W)
        tk.Label(c, text="扫描C盘中的重复文件，删除重复文件可以释放大量磁盘空间",
                font=("Microsoft YaHei", 9), bg=self.COLORS["bg"],
                fg=self.COLORS["text_secondary"]).pack(anchor=tk.W, pady=(0,12))
        bf = tk.Frame(c, bg=self.COLORS["card_bg"], highlightbackground=self.COLORS["border"],
                     highlightthickness=1, padx=15, pady=12)
        bf.pack(fill=tk.X, pady=(0,10))
        self.dup_scan_btn = ModernButton(bf, "🔍 扫描重复文件", command=self._start_duplicate_scan,
                                        color="#2196F3", hover_color="#1565C0", width=150, height=36, font_size=10)
        self.dup_scan_btn.pack(side=tk.LEFT, padx=(0,10))
        self.stop_dup_btn = ModernButton(bf, "⏹ 停止", command=self._stop_scan,
                                        color="#9E9E9E", hover_color="#757575", width=90, height=36, font_size=10)
        self.stop_dup_btn.pack(side=tk.LEFT)
        self.stop_dup_btn.set_enabled(False)
        self.dup_info_label = tk.Label(bf, text="", font=("Microsoft YaHei", 9),
                                      bg=self.COLORS["card_bg"], fg=self.COLORS["text_secondary"])
        self.dup_info_label.pack(side=tk.RIGHT, padx=10)
        # 添加"删除重复文件"按钮
        self.dup_delete_btn = ModernButton(bf, "🗑️ 删除重复文件(保留一个)", command=self._start_dup_clean,
                                          color="#f44336", hover_color="#c62828", width=200, height=36, font_size=10)
        self.dup_delete_btn.pack(side=tk.LEFT, padx=(10,0))
        if not self.duplicate_files:
            self.dup_delete_btn.set_enabled(False)
        rf = tk.Frame(c, bg=self.COLORS["card_bg"], highlightbackground=self.COLORS["border"],
                     highlightthickness=1, padx=15, pady=12)
        rf.pack(fill=tk.BOTH, expand=True)
        tk.Label(rf, text="📊 扫描结果", font=("Microsoft YaHei", 10, "bold"),
                bg=self.COLORS["card_bg"], fg=self.COLORS["dark"]).pack(anchor=tk.W)
        tk.Frame(rf, bg=self.COLORS["border"], height=1).pack(fill=tk.X, pady=8)
        self.dup_text = scrolledtext.ScrolledText(rf, font=("Consolas", 9),
            bg="#1e1e1e", fg="#d4d4d4", relief=tk.FLAT, height=15, state=tk.DISABLED)
        self.dup_text.pack(fill=tk.BOTH, expand=True)
        # 如果已有扫描结果，直接显示
        if self.duplicate_files:
            self._update_duplicate_results()
        self._reset_buttons()

    # ========== 备份管理 ==========
    def _show_backup(self):
        self._clear_content()
        self._highlight_nav(4)
        c = tk.Frame(self.content_frame, bg=self.COLORS["bg"])
        c.pack(fill=tk.BOTH, expand=True)
        tk.Label(c, text="📦 备份管理", font=("Microsoft YaHei", 16, "bold"),
                bg=self.COLORS["bg"], fg=self.COLORS["dark"]).pack(anchor=tk.W)
        tk.Label(c, text="清理前会自动备份文件，您可以在需要时恢复或清理备份",
                font=("Microsoft YaHei", 9), bg=self.COLORS["bg"],
                fg=self.COLORS["text_secondary"]).pack(anchor=tk.W, pady=(0,15))
        ic = tk.Frame(c, bg=self.COLORS["card_bg"], highlightbackground=self.COLORS["border"],
                     highlightthickness=1, padx=20, pady=25)
        ic.pack(fill=tk.X, pady=(0,15))
        self.backup_info_label = tk.Label(ic, text="正在获取备份信息...",
                                         font=("Microsoft YaHei", 11),
                                         bg=self.COLORS["card_bg"], fg=self.COLORS["dark"])
        self.backup_info_label.pack()
        bf = tk.Frame(c, bg=self.COLORS["bg"])
        bf.pack(fill=tk.X)
        ModernButton(bf, "🔄 刷新信息", command=self._refresh_backup_info,
                    color="#2196F3", hover_color="#1565C0", width=130, height=36, font_size=10).pack(side=tk.LEFT, padx=(0,10))
        ModernButton(bf, "🗑️ 清理备份", command=self._clear_backup,
                    color="#FF9800", hover_color="#F57C00", width=130, height=36, font_size=10).pack(side=tk.LEFT)
        self._reset_buttons()

    # ========== 业务逻辑 ==========

    def _check_admin_status(self):
        if is_admin():
            self.admin_indicator.config(text="✅ 管理员模式")
        else:
            self.admin_indicator.config(text="⚠️ 建议以管理员运行")

    def _update_disk_info(self):
        try:
            free = get_drive_free_space("C:")
            total = get_drive_total_space("C:")
            used = total - free
            if total > 0:
                pct = (used / total) * 100
                self.disk_progress_bar["value"] = pct
                self.disk_percent_label.config(text=f"{pct:.1f}%")
                self.disk_space_label.config(
                    text=f"已用: {format_size(used)} / 共: {format_size(total)}\n可用: {format_size(free)}")
        except:
            self.disk_space_label.config(text="无法获取磁盘信息")

    def _select_all(self):
        for v in self.clean_vars.values():
            v.set(True)

    def _deselect_all(self):
        for v in self.clean_vars.values():
            v.set(False)

    def _on_progress(self, current, total, message):
        self.root.after(0, self._update_progress_ui, current, total, message)

    def _update_home_progress(self, current, total, message):
        """更新首页进度条"""
        if hasattr(self, 'home_progress'):
            self.home_progress["mode"] = "determinate"
            self.home_progress.stop()
            if total > 0:
                pct = (current / total) * 100
                self.home_progress["value"] = pct
            self.home_progress_label.config(text=message)

    def _update_progress_ui(self, current, total, message):
        self.status_label.config(text=message)
        if total > 0:
            self.disk_progress_bar["value"] = (current / total) * 100
        # 同时更新首页进度条
        if hasattr(self, 'home_progress'):
            if total > 0:
                self.home_progress["mode"] = "determinate"
                self.home_progress.stop()
                self.home_progress["value"] = (current / total) * 100
                self.home_progress_label.config(text=f"{message} ({current}/{total})")
            else:
                self.home_progress["mode"] = "indeterminate"
                self.home_progress.start(10)
                self.home_progress_label.config(text=message)

    def _log_result(self, text):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.insert(tk.END, text + "\n")
        self.result_text.see(tk.END)
        self.result_text.config(state=tk.DISABLED)

    def _log_dup(self, text):
        self.dup_text.config(state=tk.NORMAL)
        self.dup_text.insert(tk.END, text + "\n")
        self.dup_text.see(tk.END)
        self.dup_text.config(state=tk.DISABLED)

    def _set_running(self, running):
        self.is_running = running
        btn_names = ["clean_btn", "scan_btn", "dup_scan_btn",
                     "btn_analyze", "btn_clean_all"]
        for name in btn_names:
            btn = getattr(self, name, None)
            if btn is not None:
                try:
                    btn.set_enabled(not running)
                except:
                    pass
        # 如果操作结束（running=False），确保当前页面的按钮也同步状态
        # （防止后台线程完成时用户已切换到其他页面，旧按钮已销毁）
        if not running:
            self.root.after(100, self._reset_buttons)

    # ========== 一键扫描（智能分析） ==========

    def _start_quick_analyze(self):
        if self.is_running:
            return
        self._set_running(True)
        self.status_label.config(text="🔍 正在智能分析C盘...")
        # 重置卡片状态
        self.card_temp.update_value("分析中...")
        self.card_large.update_value("分析中...")
        self.card_dup.update_value("分析中...")
        self.card_backup.update_value("分析中...")
        # 显示进度条
        if hasattr(self, 'home_progress'):
            self.home_progress["value"] = 0
            self.home_progress["mode"] = "indeterminate"
            self.home_progress.start(10)
            self.home_progress_label.config(text="🔍 正在智能分析C盘...")
        self.suggest_text.config(state=tk.NORMAL)
        self.suggest_text.delete(1.0, tk.END)
        self.suggest_text.insert(tk.END, "🔍 正在分析C盘空间使用情况，请稍候...\n")
        self.suggest_text.config(state=tk.DISABLED)
        thread = threading.Thread(target=self._do_quick_analyze, daemon=True)
        thread.start()

    def _do_quick_analyze(self):
        try:
            # 分析1：磁盘空间
            self.root.after(0, lambda: self._update_home_progress(0, 4, "📊 正在获取磁盘信息..."))
            free = get_drive_free_space("C:")
            total = get_drive_total_space("C:")
            used = total - free
            used_pct = (used / total) * 100 if total > 0 else 0

            # 分析2：估算可清理垃圾（快速扫描临时文件）
            self.root.after(0, lambda: self._update_home_progress(1, 4, "📁 正在估算临时文件大小..."))
            temp_size = 0
            for p in [os.environ.get("TEMP",""), os.environ.get("TMP",""),
                      os.path.join(os.environ.get("WINDIR","C:\\Windows"), "Temp")]:
                if os.path.exists(p):
                    temp_size += get_size(p)
            self.root.after(0, lambda: self.card_temp.update_value(
                f"≈ {format_size(temp_size)}"))

            # 分析3：扫描大文件（快速模式 - 只扫用户目录，不扫全盘）
            self.root.after(0, lambda: self._update_home_progress(2, 4, "📄 正在快速扫描大文件..."))
            user_profile = os.environ.get("USERPROFILE", "C:\\Users")
            large_files = self.scanner.scan_large_files(
                root_path=user_profile, min_size_mb=100, max_results=30)
            total_large_size = sum(f["size"] for f in large_files)
            self.root.after(0, lambda: self.card_large.update_value(
                f"{len(large_files)} 个 ({format_size(total_large_size)})"))

            # 分析4：备份大小
            self.root.after(0, lambda: self._update_home_progress(3, 4, "📦 正在检查备份..."))
            backup_size = self.backup_manager.get_backup_size()
            self.root.after(0, lambda: self.card_backup.update_value(
                format_size(backup_size)))

            # 重复文件提示
            self.root.after(0, lambda: self.card_dup.update_value("点击扫描"))

            # 生成建议
            suggestions = []
            suggestions.append(f"📊 C盘使用情况：已用 {format_size(used)} / {format_size(total)} ({used_pct:.1f}%)\n")

            if used_pct > 90:
                suggestions.append("🔴 紧急：C盘使用率超过90%，建议立即清理！\n")
            elif used_pct > 75:
                suggestions.append("🟡 警告：C盘使用率超过75%，建议尽快清理\n")

            if temp_size > 500 * 1024 * 1024:
                suggestions.append(f"📁 临时文件占用 {format_size(temp_size)}，建议清理\n")
            if len(large_files) > 0:
                suggestions.append(f"📄 发现 {len(large_files)} 个大文件(>100MB)，共占用 {format_size(total_large_size)}\n")
                suggestions.append("   建议将个人大文件迁移到D盘或其他盘\n")
            if backup_size > 100 * 1024 * 1024:
                suggestions.append(f"📦 备份文件占用 {format_size(backup_size)}，可在备份管理中清理\n")

            suggestions.append("\n💡 推荐操作：")
            suggestions.append("1. 点击「一键清理」自动清理系统垃圾")
            suggestions.append("2. 在「大文件扫描」中查看并迁移大文件")
            suggestions.append("3. 定期清理保持C盘健康")

            self.root.after(0, lambda: self._update_suggestions("\n".join(suggestions)))
            self.root.after(0, lambda: self._update_home_progress(4, 4, f"✅ 分析完成！C盘使用率 {used_pct:.1f}%，可清理垃圾约 {format_size(temp_size)}"))
            self.root.after(0, lambda: self.status_label.config(
                text=f"✅ 分析完成！C盘使用率 {used_pct:.1f}%，可清理垃圾约 {format_size(temp_size)}"))

        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text=f"❌ 分析出错: {e}"))
            self.root.after(0, lambda: self._update_home_progress(0, 1, f"❌ 分析出错: {e}"))
        finally:
            self.root.after(0, lambda: self._set_running(False))

    def _update_suggestions(self, text):
        self.suggest_text.config(state=tk.NORMAL)
        self.suggest_text.delete(1.0, tk.END)
        self.suggest_text.insert(tk.END, text)
        self.suggest_text.config(state=tk.DISABLED)

    # ========== 一键清理 ==========

    def _start_onekey_clean(self):
        if self.is_running:
            return
        if not messagebox.askyesno("一键清理", "即将清理所有系统垃圾文件（临时文件、缓存、回收站等）\n清理前会自动备份，是否继续？", icon=messagebox.WARNING):
            return
        self._show_clean()
        # 全选所有项目
        self._select_all()
        self._start_cleaning()

    # ========== 系统清理执行 ==========

    def _start_cleaning(self):
        if self.is_running:
            return
        selected = [k for k, v in self.clean_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("提示", "请至少选择一个清理项目")
            return

        self._set_running(True)
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.config(state=tk.DISABLED)
        self._log_result("=" * 60)
        self._log_result(f"🕐 开始清理 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._log_result("=" * 60)
        thread = threading.Thread(target=self._do_cleaning, args=(selected,), daemon=True)
        thread.start()

    def _do_cleaning(self, selected):
        try:
            self._log_result("\n📦 正在创建备份...")
            results = self.cleaner_core.run_all_cleaners(selected)
            total_size = 0
            total_count = 0
            self._log_result("\n" + "=" * 60)
            self._log_result("📊 清理结果汇总")
            self._log_result("=" * 60)
            for r in results:
                name = r.get("name", "未知")
                size = r.get("size", 0)
                count = r.get("count", 0)
                ok = r.get("success", False)
                total_size += size
                total_count += count
                st = "✅" if ok else "❌"
                self._log_result(f"{st} {name}: 释放 {format_size(size)} ({count} 个文件)")
            self._log_result("\n" + "-" * 60)
            self._log_result(f"📈 总计释放: {format_size(total_size)}")
            self._log_result(f"📄 处理文件: {total_count} 个")
            self._log_result("-" * 60)
            self.root.after(0, self._update_disk_info)
            self.root.after(0, lambda: self.status_label.config(
                text=f"✅ 清理完成！共释放 {format_size(total_size)}"))
        except Exception as e:
            self._log_result(f"\n❌ 错误: {e}")
            self.root.after(0, lambda: self.status_label.config(text="❌ 清理出错"))
        finally:
            self.root.after(0, lambda: self._set_running(False))

    # ========== 大文件扫描执行 ==========

    def _start_scan(self):
        if self.is_running:
            return
        self._set_running(True)
        self.scan_btn.set_enabled(False)
        self.stop_scan_btn.set_enabled(True)
        for item in self.scan_tree.get_children():
            self.scan_tree.delete(item)
        self.scan_info_label.config(text="正在扫描...")
        self.status_label.config(text="🔍 正在扫描大文件，请稍候...")
        min_size = int(self.min_size_var.get())
        thread = threading.Thread(target=self._do_scan, args=(min_size,), daemon=True)
        thread.start()

    def _do_scan(self, min_size_mb):
        try:
            self.large_files = self.scanner.scan_large_files(
                root_path="C:\\", min_size_mb=min_size_mb, max_results=200)
            self.root.after(0, self._update_scan_results)
        except Exception as e:
            self.root.after(0, lambda: self.scan_info_label.config(text=f"出错: {e}"))
            self.root.after(0, lambda: self.status_label.config(text=f"❌ 扫描出错: {e}"))
        finally:
            self.root.after(0, lambda: self.stop_scan_btn.set_enabled(False))
            self.root.after(0, lambda: self._set_running(False))

    def _update_scan_results(self):
        for item in self.scan_tree.get_children():
            self.scan_tree.delete(item)
        for f in self.large_files:
            self.scan_tree.insert("", tk.END, values=(f["name"], f["size_str"], f["path"]))
        total_size = sum(f["size"] for f in self.large_files)
        self.scan_info_label.config(
            text=f"找到 {len(self.large_files)} 个大文件，总计 {format_size(total_size)}")
        self.status_label.config(text=f"扫描完成：{len(self.large_files)} 个大文件")

    def _stop_scan(self):
        self.scanner.stop()
        self.status_label.config(text="正在停止扫描...")

    # ========== 重复文件扫描执行 ==========

    def _start_duplicate_scan(self):
        if self.is_running:
            return
        self._set_running(True)
        self.dup_scan_btn.set_enabled(False)
        self.stop_dup_btn.set_enabled(True)
        self.dup_text.config(state=tk.NORMAL)
        self.dup_text.delete(1.0, tk.END)
        self.dup_text.config(state=tk.DISABLED)
        self._log_dup("=" * 60)
        self._log_dup(f"🕐 开始扫描重复文件 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._log_dup("=" * 60)
        self._log_dup("正在扫描，这可能需要一些时间...\n")
        self.status_label.config(text="🔍 正在扫描重复文件...")
        thread = threading.Thread(target=self._do_duplicate_scan, daemon=True)
        thread.start()

    def _do_duplicate_scan(self):
        try:
            self.duplicate_files = self.scanner.scan_duplicate_files(
                root_path="C:\\", min_size_kb=1024)
            self.root.after(0, self._update_duplicate_results)
        except Exception as e:
            self._log_dup(f"\n❌ 出错: {e}")
            self.root.after(0, lambda: self.status_label.config(text=f"❌ 重复文件扫描出错: {e}"))
        finally:
            self.root.after(0, lambda: self.stop_dup_btn.set_enabled(False))
            self.root.after(0, lambda: self._set_running(False))

    def _update_duplicate_results(self):
        total_dup_size = sum(
            sum(f["size"] for f in files[1:])
            for files in self.duplicate_files.values()
        )
        dup_count = sum(len(files) - 1 for files in self.duplicate_files.values())
        self._log_dup("\n" + "=" * 60)
        self._log_dup("📊 扫描结果")
        self._log_dup("=" * 60)
        self._log_dup(f"找到 {len(self.duplicate_files)} 组重复文件")
        self._log_dup(f"可释放空间: {format_size(total_dup_size)}")
        self._log_dup(f"重复文件数: {dup_count} 个\n")
        for h, files in list(self.duplicate_files.items())[:30]:
            self._log_dup(f"📄 重复组 (大小: {files[0]['size_str']}):")
            for f in files:
                self._log_dup(f"   📍 {f['path']}")
            self._log_dup("")
        if len(self.duplicate_files) > 30:
            self._log_dup(f"... 还有 {len(self.duplicate_files) - 30} 组未显示\n")
        self.dup_info_label.config(
            text=f"找到 {len(self.duplicate_files)} 组，可释放 {format_size(total_dup_size)}")
        self.status_label.config(
            text=f"重复文件扫描完成：{len(self.duplicate_files)} 组，可释放 {format_size(total_dup_size)}")
        # 启用删除按钮
        if hasattr(self, 'dup_delete_btn'):
            self.dup_delete_btn.set_enabled(True)

    # ========== 删除重复文件 ==========

    def _start_dup_clean(self):
        """开始删除重复文件（每组保留第一个）"""
        if self.is_running:
            return
        if not self.duplicate_files:
            messagebox.showinfo("提示", "请先扫描重复文件")
            return

        total_dup_size = sum(
            sum(f["size"] for f in files[1:])
            for files in self.duplicate_files.values()
        )
        dup_count = sum(len(files) - 1 for files in self.duplicate_files.values())

        if not messagebox.askyesno(
            "确认删除",
            f"将删除 {dup_count} 个重复文件，每组保留一个\n"
            f"预计释放空间: {format_size(total_dup_size)}\n\n"
            f"⚠️ 此操作不可撤销！建议先备份重要文件。\n"
            f"是否继续？",
            icon=messagebox.WARNING
        ):
            return

        self._set_running(True)
        if hasattr(self, 'dup_delete_btn'):
            self.dup_delete_btn.set_enabled(False)
        self._log_dup("\n" + "=" * 60)
        self._log_dup("🗑️ 开始删除重复文件...")
        self._log_dup("=" * 60)
        thread = threading.Thread(target=self._do_dup_clean, daemon=True)
        thread.start()

    def _do_dup_clean(self):
        """执行删除重复文件"""
        try:
            deleted_count = 0
            deleted_size = 0
            kept_groups = {}

            for file_hash, files in self.duplicate_files.items():
                if len(files) <= 1:
                    kept_groups[file_hash] = files
                    continue

                # 保留第一个文件，删除其余
                kept_file = files[0]
                deleted_files = files[1:]

                for f in deleted_files:
                    try:
                        size = f["size"]
                        if safe_delete(f["path"]):
                            deleted_count += 1
                            deleted_size += size
                            self._log_dup(f"  ✅ 已删除: {f['path']} ({f['size_str']})")
                        else:
                            self._log_dup(f"  ❌ 删除失败: {f['path']}")
                    except Exception as e:
                        self._log_dup(f"  ❌ 删除失败: {f['path']} - {e}")

                # 保留组信息（只保留第一个文件）
                kept_groups[file_hash] = [kept_file]

            # 更新数据
            self.duplicate_files = kept_groups

            self._log_dup("\n" + "-" * 60)
            self._log_dup(f"📊 删除完成！")
            self._log_dup(f"🗑️ 删除文件: {deleted_count} 个")
            self._log_dup(f"💾 释放空间: {format_size(deleted_size)}")
            self._log_dup(f"📌 保留文件位置可在上方查看")
            self._log_dup("-" * 60)

            self.root.after(0, lambda: self.status_label.config(
                text=f"✅ 重复文件清理完成！释放 {format_size(deleted_size)}"))
            self.root.after(0, self._update_disk_info)

            # 更新首页卡片
            self.root.after(0, lambda: self.card_dup.update_value(
                f"已清理 {format_size(deleted_size)}"))

        except Exception as e:
            self._log_dup(f"\n❌ 删除过程出错: {e}")
            self.root.after(0, lambda: self.status_label.config(text="❌ 删除重复文件出错"))
        finally:
            self.root.after(0, lambda: self._set_running(False))
            if hasattr(self, 'dup_delete_btn'):
                self.root.after(0, lambda: self.dup_delete_btn.set_enabled(
                    len(self.duplicate_files) > 0))

    # ========== 备份管理 ==========

    def _refresh_backup_info(self):
        backup_size = self.backup_manager.get_backup_size()
        if hasattr(self, 'backup_info_label'):
            self.backup_info_label.config(
                text=f"📦 备份目录: {self.backup_manager.backup_root}\n"
                     f"💾 备份占用空间: {format_size(backup_size)}")

    def _clear_backup(self):
        if messagebox.askyesno("确认", "确定要删除所有备份吗？此操作不可恢复！", icon=messagebox.WARNING):
            if self.backup_manager.clear_backup():
                if hasattr(self, 'backup_info_label'):
                    self.backup_info_label.config(text="✅ 备份已清空")
                self.status_label.config(text="备份已清空")
            else:
                messagebox.showerror("错误", "清理备份失败")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = CCleanerApp()
    app.run()