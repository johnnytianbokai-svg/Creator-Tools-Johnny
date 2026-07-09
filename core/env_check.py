"""
统一环境检查模块
供"环境检查"窗口和 .app 启动脚本共用
返回结构化结果，UI 层直接消费，不需要自己写检测逻辑
"""

import os
import subprocess
import sys
from .config import load_config


class EnvResult:
    """单条检查结果"""
    def __init__(self, name, status="unknown", detail="", fix_cmd=None, fix_label=None):
        """
        status: "ok" | "warn" | "fail"
        fix_cmd: 一键修复命令（Shell 命令或 None 表示不可自动修复）
        """
        self.name = name
        self.status = status
        self.detail = detail
        self.fix_cmd = fix_cmd
        self.fix_label = fix_label


def _run(cmd, timeout=15):
    """执行命令，返回 (success, output)"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout.strip() or r.stderr.strip())
        return r.returncode == 0, out[:200]
    except FileNotFoundError:
        return False, "命令不可用"
    except subprocess.TimeoutExpired:
        return False, "执行超时"
    except Exception as e:
        return False, str(e)[:120]


def _find_python():
    """找到可用的 Python3 路径"""
    # 优先 Marvis 内置
    marvis_base = os.path.expanduser(
        "~/Library/Application Support/com.tencent.mac.marvis/components/MarvisAgent/Versions"
    )
    if os.path.isdir(marvis_base):
        for ver_dir in sorted(os.listdir(marvis_base), reverse=True):
            py = os.path.join(marvis_base, ver_dir, "runtime", "python311", "bin", "python3")
            if os.path.isfile(py):
                return py
    # 备选
    for p in ["/opt/homebrew/bin/python3", "/usr/local/bin/python3", "/usr/bin/python3"]:
        if os.path.isfile(p):
            return p
    return sys.executable


def check_all() -> list:
    """
    执行全部环境检查，返回 EnvResult 列表。
    调用方只需要遍历列表即可。
    """
    cfg = load_config()
    py = _find_python()
    results = []

    # --- Python 版本 ---
    ok, out = _run([py, "--version"])
    results.append(EnvResult("Python 版本",
        status="ok" if ok else "fail",
        detail=out if ok else "未找到 Python3",
        fix_cmd=None,
        fix_label=None))

    # --- pip ---
    ok, out = _run([py, "-m", "pip", "--version"])
    results.append(EnvResult("pip 包管理器",
        status="ok" if ok else "fail",
        detail=out.split("\n")[0] if ok else "pip 不可用",
        fix_cmd=f'"{py}" -m ensurepip' if not ok else None,
        fix_label="安装 pip" if not ok else None))

    # --- requests ---
    ok, out = _run([py, "-c", "import requests; print(requests.__version__)"])
    results.append(EnvResult("requests 库",
        status="ok" if ok else "fail",
        detail=f"v{out}" if ok else "未安装",
        fix_cmd=f'"{py}" -m pip install requests' if not ok else None,
        fix_label="安装 requests" if not ok else None))

    # --- yt-dlp ---
    ok, out = _run([py, "-c", "import yt_dlp; print(yt_dlp.version.__version__)"])
    results.append(EnvResult("yt-dlp 库 (B站下载)",
        status="ok" if ok else "fail",
        detail=f"v{out}" if ok else "未安装",
        fix_cmd=f'"{py}" -m pip install yt-dlp' if not ok else None,
        fix_label="安装 yt-dlp" if not ok else None))

    # --- faster-whisper ---
    ok, out = _run([py, "-c", "from faster_whisper import WhisperModel; print('OK')"])
    results.append(EnvResult("faster-whisper 库 (语音转文字)",
        status="ok" if ok else "fail",
        detail="已安装" if ok else "未安装（首次启动会自动下载模型）",
        fix_cmd=f'"{py}" -m pip install faster-whisper' if not ok else None,
        fix_label="安装 faster-whisper" if not ok else None))

    # --- playwright 库 ---
    ok, out = _run([py, "-c", "from playwright.sync_api import sync_playwright; print('OK')"])
    results.append(EnvResult("playwright 库 (抖音浏览器)",
        status="ok" if ok else "fail",
        detail="已安装" if ok else "未安装",
        fix_cmd=f'"{py}" -m pip install playwright' if not ok else None,
        fix_label="安装 playwright" if not ok else None))

    # --- Chromium 浏览器 ---
    chromium_ok = False
    if ok:  # playwright 已安装，检查 chromium
        chromium_ok, out = _run([py, "-c", """
import subprocess, sys
r = subprocess.run([sys.executable, '-m', 'playwright', 'install', '--dry-run', 'chromium'],
                   capture_output=True, text=True, timeout=30)
sys.exit(0 if 'already' in r.stdout.lower() or 'installed' in r.stdout.lower() else 1)
"""])
    results.append(EnvResult("Chromium 浏览器 (抖音需要)",
        status="ok" if chromium_ok else "fail",
        detail="已安装" if chromium_ok else ("未安装（约150MB）" if ok else "需先安装 playwright"),
        fix_cmd=f'"{py}" -m playwright install chromium' if ok and not chromium_ok else None,
        fix_label="安装 Chromium" if ok and not chromium_ok else None))

    # --- 配置类检查 ---
    pip_mirror = cfg.get("pip_mirror", "")
    results.append(EnvResult("pip 镜像源",
        status="ok" if pip_mirror else "warn",
        detail=pip_mirror if pip_mirror else "未配置（国内建议设置清华源）",
        fix_cmd=None, fix_label=None))

    hf_mirror = cfg.get("hf_mirror", "")
    results.append(EnvResult("HuggingFace 镜像",
        status="ok" if hf_mirror else "warn",
        detail=hf_mirror if hf_mirror else "未配置（国内建议设置 hf-mirror.com）",
        fix_cmd=None, fix_label=None))

    output_dir = cfg.get("output_dir", "")
    exists = os.path.isdir(output_dir) if output_dir else False
    results.append(EnvResult("输出目录",
        status="ok" if exists else "warn",
        detail=f"{output_dir} {'(存在)' if exists else '(不存在，将自动创建)'}" if output_dir else "未设置",
        fix_cmd=None, fix_label=None))

    return results


def install_dependency(fix_cmd: str, name: str) -> tuple:
    """
    执行依赖安装，返回 (success, output_message)
    """
    try:
        r = subprocess.run(fix_cmd, shell=True, capture_output=True, text=True, timeout=300)
        if r.returncode == 0:
            return True, f"{name} 安装成功"
        else:
            err = (r.stderr or r.stdout).strip()[-200:]
            return False, f"安装失败: {err}"
    except subprocess.TimeoutExpired:
        return False, f"{name} 安装超时（请检查网络）"
    except Exception as e:
        return False, f"安装异常: {str(e)[:120]}"


def is_playwright_ready() -> bool:
    """快速检测抖音功能是否可用"""
    try:
        from playwright.sync_api import sync_playwright
        # 检查 chromium 是否已安装
        import subprocess, sys
        r = subprocess.run(
            [sys.executable, '-m', 'playwright', 'install', '--dry-run', 'chromium'],
            capture_output=True, text=True, timeout=30
        )
        return "already" in r.stdout.lower() or "installed" in r.stdout.lower()
    except ImportError:
        return False
    except Exception:
        return False
