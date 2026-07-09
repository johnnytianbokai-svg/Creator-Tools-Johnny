"""
共享数据清洗管线 + CSV 输出
"""
import csv
import re
import os


def clean_danmaku(items: list, platform: str = "") -> list:
    """
    弹幕清洗：
    - 去重（完全相同的 text 合并，保留首次出现的所有字段）
    - 过滤空文本 / 纯空白 / 纯标点
    - 文本规范化（去除首尾空白、统一全角半角标点）
    - 返回清洗后的 list[dict]
    """
    seen = set()
    cleaned = []
    for item in items:
        text = (item.get("text") or "").strip()
        # 过滤空文本
        if not text:
            continue
        # 过滤纯标点/纯数字/纯emoji短文本（<2个有效字符）
        meaningful = re.sub(r'[\s\d\W_]', '', text)
        if len(meaningful) < 2 and len(text) < 4:
            continue
        # 规范化
        text = _normalize_text(text)
        # 去重
        dedup_key = text.lower()
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        item["text"] = text
        cleaned.append(item)
    return cleaned


def clean_comments(items: list, platform: str = "") -> list:
    """
    评论清洗（含楼层 + 回复）：
    - 过滤空评论 / 纯表情评论
    - 去除 HTML 标签
    - 文本规范化
    - 去重
    - 递归清洗子回复
    返回 list[dict]，每条评论含 replies 字段
    """
    seen = set()
    cleaned = []
    for item in items:
        text = (item.get("content") or item.get("text") or "").strip()
        # 过滤空内容
        if not text:
            continue
        # 去除 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)
        text = _normalize_text(text)
        # 过滤纯表情/纯标点
        meaningful = re.sub(r'[\s\d\W_]', '', text)
        if len(meaningful) < 2 and len(text) < 4:
            continue
        # 去重
        dedup_key = text.lower()
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        entry = {
            "content": text,
            "user": item.get("user") or item.get("author") or item.get("nickname", ""),
            "time": item.get("time") or item.get("created_at") or item.get("ctime", 0),
            "likes": item.get("likes") or item.get("like_count") or item.get("digg_count", 0),
        }
        # 递归清洗子回复
        replies = item.get("replies") or item.get("reply_list") or []
        if replies:
            entry["replies"] = clean_comments(replies, platform)
        cleaned.append(entry)
    return cleaned


def save_csv(data: list, filepath: str, columns: list = None):
    """将 list[dict] 写入 CSV 文件"""
    if not data:
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            f.write("")
        return filepath
    if columns is None:
        columns = list(data[0].keys())
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)
    return filepath


def _normalize_text(text: str) -> str:
    """文本规范化"""
    text = text.strip()
    # 统一省略号为 ...
    text = text.replace("\u2026", "...")
    # 压缩连续空格
    text = re.sub(r' {2,}', ' ', text)
    return text
