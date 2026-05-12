@echo off
chcp 65001 > nul
echo ==========================================
echo PPT Master - Trae Skill Installer
echo ==========================================
echo.

REM Check if running from the correct directory
if not exist "skills\ppt-master\SKILL.md" (
    echo [ERROR] Please run this script from the project root directory.
    echo [ERROR] Expected: skills\ppt-master\SKILL.md
echo.
    pause
    exit /b 1
)

REM Detect Trae edition
set "TRAE_SKILLS_DIR="
set "TRAE_EDITION="

if exist "%USERPROFILE%\.trae-cn\skills" (
    set "TRAE_SKILLS_DIR=%USERPROFILE%\.trae-cn\skills"
    set "TRAE_EDITION=Trae CN"
) else if exist "%USERPROFILE%\.trae\skills" (
    set "TRAE_SKILLS_DIR=%USERPROFILE%\.trae\skills"
    set "TRAE_EDITION=Trae International"
)

if "%TRAE_SKILLS_DIR%"=="" (
    echo [WARN] Trae skills directory not found.
    echo.
    echo Please select your Trae edition:
    echo 1. Trae International (~/.trae/skills)
    echo 2. Trae CN (~/.trae-cn/skills)
    echo.
    set /p choice="Enter 1 or 2: "
    if "!choice!"=="1" (
        set "TRAE_SKILLS_DIR=%USERPROFILE%\.trae\skills"
        set "TRAE_EDITION=Trae International"
    ) else (
        set "TRAE_SKILLS_DIR=%USERPROFILE%\.trae-cn\skills"
        set "TRAE_EDITION=Trae CN"
    )
)

echo [INFO] Detected: %TRAE_EDITION%
echo [INFO] Skills directory: %TRAE_SKILLS_DIR%
echo.

REM Create skills directory if not exists
if not exist "%TRAE_SKILLS_DIR%" (
    mkdir "%TRAE_SKILLS_DIR%"
    echo [INFO] Created skills directory.
)

REM Remove old skill if exists
if exist "%TRAE_SKILLS_DIR%\ppt-master" (
    echo [INFO] Removing old ppt-master skill...
    rmdir /s /q "%TRAE_SKILLS_DIR%\ppt-master"
)

REM Copy skill files
echo [INFO] Installing ppt-master skill...
xcopy /s /e /i /q "skills\ppt-master" "%TRAE_SKILLS_DIR%\ppt-master" > nul

if errorlevel 1 (
    echo [ERROR] Failed to copy skill files.
    pause
    exit /b 1
)

echo [OK] Skill installed successfully!
echo.

REM Check Python
python --version > nul 2>&1
if errorlevel 1 (
    echo [WARN] Python not found in PATH.
    echo [WARN] Please install Python 3.10+ from https://www.python.org/downloads/
    echo [WARN] Then run: pip install -r requirements.txt
) else (
    echo [INFO] Python detected.
    echo [INFO] Installing Python dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [WARN] Failed to install dependencies. Please run manually:
        echo         pip install -r requirements.txt
    ) else (
        echo [OK] Dependencies installed.
    )
)

echo.
echo ==========================================
echo Installation Complete!
echo ==========================================
echo.
echo Next steps:
echo 1. Restart Trae IDE if it's running
echo 2. Open the AI chat panel
echo 3. Type: "Create a PPT from [your file]"
echo.
echo To list available templates:
echo   python skills/ppt-master/scripts/project_manager.py list-templates
echo.
pause
