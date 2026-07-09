"""B站 Adapter：对接已通过的 B站主链路，不重写核心逻辑"""
from core.contract import ProcessResult
from core.state import get_output_dir
import re


def run(url: str, logger) -> ProcessResult:
    from core.bilibili import process_bilibili

    m = re.search(r"BV[\w]+", url)
    video_id = m.group(0) if m else "unknown_bv"
    output_dir = get_output_dir("bilibili", video_id)

    result = ProcessResult(platform="bilibili", video_id=video_id, output_dir=output_dir)

    try:
        ret = process_bilibili(url, output_dir, logger)
        result.video_id = ret.get("id", video_id)
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
