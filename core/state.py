"""统一状态/路径管理。所有模块从 state.py 获取路径，禁止硬编码。"""
import os

# === 核心路径 ===
USER_DOWNLOADS = os.path.expanduser("~/Downloads")
USER_OUTPUT_DIR = os.path.join(USER_DOWNLOADS, "111")
ACCEPT_OUTPUT_DIR = os.path.join(USER_DOWNLOADS, "你是我的眼儿_output")
DOUYIN_PROFILE_DIR = os.path.expanduser("~/.ni_shi_wo_de_yaner/douyin_profile")
PROJECT_MEMORY_FILE = os.path.join(USER_DOWNLOADS, "你是我的眼儿", "PROJECT_EXECUTION_MEMORY.md")
RUNTIME_MANIFEST_PATH = os.path.join(USER_DOWNLOADS, "你是我的眼儿_runtime_manifest_latest.json")

os.makedirs(USER_OUTPUT_DIR, exist_ok=True)
os.makedirs(ACCEPT_OUTPUT_DIR, exist_ok=True)
os.makedirs(DOUYIN_PROFILE_DIR, exist_ok=True)

def get_output_dir(platform: str, video_id: str, base_dir: str = None) -> str:
    """返回平台+视频的输出目录。base_dir 可选覆盖，否则从 config.json 读取（无则回退 USER_OUTPUT_DIR）"""
    if base_dir is None:
        try:
            from core.config import load_config
            cfg = load_config()
            base_dir = cfg.get("output_dir", "") or USER_OUTPUT_DIR
        except Exception:
            base_dir = USER_OUTPUT_DIR
    d = os.path.join(base_dir, platform, video_id)
    os.makedirs(d, exist_ok=True)
    return d
