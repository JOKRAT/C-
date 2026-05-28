# C盘清理大师 🧹

> 一款轻量级 Windows C 盘清理工具，帮助您快速释放磁盘空间。

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![GUI](https://img.shields.io/badge/GUI-tkinter-green)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 🗑️ **临时文件清理** | 清理 Windows 临时文件夹 |
| ♻️ **回收站清空** | 一键清空回收站 |
| 🌐 **浏览器缓存清理** | 支持 Chrome、Edge、Firefox 缓存 |
| 📋 **系统日志清理** | 清理 Windows 事件日志 |
| 🔄 **Windows 更新缓存** | 清理 SoftwareDistribution 和 WinSxS 组件 |
| ⚡ **预取文件清理** | 清理 Prefetch 文件夹 |
| 🖼️ **缩略图缓存清理** | 清理 Thumbnail 缓存 |
| 🌍 **DNS 缓存清理** | 刷新 DNS 解析缓存 |
| 📁 **最近文件记录清理** | 清理最近使用的文件列表 |
| 📂 **大文件扫描** | 扫描 C 盘中的大文件（可自定义阈值） |
| 🔁 **重复文件检测** | 基于 MD5 哈希检测重复文件，支持删除到仅保留一个 |
| 💾 **清理前自动备份** | 自动创建注册表备份和系统还原点 |
| 📊 **首页一键分析** | 快速概览 C 盘空间使用情况 |

---

## 🖼️ 界面预览

- **5 个导航标签**：首页、系统清理、大文件、重复文件、备份管理
- **现代化 UI**：圆角按钮、卡片式布局、彩色进度条
- **实时进度反馈**：清理/扫描过程中显示进度条和状态信息

---

## 🚀 快速使用

### 方式一：直接运行（推荐普通用户）

1. 从 [Releases](https://github.com/JOKRAT/C-/releases) 下载最新版 `C盘清理大师.exe`
2. **以管理员身份运行**（右键 → 以管理员身份运行）
3. 点击「一键扫描」分析 C 盘状态
4. 选择要清理的项目，点击「一键清理」

> ⚠️ **注意**：建议以管理员身份运行，否则部分系统目录无法访问。

### 方式二：从源码运行（推荐开发者）

```bash
# 1. 克隆仓库
git clone https://github.com/JOKRAT/C-.git
cd C-

# 2. 运行（需要 Python 3.11+）
python main.py
```

### 方式三：自行打包为 .exe

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "C盘清理大师" main.py
```

生成的可执行文件在 `dist/C盘清理大师.exe`。

---

## 📁 项目结构

```
C盘清理大师/
├── main.py              # 程序入口
├── gui_app.py           # 图形界面（tkinter）
├── cleaner_core.py      # 核心清理模块
├── scanner.py           # 大文件 & 重复文件扫描器
├── backup_manager.py    # 备份管理（注册表 + 系统还原点）
├── utils.py             # 工具函数（管理员检测、文件删除等）
├── build.bat            # 一键构建脚本
├── .gitignore           # Git 忽略规则
└── README.md            # 本文件
```

---

## ⚙️ 技术栈

- **语言**：Python 3.11+
- **GUI 框架**：tkinter（标准库）
- **打包工具**：PyInstaller 6.20+
- **多线程**：threading + ThreadPoolExecutor
- **哈希检测**：MD5（重复文件识别）
- **系统接口**：ctypes（磁盘信息、管理员检测）

---

## 🔧 开发说明

### 环境要求

- Windows 10 / Windows 11
- Python 3.11 或更高版本
- 无需额外安装第三方库（全部使用标准库）

### 本地开发

```bash
# 语法检查
python -c "import py_compile; py_compile.compile('gui_app.py', doraise=True); print('OK')"

# 直接运行调试
python main.py
```

---

## 📝 更新日志

### v1.0（当前版本）
- 完整的 C 盘清理功能
- 大文件扫描（可自定义阈值）
- 重复文件检测与删除
- 清理前自动备份
- 现代化 GUI 界面
- 一键扫描 / 一键清理
- 实时进度条反馈

---

## ⚠️ 免责声明

- 本工具会删除系统临时文件和缓存，请在使用前确认需要清理的内容
- 清理前会自动创建备份，但建议您自行备份重要数据
- 使用本工具造成的任何数据丢失，开发者不承担责任

---

## 📄 许可证

本项目采用 MIT 许可证。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
