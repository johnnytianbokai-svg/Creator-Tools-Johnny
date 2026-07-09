"""
语音转文字模块 - 基于faster-whisper
"""
import os
from faster_whisper import WhisperModel
from .config import load_config

# 全局单例
_model = None
_model_name = None


def _get_model():
    global _model, _model_name
    cfg = load_config()
    name = cfg.get("whisper_model", "small")
    if _model is not None and _model_name == name:
        return _model
    os.environ["HF_ENDPOINT"] = cfg.get("hf_mirror", "https://hf-mirror.com")
    device = cfg.get("whisper_device", "cpu")
    compute = cfg.get("whisper_compute", "int8")
    _model = WhisperModel(name, device=device, compute_type=compute)
    _model_name = name
    return _model


def transcribe_audio(audio_path, logger):
    """将音频文件转为字幕JSON"""
    logger.log("正在加载语音识别模型...")
    model = _get_model()
    logger.log("正在转写音频（这可能需要1-3分钟）...")
    segments, info = model.transcribe(audio_path, language="zh", vad_filter=True)
    subs = []
    for seg in segments:
        subs.append({
            "start_time": round(seg.start, 2),
            "end_time": round(seg.end, 2),
            "text": seg.text.strip(),
        })
    logger.log(f"转写完成，共 {len(subs)} 段字幕", step_advance=True)
    return subs


def transcribe_video(video_path, output_dir, bv, logger):
    """从视频mp4转录字幕，生成 transcript.json / transcript.txt / subtitles.srt

    返回 dict: {available, source, language, segments, text}
    """
    import subprocess as sp
    import json

    temp_dir = os.path.join(output_dir, ".temp_transcribe")
    os.makedirs(temp_dir, exist_ok=True)
    audio_path = os.path.join(temp_dir, f"{bv}.mp3")

    # 1. 提取音频
    logger.log("正在从视频提取音频轨道...")
    ffmpeg_candidates = [
        "/Applications/Downie 4.app/Contents/Resources/ffmpeg",
        "ffmpeg",
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
    ]
    ffmpeg_bin = "ffmpeg"
    for c in ffmpeg_candidates:
        if os.path.isfile(c):
            ffmpeg_bin = c
            break

    r = sp.run([
        ffmpeg_bin, "-y", "-i", video_path,
        "-vn", "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1",
        audio_path,
    ], capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise Exception(f"音频提取失败: {r.stderr.strip()[-300:]}")

    # 2. 转录
    segments = transcribe_audio(audio_path, logger)
    full_text = "\n".join(s["text"] for s in segments)

    # 3. 生成 transcript.json
    transcript = {
        "available": True,
        "source": "whisper",
        "language": "zh",
        "segments": segments,
        "text": full_text,
    }
    json_path = os.path.join(output_dir, f"{bv}_transcript.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)
    logger.log(f"  transcript.json: {json_path}")

    # 4. 生成 transcript.txt
    txt_path = os.path.join(output_dir, f"{bv}_transcript.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)
    logger.log(f"  transcript.txt: {txt_path}")

    # 5. 生成 subtitles.srt
    srt_path = os.path.join(output_dir, f"{bv}_subtitles.srt")
    try:
        srt_lines = []
        for i, seg in enumerate(segments, 1):
            start_h = int(seg["start_time"] // 3600)
            start_m = int((seg["start_time"] % 3600) // 60)
            start_s = seg["start_time"] % 60
            end_h = int(seg["end_time"] // 3600)
            end_m = int((seg["end_time"] % 3600) // 60)
            end_s = seg["end_time"] % 60
            start_fmt = f"{start_h:02d}:{start_m:02d}:{start_s:06.3f}".replace(".", ",")
            end_fmt = f"{end_h:02d}:{end_m:02d}:{end_s:06.3f}".replace(".", ",")
            srt_lines.append(f"{i}\n{start_fmt} --> {end_fmt}\n{seg['text']}\n")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_lines))
        logger.log(f"  subtitles.srt: {srt_path}")
    except Exception as e:
        logger.log(f"  subtitles.srt 生成失败: {e}")

    # 6. 清理临时文件
    try:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass

    return transcript
