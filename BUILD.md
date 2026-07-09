---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 44de08c4f7781fe3119b98807a2d348b_b055808d7b6111f18401525400bff409
    ReservedCode1: heMcKaKrhHczR1s23+RfmzQ0TemZYEtoHAL1pBsYUVNHtRqJuUOJZt9msr3ZOuG7ih4kkxVaLkjgBYQlsrQ/kvlKRqLFJJTQJQ7Ce3e6Al0mw1UcmTP83dXrWD/UdGQP+d+SNGeA29kPcH4FtyA8gWrH64eZa4L9zG2vToA+e2qaCtDxzSKTl3CmamM=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 44de08c4f7781fe3119b98807a2d348b_b055808d7b6111f18401525400bff409
    ReservedCode2: heMcKaKrhHczR1s23+RfmzQ0TemZYEtoHAL1pBsYUVNHtRqJuUOJZt9msr3ZOuG7ih4kkxVaLkjgBYQlsrQ/kvlKRqLFJJTQJQ7Ce3e6Al0mw1UcmTP83dXrWD/UdGQP+d+SNGeA29kPcH4FtyA8gWrH64eZa4L9zG2vToA+e2qaCtDxzSKTl3CmamM=
---

# 打包说明 — 你是我的眼儿

## 构建 macOS .app 包

### 前置条件
- macOS 系统
- Python 3.11+（建议使用内置 Python 版本）
- ffmpeg（建议使用 8.0+）
- 所有 Python 依赖已安装（见 `requirements.txt`）

### 手动构建步骤

```bash
# 1. 确认 Python + ffmpeg 路径
BUILTIN_PY="<path>/python/bin/python3"
FFMPEG_DIR="<path>/ffmpeg"

# 2. 创建 .app 目录结构
APP_NAME="你是我的眼儿.app"
mkdir -p "$APP_NAME/Contents/MacOS"
mkdir -p "$APP_NAME/Contents/Resources"

# 3. 复制启动脚本
cp launcher.sh "$APP_NAME/Contents/MacOS/"
chmod +x "$APP_NAME/Contents/MacOS/launcher.sh"

# 4. 复制源码
cp app.py "$APP_NAME/Contents/Resources/"
cp -R core "$APP_NAME/Contents/Resources/"
cp config.json "$APP_NAME/Contents/Resources/"
cp icon.icns "$APP_NAME/Contents/Resources/"
cp icon.png "$APP_NAME/Contents/Resources/"

# 5. 复制内置 Python
cp -R "$BUILTIN_PY" "$APP_NAME/Contents/Resources/python/"

# 6. 复制内置 ffmpeg
cp -R "$FFMPEG_DIR" "$APP_NAME/Contents/Resources/ffmpeg/"

# 7. 创建 Info.plist（见下方模板）

# 8. 清理 __pycache__
find "$APP_NAME" -name "__pycache__" -type d -exec rm -rf {} +
```

### Info.plist 模板

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launcher.sh</string>
    <key>CFBundleIconFile</key>
    <string>icon</string>
    <key>CFBundleIdentifier</key>
    <string>com.your.eye</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>你是我的眼儿</string>
    <key>CFBundleDisplayName</key>
    <string>你是我的眼儿</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.1</string>
    <key>CFBundleVersion</key>
    <string>1.0.1</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
```

### 生成 DMG

```bash
# 创建 DMG 临时目录
mkdir -p dmg_temp
cp -R "你是我的眼儿.app" dmg_temp/
ln -s /Applications dmg_temp/Applications

# 生成 DMG
hdiutil create \
    -volname "你是我的眼儿 1.0.1" \
    -srcfolder dmg_temp \
    -ov -format UDZO -imagekey zlib-level=9 \
    "你是我的眼儿_1.0.1.dmg"

# 清理临时目录
rm -rf dmg_temp
```
*（内容由AI生成，仅供参考）*
