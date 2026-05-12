#!/usr/bin/env bash
set -e

echo "=========================================="
echo "PPT Master - Trae Skill Installer"
echo "=========================================="
echo ""

# Check if running from the correct directory
if [ ! -f "skills/ppt-master/SKILL.md" ]; then
    echo "[ERROR] Please run this script from the project root directory."
    echo "[ERROR] Expected: skills/ppt-master/SKILL.md"
    exit 1
fi

# Detect Trae edition
TRAE_SKILLS_DIR=""
TRAE_EDITION=""

if [ -d "$HOME/.trae-cn/skills" ]; then
    TRAE_SKILLS_DIR="$HOME/.trae-cn/skills"
    TRAE_EDITION="Trae CN"
elif [ -d "$HOME/.trae/skills" ]; then
    TRAE_SKILLS_DIR="$HOME/.trae/skills"
    TRAE_EDITION="Trae International"
fi

if [ -z "$TRAE_SKILLS_DIR" ]; then
    echo "[WARN] Trae skills directory not found."
    echo ""
    echo "Please select your Trae edition:"
    echo "1. Trae International (~/.trae/skills)"
    echo "2. Trae CN (~/.trae-cn/skills)"
    echo ""
    read -p "Enter 1 or 2: " choice
    if [ "$choice" = "1" ]; then
        TRAE_SKILLS_DIR="$HOME/.trae/skills"
        TRAE_EDITION="Trae International"
    else
        TRAE_SKILLS_DIR="$HOME/.trae-cn/skills"
        TRAE_EDITION="Trae CN"
    fi
fi

echo "[INFO] Detected: $TRAE_EDITION"
echo "[INFO] Skills directory: $TRAE_SKILLS_DIR"
echo ""

# Create skills directory if not exists
mkdir -p "$TRAE_SKILLS_DIR"

# Remove old skill if exists
if [ -d "$TRAE_SKILLS_DIR/ppt-master" ]; then
    echo "[INFO] Removing old ppt-master skill..."
    rm -rf "$TRAE_SKILLS_DIR/ppt-master"
fi

# Copy skill files
echo "[INFO] Installing ppt-master skill..."
cp -r skills/ppt-master "$TRAE_SKILLS_DIR/"

echo "[OK] Skill installed successfully!"
echo ""

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "[WARN] Python not found in PATH."
    echo "[WARN] Please install Python 3.10+ from https://www.python.org/downloads/"
    echo "[WARN] Then run: pip install -r requirements.txt"
    PYTHON_CMD=""
fi

if [ -n "$PYTHON_CMD" ]; then
    echo "[INFO] Python detected: $($PYTHON_CMD --version)"
    echo "[INFO] Installing Python dependencies..."
    if $PYTHON_CMD -m pip install -r requirements.txt; then
        echo "[OK] Dependencies installed."
    else
        echo "[WARN] Failed to install dependencies. Please run manually:"
        echo "       $PYTHON_CMD -m pip install -r requirements.txt"
    fi
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Restart Trae IDE if it's running"
echo "2. Open the AI chat panel"
echo "3. Type: \"Create a PPT from [your file]\""
echo ""
echo "To list available templates:"
echo "  python3 skills/ppt-master/scripts/project_manager.py list-templates"
echo ""
