#!/bin/bash
RESDIR="$(cd "$(dirname "$0")/../Resources" && pwd)"
cd "$RESDIR"

# 找到可用的 Python3
MARVIS_DIR="$HOME/Library/Application Support/com.tencent.mac.marvis/components/MarvisAgent/Versions"
PYTHON=""

# 优先 Marvis 内置 Python 3.11
if [ -d "$MARVIS_DIR" ]; then
    for ver_dir in "$MARVIS_DIR"/*/; do
        candidate="${ver_dir}runtime/python311/bin/python3"
        if [ -x "$candidate" ]; then
            PYTHON="$candidate"
            break
        fi
    done
fi

# 备选 Python
if [ -z "$PYTHON" ]; then
    for candidate in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
        if [ -x "$candidate" ]; then
            PYTHON="$candidate"
            break
        fi
    done
fi

if [ -z "$PYTHON" ]; then
    osascript -e 'display dialog "未找到 Python3，请先安装 Python3。\n可在终端执行: xcode-select --install" buttons {"确定"} default button 1 with icon stop'
    exit 1
fi

# 确保依赖
MISSING_PKG=""
NEED_PLAYWRIGHT=0

"$PYTHON" -c "import requests" 2>/dev/null || MISSING_PKG="$MISSING_PKG requests"
"$PYTHON" -c "import yt_dlp" 2>/dev/null || MISSING_PKG="$MISSING_PKG yt-dlp"
"$PYTHON" -c "from faster_whisper import WhisperModel" 2>/dev/null || MISSING_PKG="$MISSING_PKG faster-whisper"
"$PYTHON" -c "from playwright.sync_api import sync_playwright" 2>/dev/null || { MISSING_PKG="$MISSING_PKG playwright"; NEED_PLAYWRIGHT=1; }

if [ -n "$MISSING_PKG" ]; then
    osascript -e 'display dialog "正在安装依赖库...\n首次启动可能需要几分钟" buttons {"好"} default button 1 giving up after 2' &
    "$PYTHON" -m pip install --user --quiet $MISSING_PKG 2>/dev/null
fi

# 检测 Chromium 浏览器（抖音需要）
if [ "$NEED_PLAYWRIGHT" -eq 1 ] || ! "$PYTHON" -c "import subprocess,sys;r=subprocess.run([sys.executable,'-m','playwright','install','--dry-run','chromium'],capture_output=True,text=True);sys.exit(0 if 'already' in r.stdout.lower() else 1)" 2>/dev/null; then
    osascript -e 'display dialog "正在下载 Chromium 浏览器...\n约150MB，请耐心等待" buttons {"好"} default button 1 giving up after 3' &
    "$PYTHON" -m playwright install chromium 2>/dev/null
fi

# 启动应用
exec "$PYTHON" app.py
