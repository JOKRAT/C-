@echo off
chcp 65001 >nul
echo ========================================
echo   C盘清理大师 - 打包脚本
echo ========================================
echo.

REM 切换到项目目录
cd /d "%~dp0"

REM 清理旧的打包文件
echo [1/4] 清理旧的构建文件...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "*.spec" del /q "*.spec" 2>nul

echo [2/4] 使用PyInstaller打包...
pyinstaller --onefile --windowed --name "C盘清理大师" --icon NUL --add-data ".;." main.py

if %errorlevel% neq 0 (
    echo.
    echo [错误] 打包失败！请检查错误信息。
    pause
    exit /b 1
)

echo [3/4] 复制配置文件...
if exist "dist\C盘清理大师.exe" (
    echo 打包成功！可执行文件: dist\C盘清理大师.exe
)

echo [4/4] 完成！
echo.
echo ========================================
echo   打包完成！
echo   可执行文件: dist\C盘清理大师.exe
echo   大小: 
for %%I in ("dist\C盘清理大师.exe") do echo   %%~zI 字节
echo ========================================
pause
