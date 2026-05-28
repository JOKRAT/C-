"""
核心清理模块 - 提供各种系统垃圾清理功能
"""

import os
import glob
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Callable
from datetime import datetime, timedelta

from utils import get_size, format_size, safe_delete


class CleanerCore:
    """核心清理器 - 管理所有清理任务"""
    
    def __init__(self, progress_callback: Callable = None):
        """
        初始化清理器
        :param progress_callback: 进度回调函数 (current, total, message)
        """
        self.progress_callback = progress_callback
        self.cleaned_size = 0
        self.cleaned_count = 0
        self._total_items = 0
        self._current_item = 0
    
    def _report_progress(self, message: str):
        """报告进度"""
        if self.progress_callback:
            self.progress_callback(self._current_item, self._total_items, message)
    
    def _add_cleaned(self, size: int, count: int = 1):
        """累加清理数据"""
        self.cleaned_size += size
        self.cleaned_count += count
        self._current_item += 1
    
    # ========== 临时文件清理 ==========
    
    def clean_temp_files(self) -> Dict:
        """清理Windows临时文件"""
        result = {"name": "临时文件", "size": 0, "count": 0, "success": True}
        temp_paths = [
            os.environ.get("TEMP", ""),
            os.environ.get("TMP", ""),
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Temp"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp"),
        ]
        
        for temp_path in set(filter(None, temp_paths)):
            if not os.path.exists(temp_path):
                continue
            self._report_progress(f"正在清理临时文件: {temp_path}")
            try:
                for item in os.listdir(temp_path):
                    item_path = os.path.join(temp_path, item)
                    size = get_size(item_path)
                    if safe_delete(item_path):
                        result["size"] += size
                        result["count"] += 1
                        self._add_cleaned(size)
            except (OSError, PermissionError):
                pass
        
        return result
    
    # ========== 回收站清理 ==========
    
    def clean_recycle_bin(self) -> Dict:
        """清空回收站"""
        result = {"name": "回收站", "size": 0, "count": 0, "success": True}
        self._report_progress("正在清空回收站...")
        try:
            # 使用Windows API清空回收站
            subprocess.run(["cmd", "/c", "rd /s /q C:\\$Recycle.Bin"], 
                         capture_output=True, shell=True)
            # 或者使用更安全的方式
            subprocess.run(["cmd", "/c", "PowerShell -Command \"Clear-RecycleBin -Force\""],
                         capture_output=True, shell=True)
            result["success"] = True
            self._add_cleaned(0)  # 大小无法精确统计
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
        
        return result
    
    # ========== 浏览器缓存清理 ==========
    
    def clean_browser_cache(self) -> List[Dict]:
        """清理浏览器缓存"""
        results = []
        user_profile = os.environ.get("USERPROFILE", "")
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        appdata = os.environ.get("APPDATA", "")
        
        browsers = [
            {
                "name": "Chrome 缓存",
                "paths": [
                    os.path.join(local_appdata, "Google", "Chrome", "User Data", "Default", "Cache"),
                    os.path.join(local_appdata, "Google", "Chrome", "User Data", "Default", "Code Cache"),
                    os.path.join(local_appdata, "Google", "Chrome", "User Data", "Default", "Service Worker", "CacheStorage"),
                ]
            },
            {
                "name": "Edge 缓存",
                "paths": [
                    os.path.join(local_appdata, "Microsoft", "Edge", "User Data", "Default", "Cache"),
                    os.path.join(local_appdata, "Microsoft", "Edge", "User Data", "Default", "Code Cache"),
                    os.path.join(local_appdata, "Microsoft", "Edge", "User Data", "Default", "Service Worker", "CacheStorage"),
                ]
            },
            {
                "name": "Firefox 缓存",
                "paths": [
                    os.path.join(local_appdata, "Mozilla", "Firefox", "Profiles"),
                ]
            },
            {
                "name": "IE/Edge 旧版缓存",
                "paths": [
                    os.path.join(local_appdata, "Microsoft", "Windows", "INetCache"),
                    os.path.join(local_appdata, "Microsoft", "Windows", "Temporary Internet Files"),
                ]
            },
        ]
        
        for browser in browsers:
            browser_result = {"name": browser["name"], "size": 0, "count": 0, "success": True}
            self._report_progress(f"正在清理{browser['name']}...")
            
            for cache_path in browser["paths"]:
                if not os.path.exists(cache_path):
                    continue
                
                # Firefox 需要特殊处理 - 查找实际配置文件
                if "Firefox" in browser["name"] and "Profiles" in cache_path:
                    try:
                        for profile in os.listdir(cache_path):
                            profile_cache = os.path.join(cache_path, profile, "cache2")
                            if os.path.exists(profile_cache):
                                size = get_size(profile_cache)
                                if safe_delete(profile_cache):
                                    browser_result["size"] += size
                                    browser_result["count"] += 1
                                    self._add_cleaned(size)
                    except (OSError, PermissionError):
                        pass
                    continue
                
                try:
                    for item in os.listdir(cache_path):
                        item_path = os.path.join(cache_path, item)
                        size = get_size(item_path)
                        if safe_delete(item_path):
                            browser_result["size"] += size
                            browser_result["count"] += 1
                            self._add_cleaned(size)
                except (OSError, PermissionError):
                    pass
            
            results.append(browser_result)
        
        return results
    
    # ========== 系统日志清理 ==========
    
    def clean_system_logs(self) -> Dict:
        """清理Windows系统日志"""
        result = {"name": "系统日志", "size": 0, "count": 0, "success": True}
        self._report_progress("正在清理系统日志...")
        
        log_paths = [
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Logs"),
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32", "LogFiles"),
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32", "winevt", "Logs"),
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Debug"),
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Panther"),
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "SoftwareDistribution", "Download"),
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32", "SleepStudy"),
        ]
        
        for log_path in log_paths:
            if not os.path.exists(log_path):
                continue
            
            try:
                for item in os.listdir(log_path):
                    item_path = os.path.join(log_path, item)
                    # 跳过正在使用的文件
                    if item.endswith((".evtx", ".etl")) and os.path.isfile(item_path):
                        try:
                            # 尝试获取文件大小，如果能获取则尝试删除
                            size = os.path.getsize(item_path)
                            # 对于事件日志，使用wevtutil命令清除
                            if item.endswith(".evtx"):
                                log_name = os.path.splitext(item)[0]
                                subprocess.run(
                                    ["wevtutil", "cl", log_name],
                                    capture_output=True, shell=True
                                )
                            else:
                                if safe_delete(item_path):
                                    result["size"] += size
                                    result["count"] += 1
                                    self._add_cleaned(size)
                        except (OSError, PermissionError):
                            pass
                    elif os.path.isfile(item_path):
                        size = get_size(item_path)
                        if safe_delete(item_path):
                            result["size"] += size
                            result["count"] += 1
                            self._add_cleaned(size)
            except (OSError, PermissionError):
                pass
        
        return result
    
    # ========== Windows更新缓存清理 ==========
    
    def clean_windows_update_cache(self) -> Dict:
        """清理Windows更新缓存"""
        result = {"name": "Windows更新缓存", "size": 0, "count": 0, "success": True}
        self._report_progress("正在清理Windows更新缓存...")
        
        # Windows更新缓存目录
        winsxs_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "WinSxS")
        soft_dist_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "SoftwareDistribution", "Download")
        
        # 清理SoftwareDistribution\Download
        if os.path.exists(soft_dist_path):
            try:
                for item in os.listdir(soft_dist_path):
                    item_path = os.path.join(soft_dist_path, item)
                    size = get_size(item_path)
                    if safe_delete(item_path):
                        result["size"] += size
                        result["count"] += 1
                        self._add_cleaned(size)
            except (OSError, PermissionError):
                pass
        
        # 使用DISM清理WinSxS（需要管理员权限，设置30秒超时避免卡死）
        try:
            self._report_progress("正在使用DISM清理WinSxS组件（30秒超时）...")
            subprocess.run(
                ["DISM", "/Online", "/Cleanup-Image", "/StartComponentCleanup", "/Quiet"],
                capture_output=True, shell=True, timeout=30
            )
            result["success"] = True
        except subprocess.TimeoutExpired:
            self._report_progress("DISM清理超时，已跳过（不影响其他清理）")
            result["note"] = "DISM清理超时已跳过"
        except Exception:
            pass
        
        # 清理Windows.old（如果有）
        windows_old = os.path.join(os.environ.get("SYSTEMDRIVE", "C:"), "Windows.old")
        if os.path.exists(windows_old):
            try:
                size = get_size(windows_old)
                subprocess.run(
                    ["cmd", "/c", f"takeown /F {windows_old} /R /D Y && icacls {windows_old} /grant Administrators:F /T && rd /s /q {windows_old}"],
                    capture_output=True, shell=True
                )
                result["size"] += size
                self._add_cleaned(size)
            except (OSError, PermissionError):
                pass
        
        return result
    
    # ========== 预取文件清理 ==========
    
    def clean_prefetch(self) -> Dict:
        """清理预取文件"""
        result = {"name": "预取文件", "size": 0, "count": 0, "success": True}
        prefetch_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Prefetch")
        
        if os.path.exists(prefetch_path):
            self._report_progress("正在清理预取文件...")
            try:
                for item in os.listdir(prefetch_path):
                    item_path = os.path.join(prefetch_path, item)
                    if item.endswith(".pf"):
                        size = get_size(item_path)
                        if safe_delete(item_path):
                            result["size"] += size
                            result["count"] += 1
                            self._add_cleaned(size)
            except (OSError, PermissionError):
                pass
        
        return result
    
    # ========== 缩略图缓存清理 ==========
    
    def clean_thumbnails(self) -> Dict:
        """清理缩略图缓存"""
        result = {"name": "缩略图缓存", "size": 0, "count": 0, "success": True}
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        
        thumb_paths = [
            os.path.join(local_appdata, "Microsoft", "Windows", "Explorer"),
        ]
        
        for thumb_path in thumb_paths:
            if os.path.exists(thumb_path):
                self._report_progress("正在清理缩略图缓存...")
                try:
                    for item in os.listdir(thumb_path):
                        item_path = os.path.join(thumb_path, item)
                        if item.startswith("thumbcache_") or item == "iconcache.db":
                            size = get_size(item_path)
                            if safe_delete(item_path):
                                result["size"] += size
                                result["count"] += 1
                                self._add_cleaned(size)
                except (OSError, PermissionError):
                    pass
        
        return result
    
    # ========== DNS缓存清理 ==========
    
    def clean_dns_cache(self) -> Dict:
        """清理DNS缓存"""
        result = {"name": "DNS缓存", "size": 0, "count": 0, "success": True}
        self._report_progress("正在清理DNS缓存...")
        try:
            subprocess.run(["ipconfig", "/flushdns"], capture_output=True, shell=True)
            result["success"] = True
            self._add_cleaned(0)
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
        
        return result
    
    # ========== 运行日志清理 ==========
    
    def clean_recent_files(self) -> Dict:
        """清理最近使用的文件列表"""
        result = {"name": "最近文件记录", "size": 0, "count": 0, "success": True}
        appdata = os.environ.get("APPDATA", "")
        
        recent_path = os.path.join(appdata, "Microsoft", "Windows", "Recent")
        if os.path.exists(recent_path):
            self._report_progress("正在清理最近文件记录...")
            try:
                for item in os.listdir(recent_path):
                    item_path = os.path.join(recent_path, item)
                    size = get_size(item_path)
                    if safe_delete(item_path):
                        result["size"] += size
                        result["count"] += 1
                        self._add_cleaned(size)
            except (OSError, PermissionError):
                pass
        
        return result
    
    # ========== 综合清理 ==========
    
    def run_all_cleaners(self, selected_items: List[str] = None) -> List[Dict]:
        """
        运行所有选中的清理任务
        :param selected_items: 选中的清理项目列表，None表示全部
        :return: 清理结果列表
        """
        self.cleaned_size = 0
        self.cleaned_count = 0
        
        # 定义所有可用的清理任务
        all_cleaners = {
            "temp_files": ("临时文件", self.clean_temp_files),
            "recycle_bin": ("回收站", self.clean_recycle_bin),
            "browser_cache": ("浏览器缓存", self.clean_browser_cache),
            "system_logs": ("系统日志", self.clean_system_logs),
            "windows_update": ("Windows更新缓存", self.clean_windows_update_cache),
            "prefetch": ("预取文件", self.clean_prefetch),
            "thumbnails": ("缩略图缓存", self.clean_thumbnails),
            "dns_cache": ("DNS缓存", self.clean_dns_cache),
            "recent_files": ("最近文件记录", self.clean_recent_files),
        }
        
        # 计算总任务数
        if selected_items:
            self._total_items = len(selected_items)
        else:
            self._total_items = len(all_cleaners)
        self._current_item = 0
        
        results = []
        
        for key, (name, cleaner_func) in all_cleaners.items():
            if selected_items and key not in selected_items:
                continue
            
            try:
                result = cleaner_func()
                if isinstance(result, list):
                    results.extend(result)
                else:
                    results.append(result)
            except Exception as e:
                results.append({
                    "name": name,
                    "size": 0,
                    "count": 0,
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    def get_total_cleaned(self) -> int:
        """获取总共清理的字节数"""
        return self.cleaned_size
