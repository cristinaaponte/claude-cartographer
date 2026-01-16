@echo off
REM Codebase Cartographer - Unified Setup
REM Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
REM
REM One-command setup that installs everything:
REM - Portable venv with dependencies
REM - Codebase mapping tools
REM - Claude Code integration (hooks, skills, commands)
REM - Initial codebase map
REM
REM Usage:
REM   setup.bat                    # Setup in current directory
REM   setup.bat C:\path\to\project # Setup in specific directory

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%1
if "%PROJECT_ROOT%"=="" set PROJECT_ROOT=%CD%

echo ======================================================================
echo Codebase Cartographer - Unified Setup
echo Copyright (c) 2025 Breach Craft - Mike Piekarski ^<mp@breachcraft.io^>
echo ======================================================================
echo.
echo Project: %PROJECT_ROOT%
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
        echo Error: Python 3.8+ is required but not found.
        echo Please install Python from https://python.org
        exit /b 1
    )
)

echo Python: %PYTHON%

REM Step 1: Install Cartographer
echo.
echo Step 1: Installing Codebase Cartographer...
echo ----------------------------------------------------------------------
%PYTHON% "%SCRIPT_DIR%install.py" "%PROJECT_ROOT%"
if %ERRORLEVEL% neq 0 (
    echo Installation failed!
    exit /b 1
)

REM Step 2: Initialize the map
echo.
echo Step 2: Initializing codebase map...
echo ----------------------------------------------------------------------
cd /d "%PROJECT_ROOT%"

if exist ".claude-map\bin\claude-map.bat" (
    call .claude-map\bin\claude-map.bat init
) else (
    echo Error: Installation failed - claude-map not found
    exit /b 1
)

REM Step 3: Run benchmark
echo.
echo Step 3: Running token optimization benchmark...
echo ----------------------------------------------------------------------
call .claude-map\bin\claude-map.bat benchmark

REM Done
echo.
echo ======================================================================
echo Setup Complete!
echo ======================================================================
echo.
echo Installation:
echo   Map database: %PROJECT_ROOT%\.claude-map\codebase.db
echo   CLI tool:     %PROJECT_ROOT%\.claude-map\bin\claude-map.bat
echo   Claude hooks: %PROJECT_ROOT%\.claude\hooks\
echo.
echo Quick Start:
echo   .claude-map\bin\claude-map find ^<name^>      # Find component
echo   .claude-map\bin\claude-map query "^<text^>"   # Natural language query
echo   .claude-map\bin\claude-map show ^<file^>      # Show file components
echo   .claude-map\bin\claude-map stats            # Show statistics
echo.
