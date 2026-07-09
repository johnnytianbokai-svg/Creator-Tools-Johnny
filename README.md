---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 44de08c4f7781fe3119b98807a2d348b_ae76735e7b6111f1aac35254006c9bbf
    ReservedCode1: RH/5DZIQNvj9GWzhX331AD+lrhT4oQGOygBCQmRN9KkocG4W7ttBVUtnJN6l6qNDmgUnHjFNeJ0WwAqk8EHSM8UjKbR4RzKvTa4kWU4logBdPPxteurDQ3d7ZMFHyeend6dozYJNDHqO9s/kbxWoycdljvYYDs0yV0bYd4krRDyskRLF7TueRAKKGR4=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 44de08c4f7781fe3119b98807a2d348b_ae76735e7b6111f1aac35254006c9bbf
    ReservedCode2: RH/5DZIQNvj9GWzhX331AD+lrhT4oQGOygBCQmRN9KkocG4W7ttBVUtnJN6l6qNDmgUnHjFNeJ0WwAqk8EHSM8UjKbR4RzKvTa4kWU4logBdPPxteurDQ3d7ZMFHyeend6dozYJNDHqO9s/kbxWoycdljvYYDs0yV0bYd4krRDyskRLF7TueRAKKGR4=
---

# 你是我的眼儿

B站/抖音视频下载与分析工具。支持视频下载、弹幕抓取、评论采集、字幕提取、语音转录。

## 功能

- **B站视频**：基于 yt-dlp 下载 DASH 双轨视频，自动 ffmpeg 合并；弹幕、评论、AI字幕抓取
- **抖音视频**：基于 Playwright 浏览器自动化 + yt-dlp 下载；评论、弹幕抓取
- **语音转录**：基于 faster-whisper 本地语音转文字（默认 small 模型）
- **GUI 界面**：Tkinter 原生界面，支持输出目录配置、平台适配器扩展

## 系统要求

- macOS 10.15+
- Python 3.11+（内置 DMG 安装版自带 Python）
- 依赖：详见 `requirements.txt`

## 安装方式（最终用户）

### DMG 安装版（推荐）

1. 下载 `你是我的眼儿_1.0.1.dmg`
2. 打开 DMG，将 `你是我的眼儿.app` 拖入 `Applications` 文件夹
3. 首次启动会提示安装 Chromium（约150MB），请等待完成
4. 启动后配置输出目录，即可使用

本机运行 App 路径：`/Applications/你是我的眼儿.app`

### 源码运行

```bash
# 克隆仓库
git clone <repo-url>
cd 你是我的眼儿

# 安装依赖
pip install -r requirements.txt
playwright install chromium

# 启动
python app.py
```

## 源码说明

```
你是我的眼儿/
├── app.py                  # GUI 主程序
├── launcher.sh             # .app 启动脚本
├── config.json             # 用户配置（输出目录、Whisper 参数等）
├── setup.py                # Python 打包配置
├── icon.icns / icon.png    # 应用图标
├── requirements.txt        # Python 依赖
├── core/
│   ├── bilibili.py         # B站下载/弹幕/评论/字幕
│   ├── douyin.py           # 抖音下载/弹幕/评论
│   ├── transcribe.py       # Whisper 语音转录
│   ├── state.py            # 统一状态/路径管理
│   ├── config.py           # 配置加载
│   ├── contract.py         # 数据契约定义
│   ├── env_check.py        # 环境检查
│   ├── common.py           # 公共工具函数
│   ├── cleaner.py          # 清理工具
│   └── adapters/           # 平台适配器
│       ├── bilibili_adapter.py
│       └── douyin_adapter.py
├── scripts/                # 辅助脚本
└── 你是我的眼儿_1.0.1.dmg  # 安装包
```

## 依赖说明

- **yt-dlp**：视频下载
- **faster-whisper**：语音转录
- **playwright**：抖音浏览器自动化 + Chromium
- **requests**：API 请求
- **av**：音视频处理

## 登录态说明

- 本仓库**不包含**任何用户 Cookie、登录凭据或浏览器 Profile
- B站下载依赖本地浏览器 Cookie（运行时从已登录的浏览器自动读取）
- 抖音依赖本地浏览器登录态 + 持久化 Profile（存储在 `~/.ni_shi_wo_de_yaner/douyin_profile/` 或 `~/Library/Application Support/你是我的眼儿/`）
- 登录态仅在用户本机有效，源码不包含任何账户信息

## 输出目录说明

默认输出目录：`~/Downloads/你是我的眼儿_output/`

可通过 `config.json` 中的 `output_dir` 字段自定义，例如：
```json
{
  "output_dir": "/Users/xxx/Downloads/my_output"
}
```

输出结构：`{output_dir}/{platform}/{video_id}/`

## 版本

最新版本：**1.0.1** — 详见 `VERSION.md`

## GitHub 上传注意事项

DMG 安装包（约190MB）不应直接提交到 Git 仓库。建议：
- **方法一**：使用 GitHub Releases 附件上传 DMG
- **方法二**：使用 Git LFS 跟踪 `.dmg` 文件
- **方法三**：仅上传源码，DMG 在 Release 页面单独提供

```bash
# 初始化仓库
git init
git add .
git commit -m "Initial commit: 你是我的眼儿 v1.0.1"

# 如果使用 Git LFS
git lfs track "*.dmg"
git add .gitattributes
```
*（内容由AI生成，仅供参考）*
