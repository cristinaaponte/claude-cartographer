@echo off
REM Codebase Cartographer - Quick Installation
REM Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
REM
REM Usage:
REM   quick-install.bat                    # Install in current directory
REM   quick-install.bat C:\path\to\project # Install in specific directory

setlocal

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%1
if "%PROJECT_ROOT%"=="" set PROJECT_ROOT=.

echo Codebase Cartographer - Quick Install
echo Copyright (c) 2025 Breach Craft
echo.

REM Find Python
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set PYTHON=python
) else (
    where python3 >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set PYTHON=python3
    ) else (
        echo Error: Python not found. Please install Python 3.8+.
        exit /b 1
    )
)

echo Using Python: %PYTHON%
echo Project: %PROJECT_ROOT%
echo.

REM Run installer
%PYTHON% "%SCRIPT_DIR%install.py" "%PROJECT_ROOT%"
