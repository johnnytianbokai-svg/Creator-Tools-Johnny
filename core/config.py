"""
配置管理模块
"""
import os
import json

CONFIG_DIR = os.path.expanduser("~/Downloads/你是我的眼儿")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULTS = {
    "output_dir": os.path.expanduser("~/Downloads/你是我的眼儿"),
    "folder_strategy": "platform/bvid",
    "pip_mirror": "https://pypi.tuna.tsinghua.edu.cn/simple",
    "hf_mirror": "https://hf-mirror.com",
    "whisper_model": "small",
    "whisper_device": "cpu",
    "whisper_compute": "int8",
}


def load_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
            for k, v in DEFAULTS.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
    return dict(DEFAULTS)


def save_config(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def get_output_dir(cfg=None):
    if cfg is None:
        cfg = load_config()
    return cfg.get("output_dir", DEFAULTS["output_dir"])
