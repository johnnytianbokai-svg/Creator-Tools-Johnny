"""
B站视频处理：获取信息、弹幕、评论、字幕、下载视频（DASH合并）
"""
import re
import os
import sys
import ssl
import json
import requests
import xml.etree.ElementTree as ET
import urllib.request
from .cleaner import clean_danmaku, clean_comments, save_csv

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE
try:
    _SSL_CTX.minimum_version = ssl.TLSVersion.TLSv1_2
except AttributeError:
    pass


def extract_bv(url):
    m = re.search(r"BV[a-zA-Z0-9]{10}", url)
    if m:
        return m.group(0)
    m = re.search(r"bvid=([a-zA-Z0-9]+)", url)
    if m:
        return m.group(1)
    return None


def get_video_info(bv, logger):
    logger.log("正在获取B站视频信息...")
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bv}"
    r = requests.get(url, headers=HEADERS, timeout=15)
    data = r.json()
    if data["code"] != 0:
        raise Exception(f"获取视频信息失败: {data.get('message', '未知错误')}")
    v = data["data"]
    info = {
        "bvid": bv,
        "title": v["title"],
        "description": v["desc"],
        "duration": v["duration"],
        "cid": v["cid"],
        "aid": v["aid"],
        "tags": [t["tag_name"] for t in v.get("tags", [])] if v.get("tags") else [],
        "stat": v.get("stat", {}),
    }
    logger.log(f"视频标题: {info['title']}", step_advance=True)
    return info


def get_danmaku(cid, logger):
    logger.log("正在抓取弹幕数据...")
    url = f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.encoding = "utf-8"
    root = ET.fromstring(r.text)
    danmaku_list = []
    for d in root.findall("d"):
        p_attr = d.get("p", "")
        parts = p_attr.split(",")
        time_val = float(parts[0]) if len(parts) > 0 else 0
        dm_type = int(parts[1]) if len(parts) > 1 else 0
        font_size = int(parts[2]) if len(parts) > 2 else 25
        color = int(parts[3]) if len(parts) > 3 else 16777215
        timestamp = int(parts[4]) if len(parts) > 4 else 0
        pool = int(parts[5]) if len(parts) > 5 else 0
        user_hash = parts[6] if len(parts) > 6 else ""
        danmaku_list.append({
            "time": time_val,
            "text": d.text or "",
            "type": dm_type,
            "font_size": font_size,
            "color": color,
            "send_timestamp": timestamp,
            "pool": pool,
            "user_hash": user_hash,
        })
    logger.log(f"获取到 {len(danmaku_list)} 条弹幕（原始）", step_advance=True)
    return danmaku_list


def get_comments(oid, logger, max_pages=20):
    logger.log("正在抓取评论数据...")
    all_comments = []
    page = 1

    while page <= max_pages:
        url = f"https://api.bilibili.com/x/v2/reply?type=1&oid={oid}&pn={page}&sort=2"
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            http_status = r.status_code
            data = r.json()
            api_code = data.get("code", -1)

            if api_code != 0:
                logger.log(f"评论 第{page}页: HTTP={http_status}, code={api_code}, 本页0条, 累计{len(all_comments)}条")
                break

            replies = data.get("data", {}).get("replies") or []
            page_count = len(replies)
            for reply in replies:
                comment = {
                    "content": reply.get("content", {}).get("message", ""),
                    "user": reply.get("member", {}).get("uname", ""),
                    "time": reply.get("ctime", 0),
                    "likes": reply.get("like", 0),
                    "replies": [],
                }
                sub_replies = reply.get("replies") or []
                for sr in sub_replies:
                    comment["replies"].append({
                        "content": sr.get("content", {}).get("message", ""),
                        "user": sr.get("member", {}).get("uname", ""),
                        "time": sr.get("ctime", 0),
                        "likes": sr.get("like", 0),
                    })
                all_comments.append(comment)

            logger.log(f"评论 第{page}页: HTTP={http_status}, code={api_code}, 本页{page_count}条, 累计{len(all_comments)}条")

            if not replies:
                break

            total_pages = data.get("data", {}).get("page", {}).get("count", 0)
            if page >= total_pages:
                break
            page += 1
        except requests.exceptions.RequestException as e:
            logger.log(f"评论抓取第{page}页网络异常: {e}")
            break
        except Exception as e:
            logger.log(f"评论抓取第{page}页异常: {e}")
            break

    if len(all_comments) == 0:
        logger.log("评论为空或接口不可用")
    else:
        logger.log(f"获取到 {len(all_comments)} 条评论（原始）", step_advance=True)
    return all_comments


def _find_ffmpeg():
    """搜索 ffmpeg，优先 PATH，其次常见安装位置"""
    import shutil
    path = shutil.which("ffmpeg")
    if path:
        return "ffmpeg", "ffprobe"
    for d in [
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/Applications/Trae CN.app/Contents/Resources/app/bin",
        "/Applications/CapCut.app/Contents/Resources",
        "/Applications/Downie 4.app/Contents/Resources",
    ]:
        ffmpeg_path = os.path.join(d, "ffmpeg")
        ffprobe_path = os.path.join(d, "ffprobe")
        if os.path.isfile(ffmpeg_path) and os.path.isfile(ffprobe_path):
            return ffmpeg_path, ffprobe_path
    raise Exception("缺少 ffmpeg，无法合并 B站 DASH 音视频轨道。")


def download_bilibili_video(url, output_path, logger):
    import subprocess as sp

    # 0. SSL workaround（B站下载环境兼容性）
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
    except Exception:
        pass

    # 1. 检测 ffmpeg
    ffmpeg, ffprobe = _find_ffmpeg()
    try:
        sp.run([ffmpeg, "-version"], capture_output=True, timeout=10, check=True)
    except (sp.CalledProcessError, FileNotFoundError):
        raise Exception("缺少 ffmpeg，无法合并 B站 DASH 音视频轨道。")

    # 2. 配置 yt-dlp 环境（PATH 中加入 ffmpeg/ffprobe 所在目录）
    env = os.environ.copy()
    ffmpeg_dir = os.path.dirname(ffmpeg)
    if ffmpeg_dir not in env.get("PATH", "").split(":"):
        env["PATH"] = ffmpeg_dir + ":" + env.get("PATH", "")

    # 3. 选择 cookies 来源
    ytdlp = [sys.executable, "-m", "yt_dlp"]
    base_args = [
        "-f", "bestvideo*+bestaudio/best",
        "--merge-output-format", "mp4",
        "-o", output_path,
        "--no-playlist",
        "--no-check-certificate",
        "--downloader", "curl",
        "--retries", "5",
        "--socket-timeout", "30",
    ]

    cookie_sources = ["chrome", "safari"]
    cookie_used = None

    for browser in cookie_sources:
        try:
            test_cmd = ytdlp + ["--cookies-from-browser", browser] + base_args + [url]
            logger.log(f"尝试使用 {browser} cookie 下载视频...")
            r = sp.run(test_cmd, capture_output=True, text=True, timeout=600, env=env)
            if r.returncode == 0:
                cookie_used = browser
                break
            stderr_lower = (r.stderr or "").lower()
            if "412" in stderr_lower or "precondition failed" in stderr_lower:
                logger.log(f"{browser} cookie 被 B站拒绝 (HTTP 412)，尝试下一个来源")
                continue
            if "could not find" in stderr_lower or "no chrome" in stderr_lower or "no chromium" in stderr_lower:
                logger.log(f"未找到 {browser} 浏览器 cookie 数据，尝试下一个来源")
                continue
            # 非 cookie 相关错误，回退原生下载器重试
            err = r.stderr.strip()[-500:] if r.stderr else "未知错误"
            logger.log(f"curl 下载失败，回退原生下载器...")
            native_args = [a for a in test_cmd if a not in ("--downloader", "curl", "--retries", "5", "--socket-timeout", "30")]
            r2 = sp.run(native_args, capture_output=True, text=True, timeout=600, env=env)
            if r2.returncode == 0:
                cookie_used = browser
                break
            err2 = r2.stderr.strip()[-500:] if r2.stderr else "未知错误"
            raise Exception(f"curl 和原生均下载失败 (cookie={browser}):\n{err2}")
        except sp.TimeoutExpired:
            raise Exception(f"yt-dlp 下载超时 (cookie={browser})")
        except sp.SubprocessError as e:
            raise Exception(f"yt-dlp 进程异常 (cookie={browser}): {e}")

    if cookie_used is None:
        raise Exception(
            "B站下载需要浏览器登录 Cookie，请先在 Chrome 或 Safari 登录 B站后重试。\n"
            "如果浏览器已登录，请确认 yt-dlp 可以访问浏览器 cookie 存储。"
        )

    logger.log(f"视频下载成功 (cookie 来源: {cookie_used})", step_advance=True)

    # 4. 音视频轨验证 (使用 ffmpeg，因为内置 ffprobe 实际是 ffmpeg)
    try:
        probe = sp.run([ffmpeg, "-i", output_path], capture_output=True, text=True, timeout=30)
        # ffmpeg 将流信息输出到 stderr
        stderr_output = probe.stderr
        has_video = "Video:" in stderr_output
        has_audio = "Audio:" in stderr_output
        if not has_video or not has_audio:
            missing = []
            if not has_video:
                missing.append("video")
            if not has_audio:
                missing.append("audio")
            raise Exception(f"下载失败：mp4 不包含完整视频轨道和音频轨道。缺失: {', '.join(missing)}")
        logger.log(f"音视频轨验证通过: 含 video + audio 双轨")
    except Exception as e:
        raise Exception(f"音视频轨验证失败: {e}")

    if os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        logger.log(f"视频文件大小: {size_mb:.1f} MB")

    return output_path


def get_subtitles(bv, cid, aid, logger):
    logger.log("正在获取B站AI字幕...")
    result = {"available": False, "reason": "no bilibili ai subtitle found"}

    try:
        url = f"https://api.bilibili.com/x/player/v2?bvid={bv}&cid={cid}"
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            subs = data.get("data", {}).get("subtitle", {}).get("subtitles", [])
            if subs:
                sub_url = None
                for s in subs:
                    candidate = s.get("sub_url", "")
                    if candidate:
                        sub_url = candidate
                        break
                if sub_url:
                    if sub_url.startswith("//"):
                        sub_url = "https:" + sub_url
                    sr = requests.get(sub_url, headers=HEADERS, timeout=15)
                    if sr.status_code == 200:
                        result = sr.json()
                        logger.log("字幕获取成功", step_advance=True)
                        return result
            logger.log("该视频没有B站AI字幕")
        else:
            logger.log(f"字幕API返回 HTTP {r.status_code}")
    except Exception as e:
        logger.log(f"字幕获取异常: {e}")

    return result


def process_bilibili(url, output_dir, logger):
    """完整的 B站视频处理流程 —— 由 Adapter 调用"""
    import os

    bv = extract_bv(url)
    if not bv:
        raise Exception(f"无法从 URL 提取 BV 号: {url}")

    info = get_video_info(bv, logger)
    cid = info["cid"]
    aid = info.get("aid", 0)
    oid = info.get("aid", cid)

    info_path = os.path.join(output_dir, f"{bv}_info.json")
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    mp4_path = os.path.join(output_dir, f"{bv}.mp4")
    download_bilibili_video(url, mp4_path, logger)

    danmaku_raw = get_danmaku(cid, logger)
    danmaku = clean_danmaku(danmaku_raw)
    danmaku_json_path = os.path.join(output_dir, f"{bv}_danmaku.json")
    danmaku_csv_path = os.path.join(output_dir, f"{bv}_danmaku.csv")
    with open(danmaku_json_path, "w", encoding="utf-8") as f:
        json.dump(danmaku, f, ensure_ascii=False, indent=2)
    save_csv(danmaku, danmaku_csv_path, columns=["content", "time", "type", "color"])

    comments_raw = get_comments(oid, logger)
    comments = clean_comments(comments_raw)
    comments_json_path = os.path.join(output_dir, f"{bv}_comments.json")
    comments_csv_path = os.path.join(output_dir, f"{bv}_comments.csv")
    with open(comments_json_path, "w", encoding="utf-8") as f:
        json.dump(comments, f, ensure_ascii=False, indent=2)
    save_csv(comments, comments_csv_path, columns=["content", "user", "time", "likes"])

    subtitles = get_subtitles(bv, cid, aid, logger)
    subtitles_json_path = os.path.join(output_dir, f"{bv}_subtitles.json")
    subtitles_srt_path = os.path.join(output_dir, f"{bv}_subtitles.srt")
    if subtitles:
        with open(subtitles_json_path, "w", encoding="utf-8") as f:
            json.dump(subtitles, f, ensure_ascii=False, indent=2)
        _generate_srt(subtitles, subtitles_srt_path, logger)
    else:
        with open(subtitles_json_path, "w", encoding="utf-8") as f:
            json.dump({}, f)

    transcript_json_path = os.path.join(output_dir, f"{bv}_transcript.json")
    transcript_txt_path = os.path.join(output_dir, f"{bv}_transcript.txt")
    try:
        from .transcribe import transcribe_video
        transcript = transcribe_video(mp4_path, output_dir, bv, logger)
    except Exception as e:
        logger.log(f"转录失败: {e}")
        # 不写空文件——让异常传播，由 Adapter 判定 FAIL
        raise

    return {"id": bv, "output_dir": output_dir}


def _fmt_time(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _generate_srt(sub_data, srt_path, logger):
    body = sub_data.get("body", [])
    if not body:
        logger.log("字幕 body 为空，生成空 SRT")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("")
        return
    lines = []
    for i, item in enumerate(body, 1):
        start = item.get("from", 0)
        end = item.get("to", 0)
        content = item.get("content", "")
        lines.append(str(i))
        lines.append(f"{_fmt_time_srt(start)} --> {_fmt_time_srt(end)}")
        lines.append(content)
        lines.append("")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _fmt_time_srt(seconds):
    s = float(seconds)
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = int(s % 60)
    ms = int((s - int(s)) * 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"
