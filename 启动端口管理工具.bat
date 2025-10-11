@echo off
title Port Manager Launcher

echo.
echo ====================================
echo     Port Manager Tool Launcher
echo ====================================
echo.

echo Checking Python environment...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo.
    echo Please make sure Python 3.6+ is installed
    echo and added to system PATH environment variable
    echo.
    pause
    exit /b 1
)

echo [SUCCESS] Python environment check passed
echo.

echo Checking dependencies...

python -c "import tkinter, psutil" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Missing dependencies, installing automatically...
    echo.

    echo Installing psutil...
    pip install psutil

    if %errorlevel% neq 0 (
        echo [ERROR] Dependency installation failed!
        echo Please manually run: pip install psutil
        echo.
        pause
        exit /b 1
    )

    echo [SUCCESS] Dependencies installed
    echo.
) else (
    echo [SUCCESS] Dependencies check passed
    echo.
)

echo Starting Port Manager Tool...
echo.

python port_manager.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Program encountered an error!
    pause
)