"""
工具函数模块 - 提供通用工具函数
"""

import os
import sys
import ctypes
import logging
from datetime import datetime, timedelta
from pathlib import Path


def is_admin() -> bool:
    """检查程序是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def run_as_admin():
    """以管理员权限重新启动程序"""
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )


def get_size(path: str) -> int:
    """获取文件或文件夹的大小（字节）"""
    try:
        if os.path.isfile(path):
            return os.path.getsize(path)
        elif os.path.isdir(path):
            total = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total += os.path.getsize(fp)
                    except (OSError, PermissionError):
                        pass
            return total
    except (OSError, PermissionError):
        return 0
    return 0


def format_size(size_bytes: int) -> str:
    """将字节大小格式化为可读字符串"""
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"


def get_drive_free_space(drive: str = "C:") -> int:
    """获取指定驱动器的剩余空间（字节）"""
    try:
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p(drive + "\\"),
            None,
            None,
            ctypes.pointer(free_bytes),
        )
        return free_bytes.value
    except Exception:
        return 0


def get_drive_total_space(drive: str = "C:") -> int:
    """获取指定驱动器的总空间（字节）"""
    try:
        total_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p(drive + "\\"),
            None,
            ctypes.pointer(total_bytes),
            None,
        )
        return total_bytes.value
    except Exception:
        return 0


def setup_logger():
    """设置日志记录器"""
    log_dir = Path(os.environ.get("TEMP", ".")) / "CCleaner_Logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"cleaner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger(__name__)


def safe_delete(path: str) -> bool:
    """安全删除文件/文件夹（先尝试普通删除，失败则尝试强制删除）"""
    try:
        if os.path.isfile(path):
            os.remove(path)
            return True
        elif os.path.isdir(path):
            import shutil
            shutil.rmtree(path, ignore_errors=True)
            return True
    except (OSError, PermissionError):
        pass
    return False
