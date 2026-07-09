"""
py2app 打包配置 - 你是我的眼儿
"""
from setuptools import setup

APP = ["app.py"]
DATA_FILES = [
    ("core", ["core/__init__.py", "core/config.py", "core/common.py",
              "core/bilibili.py", "core/douyin.py", "core/transcribe.py"]),
    ("", ["config.json", "icon.icns"]),
]
OPTIONS = {
    "argv_emulation": False,
    "packages": ["requests", "yt_dlp", "faster_whisper", "ctranslate2", "tokenizers", "numpy"],
    "includes": ["tkinter", "subprocess", "json", "os", "sys", "threading", "re", "xml", "asyncio"],
    "iconfile": "icon.icns",
    "plist": {
        "CFBundleName": "你是我的眼儿",
        "CFBundleDisplayName": "你是我的眼儿",
        "CFBundleIdentifier": "com.your.eye",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
        "LSBackgroundOnly": False,
    },
}

setup(
    app=APP,
    name="你是我的眼儿",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
