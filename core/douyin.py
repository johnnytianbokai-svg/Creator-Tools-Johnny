"""
抖音视频处理：Playwright persistent context + 登录态 + 信息提取 + 下载 + 评论 + 弹幕 + 转录
"""
import re
import os
import json
import time
import asyncio
import requests
import subprocess as sp
from .cleaner import clean_danmaku, clean_comments, save_csv

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
}

# 登录态持久化目录
_DOUYIN_PROFILE_DIR = os.path.expanduser("~/.ni_shi_wo_de_yaner/douyin_profile")
os.makedirs(_DOUYIN_PROFILE_DIR, exist_ok=True)


def extract_video_id(url):
    """从抖音 URL 提取 video_id"""
    m = re.search(r"/video/(\d+)", url)
    if m:
        return m.group(1)
    m = re.search(r"/note/(\d+)", url)
    if m:
        return m.group(1)
    return None


async def _wait_for_login(page, logger, timeout=120):
    """等待用户在非 headless 浏览器中完成登录（扫码或手机登录）"""
    logger.log("请在浏览器窗口中完成抖音登录（扫码或手机号）...")
    logger.log(f"等待超时: {timeout} 秒")
    start = time.time()
    while time.time() - start < timeout:
        try:
            # 检查是否已登录：看页面是否有 "我" 或用户头像等元素
            logged_in = await page.evaluate("""
                () => {
                    const hasLoginBtn = document.querySelector('[class*="login"]') ||
                                       document.querySelector('text="登录"');
                    const hasUserMenu = document.querySelector('[class*="user"]') ||
                                        document.querySelector('[class*="avatar"]') ||
                                        document.querySelector('[data-e2e="user-avatar"]');
                    // 如果没找到登录按钮且有用户元素，认为已登录
                    if (!hasLoginBtn && hasUserMenu) return true;
                    // 检查 localStorage 中的 token
                    const token = localStorage.getItem('token') ||
                                 localStorage.getItem('passport_csrf_token');
                    return !!token;
                }
            """)
            if logged_in:
                logger.log("检测到登录态，继续执行...")
                return True
        except Exception:
            pass
        await asyncio.sleep(3)
    logger.log("登录等待超时")
    return False


async def _check_login_state(context, page, logger):
    """检测 persistent context 中是否已有有效登录态"""
    try:
        await page.goto("https://www.douyin.com", wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2)
        logged_in = await page.evaluate("""
            () => {
                // 检查 localStorage 中的登录凭证（抖音关键 cookie 是 httpOnly，document.cookie 不可见）
                const keys = Object.keys(localStorage);
                const loginKeys = ['user_info_passport', 'has_login_show', 'login_sid_guard',
                                   'sid_guard', 'token', 'passport_csrf_token'];
                for (const k of loginKeys) {
                    for (const lk of keys) {
                        if (lk.includes(k)) {
                            const val = localStorage.getItem(lk);
                            if (val && val.length > 5) return true;
                        }
                    }
                }
                // 检查页面是否显示已登录特征（URL 跳转到推荐页/jingxuan 等）
                const url = window.location.href;
                if (url.includes('/jingxuan') || url.includes('/recommend') || url.includes('/discover')) {
                    const title = document.title;
                    if (title && !title.includes('登录')) return true;
                }
                return false;
            }
        """)
        if logged_in:
            logger.log("已检测到有效登录态（persistent profile）")
            return True
        else:
            logger.log("未检测到登录态，需要用户登录")
            return False
    except Exception as e:
        logger.log(f"登录态检测异常: {e}")
        return False


async def _follow_redirect(page, url, logger):
    """跟随短链接重定向，返回 final_url 和 aweme_id"""
    logger.log(f"原始 URL: {url}")
    resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    final_url = page.url
    logger.log(f"重定向后 URL: {final_url}")

    aweme_id = extract_video_id(final_url)
    if not aweme_id:
        # 尝试从短链接路径提取
        m = re.search(r"v\.douyin\.com/(\w+)", url)
        if m:
            logger.log("从短链接重定向解析 video_id...")
            await asyncio.sleep(2)
            final_url = page.url
            aweme_id = extract_video_id(final_url)

    logger.log(f"解析 video_id: {aweme_id or '失败'}")
    return final_url, aweme_id


async def _get_video_info(page, aweme_id, final_url, logger):
    """通过 response 拦截捕获 aweme/detail API 响应，浏览器 fetch 兜底"""
    info = {"id": aweme_id or "", "source_url": final_url, "final_url": final_url,
            "login_state_used": True, "api_source": "aweme/detail_response_intercept"}

    aweme_detail = None
    captured_event = asyncio.Event()

    async def handle_response(response):
        nonlocal aweme_detail
        if "/aweme/v1/web/aweme/detail/" in response.url:
            try:
                body = await response.json()
                ad = body.get("aweme_detail")
                if ad and ad.get("video"):
                    aweme_detail = ad
                    captured_event.set()
            except Exception:
                pass

    page.on("response", handle_response)

    try:
        logger.log("注册 aweme/detail 响应拦截，重新加载页面以触发 API...")
        try:
            await page.reload(wait_until="domcontentloaded", timeout=30000)
        except Exception:
            # reload 可能超时但 API 响应可能已到达
            pass

        try:
            await asyncio.wait_for(captured_event.wait(), timeout=15.0)
            logger.log("成功拦截 aweme/detail 响应")
        except asyncio.TimeoutError:
            logger.log("响应拦截超时 (15s)，尝试浏览器 fetch 兜底...")
            try:
                raw = await page.evaluate("""
                    async ([aweme_id]) => {
                        const resp = await fetch(
                            'https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id=' + aweme_id,
                            { headers: { 'Referer': 'https://www.douyin.com/' } }
                        );
                        return await resp.text();
                    }
                """, [aweme_id])
                if raw:
                    import json as _json
                    data = _json.loads(raw)
                    ad = data.get("aweme_detail")
                    if ad and ad.get("video"):
                        aweme_detail = ad
                        logger.log("浏览器 fetch 兜底成功")
            except Exception as e:
                logger.log(f"浏览器 fetch 兜底失败: {e}")
    finally:
        page.remove_listener("response", handle_response)

    if not aweme_detail:
        raise Exception("FAIL: 无法获取 aweme/detail，RENDER_DATA 已失效，浏览器 API 拦截失败。")

    # 从 aweme_detail 提取视频信息
    video_data = aweme_detail.get("video", {})
    author = aweme_detail.get("author", {})
    info.update({
        "title": aweme_detail.get("desc", ""),
        "author": author.get("nickname", "") or author.get("unique_id", ""),
        "duration": aweme_detail.get("duration", 0) or video_data.get("duration", 0),
        "statistics": aweme_detail.get("statistics", {}),
    })
    logger.log(f"通过 aweme/detail 获取视频信息: {info.get('title', '')[:60]}")

    # 提取视频 URL
    video_url_str, url_source = _extract_video_url(video_data, logger)
    info["video_url_source"] = url_source

    if not video_url_str:
        raise Exception("FAIL: 无可用抖音视频 URL。")
    info["watermark_removed"] = True  # download_addr 通常无水印

    return info, video_url_str


def _extract_video_url(video_data, logger):
    """从 aweme_detail.video 提取视频 URL，优先 download_addr > play_addr > bit_rate"""
    video_url = ""
    source = ""

    def _get_first_url(source_obj):
        """从 url_list 提取第一个 URL"""
        if isinstance(source_obj, list) and source_obj:
            return source_obj[0]
        if isinstance(source_obj, str) and source_obj.startswith("http"):
            return source_obj
        if isinstance(source_obj, dict):
            ul = source_obj.get("url_list", [])
            if ul and isinstance(ul, list):
                return ul[0]
        return ""

    # 1. download_addr.url_list（优先，通常无水印）
    da = video_data.get("download_addr", {})
    if isinstance(da, dict):
        video_url = _get_first_url(da.get("url_list", []))
        if video_url:
            source = "download_addr"

    # 2. play_addr.url_list
    if not video_url:
        pa = video_data.get("play_addr", {})
        if isinstance(pa, dict):
            video_url = _get_first_url(pa.get("url_list", []))
            if video_url:
                source = "play_addr"

    # 3. bit_rate[n].play_addr.url_list
    if not video_url:
        bit_rates = video_data.get("bit_rate", [])
        if isinstance(bit_rates, list):
            for br in bit_rates:
                pa = br.get("play_addr", {})
                if isinstance(pa, dict):
                    video_url = _get_first_url(pa.get("url_list", []))
                    if video_url:
                        source = "bit_rate"
                        break

    if video_url:
        video_url = video_url.replace("playwm", "play").replace("watermark=1", "watermark=0")

    logger.log(f"视频 URL 来源: {source}")
    return video_url, source


def _download_video(video_url, save_path, logger):
    """流式下载视频文件"""
    logger.log("正在下载视频...")
    try:
        headers = {**HEADERS, "Referer": "https://www.douyin.com/"}
        r = requests.get(video_url, headers=headers, timeout=120, stream=True)
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        last_log_pct = -1
        with open(save_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = int(downloaded / total * 100)
                        if pct >= last_log_pct + 10:
                            last_log_pct = pct
                            logger.log(f"  下载进度: {pct}%")
        file_size = downloaded / 1024
        logger.log(f"视频下载完成 ({file_size:.0f} KB)", step_advance=True)
        return save_path
    except Exception as e:
        raise Exception(f"视频下载失败: {e}")


def _ffprobe_check(video_path, logger):
    """使用 ffmpeg 检查视频是否有 video + audio 双轨（内置 ffprobe 实际是 ffmpeg）"""
    logger.log("正在检查视频轨道...")
    # P2C 部署：优先使用内置 ffmpeg（因为 ffprobe 与 ffmpeg 是同一二进制）
    _app_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _builtin_ffmpeg = os.path.join(_app_base, "ffmpeg", "ffmpeg")
    ffmpeg_candidates = [
        "ffmpeg",
        _builtin_ffmpeg,
        "/Applications/Trae CN.app/Contents/Resources/app/bin/ffmpeg",
        "/Applications/Downie 4.app/Contents/Resources/ffmpeg",
    ]
    ffmpeg_bin = "ffmpeg"
    for c in ffmpeg_candidates:
        if os.path.isfile(c):
            ffmpeg_bin = c
            break

    try:
        r = sp.run([ffmpeg_bin, "-i", video_path],
                    capture_output=True, text=True, timeout=30)
        # ffmpeg 将流信息输出到 stderr
        stderr_output = r.stderr
        has_video = "Video:" in stderr_output
        has_audio = "Audio:" in stderr_output

        if not has_video:
            raise Exception("视频流缺失")
        if not has_audio:
            raise Exception("音频流缺失")

        logger.log(f"视频轨道检查通过: video={has_video}, audio={has_audio}")
        return True
    except Exception:
        raise Exception(f"ffmpeg 流检查失败: {r.stderr.strip()[-200:] if r.stderr else '无输出'}")


async def _get_comments_from_api(aweme_id, page, logger, max_pages=10):
    """通过浏览器原生 fetch 分页抓取评论（绕过 page.request 反爬限制）"""
    logger.log("正在抓取评论...")
    all_comments = []
    cursor = 0
    page_num = 0

    while page_num < max_pages:
        url = (
            f"https://www.douyin.com/aweme/v1/web/comment/list/?"
            f"aweme_id={aweme_id}&cursor={cursor}&count=20"
        )
        try:
            raw = await page.evaluate("""
                async ([url]) => {
                    const resp = await fetch(url, {
                        headers: {'Referer': 'https://www.douyin.com/'}
                    });
                    return await resp.text();
                }
            """, [url])
            import json as _json
            data = _json.loads(raw)
            api_code = data.get("status_code", -1)
            comments = data.get("comments") or []
            logger.log(f"  评论第{page_num+1}页: cursor={cursor}, "
                       f"status_code={api_code}, 本页={len(comments)}条, "
                       f"累计={len(all_comments) + len(comments)}条")

            if api_code != 0 or not comments:
                if page_num == 0 and api_code != 0:
                    logger.log(f"  评论 API 返回非 0 code: {api_code}")
                break

            for c in comments:
                comment = {
                    "content": c.get("text", ""),
                    "user": c.get("user", {}).get("nickname", ""),
                    "time": c.get("create_time", 0),
                    "likes": c.get("digg_count", 0),
                    "replies": [],
                }
                reply_list = c.get("reply_comment") or []
                for sr in reply_list:
                    comment["replies"].append({
                        "content": sr.get("text", ""),
                        "user": sr.get("user", {}).get("nickname", ""),
                        "time": sr.get("create_time", 0),
                        "likes": sr.get("digg_count", 0),
                    })
                all_comments.append(comment)

            cursor = data.get("cursor", 0)
            if cursor == 0:
                break
            page_num += 1
        except Exception as e:
            logger.log(f"  评论抓取第{page_num+1}页异常: {e}")
            break

    logger.log(f"评论抓取完成: 累计 {len(all_comments)} 条", step_advance=True)
    return all_comments


async def _get_danmaku(page, logger):
    """best-effort 抓取弹幕（DOM scan / page.evaluate）"""
    logger.log("正在抓取弹幕数据（best-effort）...")
    try:
        raw_danmaku = await page.evaluate("""
            () => {
                const items = [];
                // 尝试从页面注入的弹幕数据提取
                const scripts = document.querySelectorAll('script');
                for (const s of scripts) {
                    if (s.textContent && s.textContent.includes('barrage_list')) {
                        try {
                            const m = s.textContent.match(/barrage_list[^\\[]*\\[([\\s\\S]*?)\\]/);
                            if (m) {
                                const objs = JSON.parse('[' + m[1] + ']');
                                objs.forEach(o => items.push({text: o.content || o.text || '', time: o.time || 0}));
                            }
                        } catch(e) {}
                    }
                }
                // DOM 降级扫描
                if (items.length === 0) {
                    const containers = document.querySelectorAll(
                        '[class*="danmaku"], [class*="barrage"], [class*="dm-item"], [class*="comment-item"]'
                    );
                    containers.forEach(c => {
                        const t = c.textContent?.trim();
                        if (t && t.length > 0 && t.length < 200) items.push({text: t});
                    });
                }
                return items;
            }
        """)
        logger.log(f"弹幕抓取: {len(raw_danmaku)} 条（原始）", step_advance=True)
        return raw_danmaku
    except Exception as e:
        logger.log(f"弹幕抓取异常: {e}")
        return []


def _save_json(data, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def process_douyin(url, output_dir, logger):
    """完整的抖音视频处理流程"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise Exception("缺少 playwright 模块。")

    os.makedirs(output_dir, exist_ok=True)

    async with async_playwright() as p:
        # 1. 创建或复用 persistent browser context
        logger.log("正在启动浏览器（persistent context）...")
        context = await p.chromium.launch_persistent_context(
            _DOUYIN_PROFILE_DIR,
            headless=True,
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True,
        )

        page = await context.new_page()
        login_state_used = False

        # 2. 检测登录态
        try:
            logged_in = await _check_login_state(context, page, logger)
        except Exception as e:
            logger.log(f"登录态检测异常，将尝试重新登录: {e}")
            logged_in = False

        if not logged_in:
            # 关闭 headless context，重新以非 headless 打开让用户登录
            logger.log("需要登录态，正在打开可视浏览器...")
            await context.close()

            context = await p.chromium.launch_persistent_context(
                _DOUYIN_PROFILE_DIR,
                headless=False,
                user_agent=HEADERS["User-Agent"],
                viewport={"width": 1280, "height": 720},
                ignore_https_errors=True,
            )
            page = await context.new_page()
            await page.goto("https://www.douyin.com", wait_until="domcontentloaded", timeout=30000)
            logged_in = await _wait_for_login(page, logger, timeout=120)

            if not logged_in:
                await context.close()
                raise Exception("抖音需要登录态，请在浏览器中完成登录后重试。")

            # 重新以 headless 模式运行（登录已保存到 profile）
            await context.close()
            context = await p.chromium.launch_persistent_context(
                _DOUYIN_PROFILE_DIR,
                headless=True,
                user_agent=HEADERS["User-Agent"],
                viewport={"width": 1280, "height": 720},
                ignore_https_errors=True,
            )
            page = await context.new_page()

        login_state_used = True
        logger.log("登录态就绪")

        # 3. 跟随短链接并解析 final_url
        final_url, aweme_id = await _follow_redirect(page, url, logger)
        if not aweme_id:
            await context.close()
            raise Exception(f"无法从 URL 解析视频 ID: {final_url}")

        # 4. 通过 aweme/detail 响应拦截获取视频信息和 URL
        logger.log("正在加载视频页面并拦截 aweme/detail...")
        info, video_url_str = await _get_video_info(page, aweme_id, final_url, logger)
        info["login_state_used"] = login_state_used

        # 5. 下载 video.mp4
        video_path = os.path.join(output_dir, "video.mp4")
        _download_video(video_url_str, video_path, logger)

        # 6. ffprobe 检查
        _ffprobe_check(video_path, logger)

        # 7. 抓取评论
        raw_comments = await _get_comments_from_api(aweme_id, page, logger)
        cleaned_comments = clean_comments(raw_comments, "douyin")

        # 8. best-effort 抓取弹幕
        raw_danmaku = await _get_danmaku(page, logger)
        cleaned_danmaku = clean_danmaku(raw_danmaku, "douyin")

        await context.close()

    # --- 所有文件写入（浏览器已关闭）---
    logger.log("正在生成输出文件...")

    # info.json
    _save_json(info, os.path.join(output_dir, "info.json"))

    # comments
    _save_json(cleaned_comments, os.path.join(output_dir, "comments.json"))
    if cleaned_comments:
        comment_rows = []
        for c in cleaned_comments:
            row = {"content": c["content"], "user": c["user"],
                   "time": c["time"], "likes": c["likes"]}
            comment_rows.append(row)
            for r in c.get("replies", []):
                comment_rows.append({
                    "content": f"[回复] {r['content']}", "user": r["user"],
                    "time": r["time"], "likes": r["likes"],
                })
        save_csv(comment_rows, os.path.join(output_dir, "comments.csv"),
                 columns=["content", "user", "time", "likes"])
    else:
        logger.log("  评论为空，生成空文件")
        _save_json({"available": False, "reason": "no comments returned"}, os.path.join(output_dir, "comments.json"))
        with open(os.path.join(output_dir, "comments.csv"), "w", encoding="utf-8") as f:
            f.write("content,user,time,likes\n")

    # danmaku
    if cleaned_danmaku:
        _save_json(cleaned_danmaku, os.path.join(output_dir, "danmaku.json"))
        columns = ["text", "time"] if any("time" in d for d in cleaned_danmaku) else ["text"]
        save_csv(cleaned_danmaku, os.path.join(output_dir, "danmaku.csv"), columns=columns)
    else:
        logger.log("  弹幕为空，写入不可用标记")
        _save_json({"available": False,
                     "reason": "douyin danmaku not available in current capture mode"},
                   os.path.join(output_dir, "danmaku.json"))
        with open(os.path.join(output_dir, "danmaku.csv"), "w", encoding="utf-8") as f:
            f.write("text\n")

    # 9. 转录
    logger.log("正在调用语音转录...")
    try:
        from .transcribe import transcribe_video as _transcribe
        transcript = _transcribe(video_path, output_dir, "transcript", logger)

        # 重命名以匹配抖音命名规范（transcribe_video 产生 {bv}_xxx 格式）
        src_map = {
            os.path.join(output_dir, "transcript_transcript.json"): os.path.join(output_dir, "transcript.json"),
            os.path.join(output_dir, "transcript_transcript.txt"): os.path.join(output_dir, "transcript.txt"),
            os.path.join(output_dir, "transcript_subtitles.srt"): os.path.join(output_dir, "subtitles.srt"),
        }
        for src, dst in src_map.items():
            if os.path.isfile(src):
                os.rename(src, dst)
                logger.log(f"  {os.path.basename(dst)} 已生成")
    except Exception as e:
        raise Exception(f"转录失败: {e}")

    logger.log("\n所有文件生成完成", step_advance=True)
    logger.done()

    return {
        "id": aweme_id,
        "title": info.get("title", ""),
        "output_dir": output_dir,
        "comment_count": len(cleaned_comments),
        "danmaku_count": len(cleaned_danmaku),
        "login_state_used": login_state_used,
    }
