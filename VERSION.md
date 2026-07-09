---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 44de08c4f7781fe3119b98807a2d348b_af51f5107b6111f18401525400bff409
    ReservedCode1: 6UHEMKvYG+hT6g8l0tF4+LF4cmnj1y2kREBlmTkuu8saBhuJNKJwnPYmoM1IhMj8wIgQaBrpzu4H2LCOPXLqTjnXSZsDAdWtmlYmOiG3irKb33ARg00pCHmeR50kLj7CxN/jjdrjBcAOpnxwh2TWSp8AbKMl07gZv52m1ZBHw4bv7ZaKPspioC2YPbk=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 44de08c4f7781fe3119b98807a2d348b_af51f5107b6111f18401525400bff409
    ReservedCode2: 6UHEMKvYG+hT6g8l0tF4+LF4cmnj1y2kREBlmTkuu8saBhuJNKJwnPYmoM1IhMj8wIgQaBrpzu4H2LCOPXLqTjnXSZsDAdWtmlYmOiG3irKb33ARg00pCHmeR50kLj7CxN/jjdrjBcAOpnxwh2TWSp8AbKMl07gZv52m1ZBHw4bv7ZaKPspioC2YPbk=
---

# 版本说明 — 你是我的眼儿

## v1.0.1 (2026-07-09)

### 修复
- **ffprobe exit 8 阻塞点**：将 bilibili.py 和 douyin.py 中的 ffprobe 流检测改为 ffmpeg -i + stderr 关键字解析（`Video:` / `Audio:`），解决内置 ffprobe 实为 ffmpeg 同一二进制导致的 exit 8 失败
- **GUI 输出目录不生效**：`state.py` 的 `get_output_dir()` 改为优先从 `config.json` 读取 `output_dir`，后端输出目录与 GUI 选择一致

### 构建
- 新建内置 Python 3.11.9 + ffmpeg 8.0.1 的独立 .app
- 生成 DMG 安装包（190MB）
- launcher.sh 优先使用内置 Python

### 验收
- B站手动冒烟测试通过（视频 `BV17GTF6SEUm`）
- 输出目录正确指向 `~/Downloads/冒烟测试0709/`，不再错误输出到 `~/Downloads/111/`
- mp4 双轨（video + audio）、transcript 48 segments、SRT 48 条

---

## v1.0.0 (2026-07-08)

### 功能
- 初始发布版本
- 支持 B站视频下载、弹幕、评论、AI字幕
- 支持抖音视频下载、弹幕、评论
- faster-whisper 语音转录
- Tkinter GUI
*（内容由AI生成，仅供参考）*
