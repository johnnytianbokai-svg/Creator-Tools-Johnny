#!/usr/bin/env python3
"""抖音 P0 验收脚本：检查输出目录文件完整性、ffprobe 双轨、transcript 非空"""
import sys, os, json, subprocess as sp

REQUIRED_FILES = [
    "video.mp4",
    "info.json",
    "comments.json",
    "comments.csv",
    "danmaku.json",
    "danmaku.csv",
    "transcript.json",
    "transcript.txt",
    "subtitles.srt",
]

def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        # 尝试从最近 douyin 输出目录推断
        base = "/Users/tianbokai/Downloads/111/douyin/"
        if not os.path.isdir(base):
            fail("缺少参数: output_dir")
        dirs = sorted(
            [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))],
            key=lambda d: os.path.getmtime(os.path.join(base, d)),
            reverse=True,
        )
        if not dirs:
            fail("无可用 douyin 输出目录")
        output_dir = os.path.join(base, dirs[0])
    else:
        output_dir = sys.argv[1]

    if not os.path.isdir(output_dir):
        fail(f"输出目录不存在: {output_dir}")

    # 1. 文件完整性
    missing = []
    for f in REQUIRED_FILES:
        fp = os.path.join(output_dir, f)
        if not os.path.isfile(fp):
            missing.append(f)
        elif os.path.getsize(fp) == 0 and f in ("video.mp4", "transcript.txt"):
            missing.append(f"{f} (empty)")
    if missing:
        fail(f"缺少文件: {', '.join(missing)}")

    # 2. info.json: 检查 api_source 不为 RENDER_DATA
    info_path = os.path.join(output_dir, "info.json")
    with open(info_path) as f:
        info = json.load(f)
    if info.get("api_source") == "RENDER_DATA":
        fail("info.api_source 仍为 RENDER_DATA，未切换到 aweme/detail")

    # 3. ffprobe 双轨
    video_path = os.path.join(output_dir, "video.mp4")
    ffprobe_bin = "ffprobe"
    for c in [
        "ffprobe",
        "/Applications/Trae CN.app/Contents/Resources/app/bin/ffprobe",
    ]:
        if os.path.isfile(c):
            ffprobe_bin = c
            break
    r = sp.run([ffprobe_bin, "-v", "quiet", "-print_format", "json",
                 "-show_streams", video_path],
                capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        fail(f"ffprobe 失败: {r.stderr.strip()[-200:]}")
    streams = json.loads(r.stdout).get("streams", [])
    has_video = any(s["codec_type"] == "video" for s in streams)
    has_audio = any(s["codec_type"] == "audio" for s in streams)
    if not has_video or not has_audio:
        fail(f"轨道缺失: video={has_video}, audio={has_audio}")

    # 4. transcript 非空
    txt_path = os.path.join(output_dir, "transcript.txt")
    with open(txt_path) as f:
        content = f.read().strip()
    if not content:
        fail("transcript.txt 为空")

    print("PASS")

if __name__ == "__main__":
    main()
