#!/usr/bin/env python3
"""B站 P0 验收脚本：检查指定 B站 URL 对应的输出产物是否完整"""
import sys
import os
import json
import subprocess as sp

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.config import load_config
from core.bilibili import extract_bv, _find_ffmpeg


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        fail("缺少参数: B站 URL")

    url = sys.argv[1]
    bv = extract_bv(url)
    if not bv:
        fail("无法从 URL 提取 BV 号")

    cfg = load_config()
    base = cfg.get("output_dir", os.path.expanduser("~/Downloads/你是我的眼儿"))
    output_dir = os.path.join(base, "bilibili", bv)

    if not os.path.isdir(output_dir):
        fail(f"输出目录不存在: {output_dir}")

    checks = [
        ("mp4 文件", os.path.join(output_dir, f"{bv}.mp4")),
        ("info.json", os.path.join(output_dir, f"{bv}_info.json")),
        ("danmaku.json", os.path.join(output_dir, f"{bv}_danmaku.json")),
        ("danmaku.csv", os.path.join(output_dir, f"{bv}_danmaku.csv")),
        ("comments.json", os.path.join(output_dir, f"{bv}_comments.json")),
        ("comments.csv", os.path.join(output_dir, f"{bv}_comments.csv")),
        ("subtitles.json", os.path.join(output_dir, f"{bv}_subtitles.json")),
    ]

    for label, path in checks:
        if not os.path.isfile(path):
            fail(f"缺失: {label} ({path})")

    # ffprobe 验证 mp4
    mp4_path = os.path.join(output_dir, f"{bv}.mp4")
    try:
        _, ffprobe = _find_ffmpeg()
        probe = sp.run([
            ffprobe, "-v", "quiet", "-print_format", "json",
            "-show_streams", mp4_path
        ], capture_output=True, text=True, timeout=30, check=True)
        streams = json.loads(probe.stdout).get("streams", [])
        has_video = any(s.get("codec_type") == "video" for s in streams)
        has_audio = any(s.get("codec_type") == "audio" for s in streams)
        if not has_video:
            fail("mp4 不包含 video stream")
        if not has_audio:
            fail("mp4 不包含 audio stream")
    except sp.CalledProcessError as e:
        fail(f"ffprobe 失败: {e.stderr.strip()[-200:] if e.stderr else e}")
    except FileNotFoundError:
        fail("ffprobe 命令不可用")
    except Exception as e:
        fail(f"ffprobe 错误: {e}")

    print("PASS")


if __name__ == "__main__":
    main()
