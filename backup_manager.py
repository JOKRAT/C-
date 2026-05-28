"""
安全备份模块 - 清理前自动备份文件到回收站或备份目录
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path
from typing import List, Tuple


class BackupManager:
    """备份管理器 - 在清理前创建文件备份"""
    
    def __init__(self):
        self.backup_root = Path(os.environ.get("LOCALAPPDATA", ".")) / "CCleaner_Backup"
        self.manifest_file = self.backup_root / "manifest.json"
        self._ensure_backup_dir()
    
    def _ensure_backup_dir(self):
        """确保备份目录存在"""
        self.backup_root.mkdir(parents=True, exist_ok=True)
    
    def backup_file(self, file_path: str) -> bool:
        """备份单个文件到备份目录"""
        try:
            src = Path(file_path)
            if not src.exists():
                return False
            
            # 创建相对路径结构
            rel_path = src.relative_to(src.anchor) if src.is_absolute() else src
            backup_path = self.backup_root / rel_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 复制文件
            shutil.copy2(str(src), str(backup_path))
            return True
        except (OSError, PermissionError, ValueError) as e:
            print(f"备份文件失败 {file_path}: {e}")
            return False
    
    def backup_directory(self, dir_path: str) -> int:
        """备份整个目录，返回成功备份的文件数"""
        count = 0
        try:
            for dirpath, dirnames, filenames in os.walk(dir_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if self.backup_file(fp):
                        count += 1
        except (OSError, PermissionError):
            pass
        return count
    
    def backup_items(self, paths: List[str]) -> Tuple[int, int]:
        """
        备份多个路径
        返回: (成功备份的文件数, 总项目数)
        """
        success_count = 0
        total_count = len(paths)
        
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_record = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "items": []
        }
        
        for path in paths:
            if os.path.isfile(path):
                if self.backup_file(path):
                    success_count += 1
                    session_record["items"].append({
                        "path": path,
                        "type": "file",
                        "backup_path": str(self.backup_root / Path(path).relative_to(Path(path).anchor))
                    })
            elif os.path.isdir(path):
                count = self.backup_directory(path)
                success_count += count
                session_record["items"].append({
                    "path": path,
                    "type": "directory",
                    "file_count": count
                })
        
        # 保存本次会话记录
        self._save_session(session_record)
        return success_count, total_count
    
    def _save_session(self, session_record: dict):
        """保存备份会话记录到清单文件"""
        try:
            manifest = []
            if self.manifest_file.exists():
                with open(self.manifest_file, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            
            manifest.append(session_record)
            
            # 只保留最近10次记录
            if len(manifest) > 10:
                manifest = manifest[-10:]
            
            with open(self.manifest_file, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存备份清单失败: {e}")
    
    def get_backup_size(self) -> int:
        """获取备份目录的总大小"""
        total = 0
        try:
            for dirpath, dirnames, filenames in os.walk(str(self.backup_root)):
                for f in filenames:
                    try:
                        total += os.path.getsize(os.path.join(dirpath, f))
                    except (OSError, PermissionError):
                        pass
        except (OSError, PermissionError):
            pass
        return total
    
    def restore_backup(self, session_id: str = None) -> int:
        """
        恢复备份文件
        如果指定session_id则恢复特定会话，否则恢复所有
        返回恢复的文件数
        """
        if not self.manifest_file.exists():
            return 0
        
        try:
            with open(self.manifest_file, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            return 0
        
        restored = 0
        for session in manifest:
            if session_id and session["session_id"] != session_id:
                continue
            
            for item in session["items"]:
                if item["type"] == "file":
                    backup_path = Path(item["backup_path"])
                    if backup_path.exists():
                        try:
                            original_path = Path(item["path"])
                            original_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(str(backup_path), str(original_path))
                            restored += 1
                        except (OSError, PermissionError):
                            pass
        
        return restored
    
    def clear_backup(self) -> bool:
        """清空所有备份"""
        try:
            shutil.rmtree(str(self.backup_root))
            self._ensure_backup_dir()
            return True
        except (OSError, PermissionError):
            return False
