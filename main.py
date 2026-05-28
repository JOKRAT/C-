"""
C盘清理大师 - 主程序入口
支持直接运行和PyInstaller打包
"""

import sys
import os

# 确保当前目录在路径中
if getattr(sys, 'frozen', False):
    # 如果是打包后的exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

from utils import is_admin
from gui_app import CCleanerApp


def main():
    """主函数"""
    if not is_admin():
        print("提示: 建议以管理员身份运行以获得最佳清理效果")
    
    app = CCleanerApp()
    app.run()


if __name__ == "__main__":
    main()
