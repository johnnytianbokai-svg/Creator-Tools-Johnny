"""抖音 Adapter：对接已通过的抖音主链路，不重写核心逻辑"""
from core.contract import ProcessResult
from core.state import get_output_dir
import re


def run(url: str, logger) -> ProcessResult:
    import asyncio
    from core.douyin import process_douyin

    m = re.search(r"/video/(\d+)", url)
    video_id = m.group(1) if m else "unknown"
    output_dir = get_output_dir("douyin", video_id)

    result = ProcessResult(platform="douyin", video_id=video_id, output_dir=output_dir)

    try:
        ret = asyncio.run(process_douyin(url, output_dir, logger))
        result.video_id = ret.get("id", video_id)
        # 从 process_douyin 获取真实 video_id 后修正 output_dir
        real_video_id = ret.get("id", video_id)
        if real_video_id != video_id:
            # 短链场景：process_douyin 把文件写到了 "unknown" 目录，移到正确目录
            import shutil, os as _os
            correct_dir = get_output_dir("douyin", real_video_id)
            if _os.path.isdir(output_dir) and output_dir != correct_dir:
                _os.makedirs(_os.path.dirname(correct_dir), exist_ok=True)
                if _os.path.isdir(correct_dir):
                    shutil.rmtree(correct_dir)
                shutil.move(output_dir, correct_dir)
            result.output_dir = correct_dir
        else:
            result.output_dir = ret.get("output_dir", output_dir)
        result.set_file_states(result.output_dir)
        result.validate_content(result.output_dir)
        result.status = "PASS" if result.all_files_present() else "FAIL"
        if result.status == "FAIL":
            result.error = "output files incomplete"
    except Exception as e:
        result.status = "FAIL"
        result.error = str(e)

    return result
