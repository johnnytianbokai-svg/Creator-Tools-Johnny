"""统一处理结果契约：所有 Adapter 返回 ProcessResult"""
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ProcessResult:
    platform: str
    video_id: str
    output_dir: str
    files: Dict[str, str] = field(default_factory=dict)  # filename -> abs path
    status: str = ""  # PASS / FAIL
    error: Optional[str] = None
    runtime_manifest_path: str = ""

    # 文件状态
    video: bool = False
    info: bool = False
    comments_json: bool = False
    comments_csv: bool = False
    danmaku_json: bool = False
    danmaku_csv: bool = False
    transcript_json: bool = False
    transcript_txt: bool = False
    subtitles_srt: bool = False

    # 内容级校验
    transcript_segments_count: int = 0
    transcript_txt_size: int = 0
    subtitles_srt_size: int = 0

    def set_file_states(self, output_dir: str):
        """根据 output_dir 中文件存在性设置状态，兼容 B站 {video_id}_* 和 抖音 * 命名"""
        import os
        checks = {
            "video": ["video.mp4", f"{self.video_id}.mp4"],
            "info": ["info.json", f"{self.video_id}_info.json"],
            "comments_json": ["comments.json", f"{self.video_id}_comments.json"],
            "comments_csv": ["comments.csv", f"{self.video_id}_comments.csv"],
            "danmaku_json": ["danmaku.json", f"{self.video_id}_danmaku.json"],
            "danmaku_csv": ["danmaku.csv", f"{self.video_id}_danmaku.csv"],
            "transcript_json": ["transcript.json", f"{self.video_id}_transcript.json"],
            "transcript_txt": ["transcript.txt", f"{self.video_id}_transcript.txt"],
            "subtitles_srt": ["subtitles.srt", f"{self.video_id}_subtitles.srt"],
        }
        for attr, candidates in checks.items():
            found = False
            for fname in candidates:
                fp = os.path.join(output_dir, fname)
                if os.path.isfile(fp):
                    setattr(self, attr, True)
                    self.files[fname] = fp
                    found = True
                    break
            if not found:
                setattr(self, attr, False)

    def validate_content(self, output_dir: str):
        """读取 transcript 文件校验内容完整性"""
        import os, json
        # transcript.json: 存在 + segments > 0
        for fname in ["transcript.json", f"{self.video_id}_transcript.json"]:
            fp = os.path.join(output_dir, fname)
            if os.path.isfile(fp):
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self.transcript_segments_count = len(data.get("segments", []))
                except Exception:
                    self.transcript_segments_count = 0
                break

        # transcript.txt: size > 0
        for fname in ["transcript.txt", f"{self.video_id}_transcript.txt"]:
            fp = os.path.join(output_dir, fname)
            if os.path.isfile(fp):
                self.transcript_txt_size = os.path.getsize(fp)
                break

        # subtitles.srt: 如果存在 size > 0
        for fname in ["subtitles.srt", f"{self.video_id}_subtitles.srt"]:
            fp = os.path.join(output_dir, fname)
            if os.path.isfile(fp):
                self.subtitles_srt_size = os.path.getsize(fp)
                break

    def transcript_valid(self) -> bool:
        """transcript 空文件 = FAIL"""
        return (
            self.transcript_json
            and self.transcript_txt
            and self.transcript_segments_count > 0
            and self.transcript_txt_size > 0
        )

    def all_files_present(self) -> bool:
        return all([
            self.video, self.info,
            self.comments_json, self.comments_csv,
            self.danmaku_json, self.danmaku_csv,
            self.transcript_json, self.transcript_txt, self.subtitles_srt,
        ]) and self.transcript_valid()
