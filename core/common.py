"""
通用工具：日志回调、进度回调、文件管理
"""
import os
import json
from datetime import datetime
from .config import load_config


class TaskLogger:
    def __init__(self, log_callback=None, progress_callback=None):
        self.log_cb = log_callback
        self.progress_cb = progress_callback
        self._current = 0
        self._total = 7

    def set_steps(self, total):
        self._total = total
        self._current = 0

    def log(self, msg, step_advance=False):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        if self.log_cb:
            self.log_cb(line)
        print(line)
        if step_advance and self.progress_cb:
            self._current = min(self._current + 1, self._total)
            pct = int(self._current / max(self._total, 1) * 100)
            self.progress_cb(pct)

    def done(self):
        if self.progress_cb:
            self.progress_cb(100)


def ensure_output_dir(platform, bv_or_id, base_dir=None):
    if base_dir is None:
        cfg = load_config()
        base_dir = cfg.get("output_dir", os.path.expanduser("~/Downloads/你是我的眼儿"))
    strategy = load_config().get("folder_strategy", "platform/bvid")
    if strategy == "flat":
        d = base_dir
    elif strategy == "platform":
        d = os.path.join(base_dir, platform)
    else:
        d = os.path.join(base_dir, platform, bv_or_id)
    os.makedirs(d, exist_ok=True)
    return d


def save_json(data, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath
