@echo off
chcp 65001 >nul
title 创建桌面快捷方式 - C盘清理大师

echo ========================================
echo   创建桌面快捷方式
echo ========================================
echo.

REM 获取当前目录
set "CURRENT_DIR=%~dp0"
set "EXE_PATH=%CURRENT_DIR%dist\C盘清理大师.exe"

REM 检查exe是否存在
if not exist "%EXE_PATH%" (
    echo [错误] 找不到可执行文件！
    echo 请先运行 build.bat 进行打包。
    echo 期望路径: %EXE_PATH%
    pause
    exit /b 1
)

REM 获取桌面路径
set "DESKTOP=%USERPROFILE%\Desktop"

REM 创建VBScript来创建快捷方式
set "VBS_FILE=%TEMP%\CreateShortcut.vbs"

echo Set WshShell = WScript.CreateObject("WScript.Shell") > "%VBS_FILE%"
echo Set Shortcut = WshShell.CreateShortcut("%DESKTOP%\C盘清理大师.lnk") >> "%VBS_FILE%"
echo Shortcut.TargetPath = "%EXE_PATH%" >> "%VBS_FILE%"
echo Shortcut.WorkingDirectory = "%CURRENT_DIR%" >> "%VBS_FILE%"
echo Shortcut.Description = "C盘清理大师 - 一键清理系统垃圾" >> "%VBS_FILE%"
echo Shortcut.IconLocation = "%EXE_PATH%, 0" >> "%VBS_FILE%"
echo Shortcut.Save >> "%VBS_FILE%"

cscript //nologo "%VBS_FILE%"

REM 清理临时文件
del "%VBS_FILE%" 2>nul

echo.
echo ✅ 桌面快捷方式已创建成功！
echo 📍 位置: %DESKTOP%\C盘清理大师.lnk
echo.
echo 提示：建议右键点击快捷方式 → 属性 → 高级 → 
echo      勾选「以管理员身份运行」以获得最佳清理效果
echo.
pause
