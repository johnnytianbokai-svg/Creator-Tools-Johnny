# PROJECT EXECUTION MEMORY

## 固定验收链接

### B站 (冻结 — 已 PASS)
```
https://www.bilibili.com/video/BV1hjT56VEW8/?spm_id_from=333.1007.tianma.1-1-1.click
```
PASS manifest: /Users/tianbokai/Downloads/B站前端App_manifest_20260705_fixed.md

### 抖音
```
https://v.douyin.com/HJoW8Q0ft0A/
```
原始分享: 2.84 复制打开抖音，看看【王林医生的作品】焦虑抑郁你还认为是矫情吗？ 没有敏感的体质，没有生... https://v.douyin.com/HJoW8Q0ft0A/ 01/02 :1pm O@K.jC yGV:/

验收必须使用上述固定链接，不允许自行搜索、换视频、用历史链接替代。链接失败直接 FAIL。

## 前端 App 验收规则

- 终端脚本 PASS 不等于产品 PASS
- 最终验收必须来自 `/Users/tianbokai/Desktop/你是我的眼儿.app`
- runtime_manifest 必须证明运行路径来自 `.app/Contents/Resources/`
- 不允许用 python3 app.py 替代 .app
- 不允许用 python3 scripts/accept_*.py 作为最终验收依据

## 输出目录规则

- 用户产物（视频/JSON/CSV/transcript/srt）→ `/Users/tianbokai/Downloads/111/`
- 验收文档（.md/manifest/截图/报告）→ `/Users/tianbokai/Downloads/`

## 架构原则

- Contract: 统一结果结构
- Adapter: 隔离 B站/抖音变化
- State: 统一路径/profile/output/runtime_manifest

## 内容有效性标准

- 文件存在 ≠ 内容有效
- transcript.txt size 必须 > 0
- transcript.json segments 必须 > 0
- 空 transcript 永不 PASS
- 评论为空必须有 reason
- 弹幕为空必须写 unavailable + reason

## B站修复记录 (2026-07-05)

阻塞点: `'list' object has no attribute 'get'`
根因: process_bilibili 调用 transcribe_audio(返回list) → .get("segments") 失败
修复: 改用 transcribe_video(返回dict)，Contract 新增 validate_content()/transcript_valid()
结果: transcript 31 segments / 2482 bytes — PASS
