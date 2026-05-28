"""
大文件扫描模块 - 扫描C盘中的大文件和重复文件
"""

import os
import hashlib
from pathlib import Path
from typing import List, Dict, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from utils import get_size, format_size


class FileScanner:
    """文件扫描器 - 扫描大文件和重复文件"""
    
    def __init__(self, progress_callback: Callable = None):
        self.progress_callback = progress_callback
        self.scanned_files = []
        self.large_files = []
        self.duplicate_files = {}
        self._lock = Lock()
        self._stop_flag = False
    
    def stop(self):
        """停止扫描"""
        self._stop_flag = True
    
    def _report_progress(self, message: str, current: int = 0, total: int = 0):
        """报告进度"""
        if self.progress_callback:
            self.progress_callback(current, total, message)
    
    def scan_large_files(
        self,
        root_path: str = "C:\\",
        min_size_mb: int = 50,
        max_results: int = 100,
        exclude_dirs: List[str] = None
    ) -> List[Dict]:
        """
        扫描大文件
        :param root_path: 扫描根目录
        :param min_size_mb: 最小文件大小(MB)
        :param max_results: 最大返回结果数
        :param exclude_dirs: 排除的目录列表
        :return: 大文件列表
        """
        self._stop_flag = False
        self.large_files = []
        min_size_bytes = min_size_mb * 1024 * 1024
        
        if exclude_dirs is None:
            exclude_dirs = [
                "Windows", "Program Files", "Program Files (x86)",
                "ProgramData", "System Volume Information",
                "$Recycle.Bin", "Recovery", "Boot",
                "Users\\All Users", "PerfLogs",
            ]
        
        # 收集所有文件
        all_files = []
        self._report_progress("正在扫描文件系统...", 0, 0)
        
        try:
            for dirpath, dirnames, filenames in os.walk(root_path):
                if self._stop_flag:
                    break
                
                # 跳过排除目录
                dirnames[:] = [
                    d for d in dirnames
                    if not any(excluded.lower() in os.path.join(dirpath, d).lower()
                              for excluded in exclude_dirs)
                ]
                
                for filename in filenames:
                    if self._stop_flag:
                        break
                    filepath = os.path.join(dirpath, filename)
                    all_files.append(filepath)
        except (OSError, PermissionError):
            pass
        
        total_files = len(all_files)
        self._report_progress(f"正在分析文件大小 (共 {total_files} 个文件)...", 0, total_files)
        
        # 使用多线程检查文件大小
        processed = 0
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_file = {
                executor.submit(self._check_file_size, fp, min_size_bytes): fp
                for fp in all_files
            }
            
            for future in as_completed(future_to_file):
                if self._stop_flag:
                    break
                
                with self._lock:
                    processed += 1
                    if processed % 1000 == 0:
                        self._report_progress(
                            f"正在分析文件... ({processed}/{total_files})",
                            processed, total_files
                        )
                
                result = future.result()
                if result:
                    with self._lock:
                        self.large_files.append(result)
        
        # 按大小排序，取前max_results个
        self.large_files.sort(key=lambda x: x["size"], reverse=True)
        self.large_files = self.large_files[:max_results]
        
        return self.large_files
    
    def _check_file_size(self, filepath: str, min_size_bytes: int) -> Dict:
        """检查单个文件大小"""
        try:
            size = os.path.getsize(filepath)
            if size >= min_size_bytes:
                return {
                    "path": filepath,
                    "size": size,
                    "size_str": format_size(size),
                    "name": os.path.basename(filepath),
                    "directory": os.path.dirname(filepath),
                }
        except (OSError, PermissionError):
            pass
        return None
    
    def scan_duplicate_files(
        self,
        root_path: str = "C:\\",
        min_size_kb: int = 1024,
        exclude_dirs: List[str] = None
    ) -> Dict[str, List[Dict]]:
        """
        扫描重复文件
        :param root_path: 扫描根目录
        :param min_size_kb: 最小文件大小(KB)
        :param exclude_dirs: 排除的目录列表
        :return: 重复文件字典 {hash: [file_info, ...]}
        """
        self._stop_flag = False
        self.duplicate_files = {}
        min_size_bytes = min_size_kb * 1024
        
        if exclude_dirs is None:
            exclude_dirs = [
                "Windows", "Program Files", "Program Files (x86)",
                "ProgramData", "System Volume Information",
                "$Recycle.Bin",
            ]
        
        # 第一步：按文件大小分组
        size_groups = {}
        total_files = 0
        
        self._report_progress("正在扫描文件系统（重复文件检测）...", 0, 0)
        
        try:
            for dirpath, dirnames, filenames in os.walk(root_path):
                if self._stop_flag:
                    break
                
                dirnames[:] = [
                    d for d in dirnames
                    if not any(excluded.lower() in os.path.join(dirpath, d).lower()
                              for excluded in exclude_dirs)
                ]
                
                for filename in filenames:
                    if self._stop_flag:
                        break
                    filepath = os.path.join(dirpath, filename)
                    try:
                        size = os.path.getsize(filepath)
                        if size >= min_size_bytes:
                            if size not in size_groups:
                                size_groups[size] = []
                            size_groups[size].append(filepath)
                            total_files += 1
                    except (OSError, PermissionError):
                        pass
        except (OSError, PermissionError):
            pass
        
        # 第二步：对相同大小的文件计算哈希
        candidates = [
            files for size, files in size_groups.items() if len(files) > 1
        ]
        
        total_candidates = sum(len(files) for files in candidates)
        processed = 0
        
        self._report_progress(f"正在计算文件哈希 (共 {total_candidates} 个候选文件)...", 0, total_candidates)
        
        for file_group in candidates:
            if self._stop_flag:
                break
            
            for filepath in file_group:
                if self._stop_flag:
                    break
                
                with self._lock:
                    processed += 1
                    if processed % 100 == 0:
                        self._report_progress(
                            f"正在计算哈希... ({processed}/{total_candidates})",
                            processed, total_candidates
                        )
                
                file_hash = self._calculate_hash(filepath)
                if file_hash:
                    with self._lock:
                        if file_hash not in self.duplicate_files:
                            self.duplicate_files[file_hash] = []
                        self.duplicate_files[file_hash].append({
                            "path": filepath,
                            "size": os.path.getsize(filepath),
                            "size_str": format_size(os.path.getsize(filepath)),
                            "name": os.path.basename(filepath),
                            "directory": os.path.dirname(filepath),
                        })
        
        # 只保留确实有重复的
        self.duplicate_files = {
            h: files for h, files in self.duplicate_files.items() if len(files) > 1
        }
        
        return self.duplicate_files
    
    def _calculate_hash(self, filepath: str, buffer_size: int = 65536) -> str:
        """计算文件的MD5哈希值"""
        try:
            md5 = hashlib.md5()
            with open(filepath, "rb") as f:
                while True:
                    data = f.read(buffer_size)
                    if not data:
                        break
                    md5.update(data)
            return md5.hexdigest()
        except (OSError, PermissionError):
            return None
    
    def get_total_duplicate_size(self) -> int:
        """获取重复文件占用的总空间（保留一个副本后的可释放空间）"""
        total = 0
        for file_hash, files in self.duplicate_files.items():
            if len(files) > 1:
                # 保留第一个，其余都是重复的
                for f in files[1:]:
                    total += f["size"]
        return total
    
    def get_total_large_files_size(self) -> int:
        """获取大文件总大小"""
        return sum(f["size"] for f in self.large_files)
