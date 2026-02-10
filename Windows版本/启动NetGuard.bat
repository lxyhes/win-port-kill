@echo off
chcp 65001 >nul
title NetGuard 端口管理工具 - 热加载模式
echo.
echo ==========================================
echo    🛡️ NetGuard 端口管理工具
echo    热加载模式 - 修改代码后自动重启
echo ==========================================
echo.
echo 正在启动...
echo.

python netguard_hotreload.py

pause
