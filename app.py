#!/usr/bin/env python3
"""
你是我的眼儿 - B站/抖音视频弹幕+字幕提取工具
AI一键式Websocket自动投喂器
"""
import os
import sys
import json
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

sys.path.insert(0, os.path.dirname(__file__))
from core.config import load_config, save_config, DEFAULTS
from core.common import TaskLogger, ensure_output_dir, save_json
from core.bilibili import extract_bv, get_video_info, get_danmaku, get_comments, download_bilibili_video, get_subtitles
from core.cleaner import clean_danmaku, clean_comments as clean_comments_data, save_csv as save_csv_data
from core.douyin import extract_video_id
from core.transcribe import transcribe_video


# === macOS Tkinter 按钮颜色修正 ===
# tk.Button 在 macOS 上忽略 bg/fg，必须用 ttk 配合可定制主题
STYLE_SETUP_DONE = False
def _setup_styles():
    global STYLE_SETUP_DONE
    if STYLE_SETUP_DONE:
        return
    s = ttk.Style()
    # clam 主题支持完整的背景色/前景色定制
    try:
        s.theme_use("clam")
    except Exception:
        pass
    # 顶部功能按钮：深灰底白字
    s.configure("Top.TButton",
                background="#3a3a3a", foreground="#ffffff",
                borderwidth=0, relief="flat", padding=(14, 5), font=("PingFang SC", 10))
    s.map("Top.TButton",
          background=[("active", "#505050"), ("pressed", "#2a2a2a")],
          foreground=[("active", "#ffffff")])
    # 主要操作按钮：蓝底白字
    s.configure("Action.TButton",
                background="#0078d4", foreground="#ffffff",
                borderwidth=0, relief="flat", padding=(30, 8),
                font=("PingFang SC", 12, "bold"))
    s.map("Action.TButton",
          background=[("active", "#106ebe"), ("disabled", "#555555")],
          foreground=[("active", "#ffffff"), ("disabled", "#999999")])
    STYLE_SETUP_DONE = True


class EnvCheckDialog(tk.Toplevel):
    """预装环境检查窗口 - 支持一键安装缺失依赖"""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("预装环境检查")
        self.geometry("650x520")
        self.configure(bg="#1e1e1e")
        self.transient(parent)
        self.grab_set()
        self._fix_widgets = {}  # name -> ttk.Button 映射

        tk.Label(self, text="预装环境检查", font=("PingFang SC", 16, "bold"),
                 bg="#1e1e1e", fg="#007acc").pack(pady=(15,5))
        tk.Label(self, text="检查所有运行时依赖，支持一键安装缺失项",
                 font=("PingFang SC", 10), bg="#1e1e1e", fg="#888").pack(pady=(0,10))

        # 可滚动的结果区域
        canvas_frame = tk.Frame(self, bg="#1e1e1e")
        canvas_frame.pack(fill="both", expand=True, padx=15, pady=(0, 5))

        self.canvas = tk.Canvas(canvas_frame, bg="#1e1e1e", highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.result_frame = tk.Frame(self.canvas, bg="#1e1e1e")

        self.result_frame.bind("<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.result_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        # 底部按钮
        btn_frame = tk.Frame(self, bg="#1e1e1e")
        btn_frame.pack(fill="x", padx=20, pady=(5, 15))
        tk.Button(btn_frame, text="重新检查", bg="#007acc", fg="white",
                  relief="flat", padx=15, pady=5, command=self._run_checks).pack(side="left")
        self._fix_all_btn = tk.Button(btn_frame, text="一键安装全部", bg="#0e639c", fg="white",
                  relief="flat", padx=15, pady=5, command=self._fix_all)
        tk.Button(btn_frame, text="关闭", bg="#3c3c3c", fg="#d4d4d4",
                  relief="flat", padx=15, pady=5, command=self.destroy).pack(side="right")

        self._run_checks()

    def _draw_result_row(self, r, row):
        """绘制单行检查结果"""
        row_frame = tk.Frame(self.result_frame, bg="#1e1e1e")
        row_frame.pack(fill="x", pady=1)

        # 状态图标
        colors = {"ok": "#4ec94e", "warn": "#dcdcaa", "fail": "#f44747"}
        tags = {"ok": "[OK]  ", "warn": "[WARN]", "fail": "[FAIL]"}
        tag = tags.get(r.status, "[???] ")
        color = colors.get(r.status, "#888")

        tk.Label(row_frame, text=tag, font=("Menlo", 10), bg="#1e1e1e",
                 fg=color, width=8, anchor="e").pack(side="left")

        # 名称
        tk.Label(row_frame, text=f"{r.name:30s}", font=("PingFang SC", 10),
                 bg="#1e1e1e", fg="#d4d4d4", anchor="w", width=35).pack(side="left")

        # 详情
        tk.Label(row_frame, text=r.detail[:60], font=("PingFang SC", 9),
                 bg="#1e1e1e", fg="#888", anchor="w").pack(side="left", fill="x", expand=True)

        # 修复按钮
        if r.fix_cmd and r.status != "ok":
            btn = tk.Button(row_frame, text=r.fix_label or "安装",
                           bg="#0e639c", fg="white", font=("PingFang SC", 9),
                           relief="flat", padx=8, pady=2,
                           command=lambda cmd=r.fix_cmd, nm=r.name, b=None: self._install_one(cmd, nm))
            btn.pack(side="right", padx=(5, 0))
            self._fix_widgets[r.name] = btn

    def _run_checks(self):
        from core.env_check import check_all
        for w in self.result_frame.winfo_children():
            w.destroy()
        self._fix_widgets.clear()

        results = check_all()
        has_failure = any(r.status == "fail" for r in results)

        for r in results:
            self._draw_result_row(r, 0)

        if has_failure:
            self._fix_all_btn.pack(side="left", padx=(10, 0))
        else:
            self._fix_all_btn.pack_forget()

        self.canvas.yview_moveto(0)

    def _install_one(self, fix_cmd, name):
        """后台安装单个依赖"""
        import threading
        btn = self._fix_widgets.get(name)
        if btn:
            btn.configure(text="安装中...", state="disabled")

        def do_install():
            from core.env_check import install_dependency
            ok, msg = install_dependency(fix_cmd, name)
            self.after(0, lambda: self._install_done(name, ok, msg))

        threading.Thread(target=do_install, daemon=True).start()

    def _install_done(self, name, success, msg):
        if success:
            messagebox.showinfo("安装完成", msg, parent=self)
        else:
            messagebox.showerror("安装失败", f"{name}:\n{msg}", parent=self)
        self._run_checks()

    def _fix_all(self):
        """一键安装所有可修复的依赖"""
        import threading
        from core.env_check import check_all, install_dependency

        results = check_all()
        todo = [(r.name, r.fix_cmd) for r in results if r.fix_cmd and r.status != "ok"]

        if not todo:
            messagebox.showinfo("提示", "所有依赖已就绪", parent=self)
            return

        self._fix_all_btn.configure(text="安装中...", state="disabled")
        for name in [t[0] for t in todo]:
            btn = self._fix_widgets.get(name)
            if btn:
                btn.configure(text="安装中...", state="disabled")

        def do_install():
            ok_count = 0
            fail_list = []
            for name, cmd in todo:
                ok, msg = install_dependency(cmd, name)
                if ok:
                    ok_count += 1
                else:
                    fail_list.append(f"{name}: {msg}")
            self.after(0, lambda: self._fix_all_done(ok_count, len(todo), fail_list))

        threading.Thread(target=do_install, daemon=True).start()

    def _fix_all_done(self, ok_count, total, fail_list):
        if fail_list:
            messagebox.showwarning("安装结果",
                f"完成 {ok_count}/{total} 项\n\n失败项:\n" + "\n".join(fail_list),
                parent=self)
        else:
            messagebox.showinfo("安装完成", f"全部 {ok_count} 项已安装完成", parent=self)
        self._run_checks()


class SettingsDialog(tk.Toplevel):
    """设置窗口 - 管理后端AI部署能力"""
    def __init__(self, parent, on_save=None):
        super().__init__(parent)
        self.title("设置 - 后端AI部署管理")
        self.geometry("550x450")
        self.configure(bg="#1e1e1e")
        self.transient(parent)
        self.grab_set()
        self.on_save = on_save
        self.cfg = load_config()

        tk.Label(self, text="后端AI部署设置", font=("PingFang SC", 16, "bold"),
                 bg="#1e1e1e", fg="#007acc").pack(pady=(15,5))

        # Notebook分页
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=15, pady=10)

        # ---- 输出设置 ----
        out_frame = tk.Frame(notebook, bg="#1e1e1e")
        notebook.add(out_frame, text="输出路径")

        tk.Label(out_frame, text="清洗文件输出位置", font=("PingFang SC", 11),
                 bg="#1e1e1e", fg="#d4d4d4").pack(anchor="w", padx=15, pady=(10,5))

        path_frame = tk.Frame(out_frame, bg="#1e1e1e")
        path_frame.pack(fill="x", padx=15, pady=5)
        self.out_var = tk.StringVar(value=self.cfg.get("output_dir", DEFAULTS["output_dir"]))
        tk.Entry(path_frame, textvariable=self.out_var, font=("Menlo", 10),
                 bg="#2d2d2d", fg="#d4d4d4", relief="flat", width=50).pack(side="left", fill="x", expand=True)
        tk.Button(path_frame, text="浏览...", bg="#3c3c3c", fg="#d4d4d4",
                  relief="flat", command=self._browse_output).pack(side="right", padx=(5,0))

        tk.Label(out_frame, text="新建文件夹策略", font=("PingFang SC", 11),
                 bg="#1e1e1e", fg="#d4d4d4").pack(anchor="w", padx=15, pady=(15,5))
        self.strategy_var = tk.StringVar(value="platform/bvid")
        for txt, val in [("按平台/视频ID 分文件夹 (推荐)", "platform/bvid"),
                          ("全部放在一起", "flat"),
                          ("按平台分大类", "platform")]:
            tk.Radiobutton(out_frame, text=txt, variable=self.strategy_var, value=val,
                           bg="#1e1e1e", fg="#d4d4d4", selectcolor="#1e1e1e",
                           activebackground="#1e1e1e", activeforeground="#007acc").pack(anchor="w", padx=25, pady=2)

        # ---- 网络/镜像 ----
        net_frame = tk.Frame(notebook, bg="#1e1e1e")
        notebook.add(net_frame, text="网络镜像")

        tk.Label(net_frame, text="pip 镜像源", font=("PingFang SC", 11),
                 bg="#1e1e1e", fg="#d4d4d4").pack(anchor="w", padx=15, pady=(10,3))
        self.pip_var = tk.StringVar(value=self.cfg.get("pip_mirror", DEFAULTS["pip_mirror"]))
        tk.Entry(net_frame, textvariable=self.pip_var, font=("Menlo", 10),
                 bg="#2d2d2d", fg="#d4d4d4", relief="flat").pack(fill="x", padx=15, pady=3)

        tk.Label(net_frame, text="HuggingFace 镜像", font=("PingFang SC", 11),
                 bg="#1e1e1e", fg="#d4d4d4").pack(anchor="w", padx=15, pady=(10,3))
        self.hf_var = tk.StringVar(value=self.cfg.get("hf_mirror", DEFAULTS["hf_mirror"]))
        tk.Entry(net_frame, textvariable=self.hf_var, font=("Menlo", 10),
                 bg="#2d2d2d", fg="#d4d4d4", relief="flat").pack(fill="x", padx=15, pady=3)

        # ---- AI模型 ----
        ai_frame = tk.Frame(notebook, bg="#1e1e1e")
        notebook.add(ai_frame, text="AI模型")

        tk.Label(ai_frame, text="Whisper 模型大小", font=("PingFang SC", 11),
                 bg="#1e1e1e", fg="#d4d4d4").pack(anchor="w", padx=15, pady=(10,3))
        self.model_var = tk.StringVar(value=self.cfg.get("whisper_model", "small"))
        model_frame = tk.Frame(ai_frame, bg="#1e1e1e")
        model_frame.pack(fill="x", padx=15, pady=3)
        for m in ["tiny", "small", "medium"]:
            tk.Radiobutton(model_frame, text=f"{m} (速度: {'极快' if m=='tiny' else '快' if m=='small' else '慢'})",
                           variable=self.model_var, value=m,
                           bg="#1e1e1e", fg="#d4d4d4", selectcolor="#1e1e1e",
                           activebackground="#1e1e1e", activeforeground="#007acc").pack(anchor="w")

        tk.Label(ai_frame, text="\n部署能力说明", font=("PingFang SC", 11),
                 bg="#1e1e1e", fg="#d4d4d4").pack(anchor="w", padx=15, pady=(10,3))
        info_text = ("本应用完全本地化运行，不依赖外部AI服务:\n"
                     "  B站弹幕: HTTP API (无需鉴权)\n"
                     "  语音转文字: faster-whisper 本地模型\n"
                     "  抖音弹幕: playwright 浏览器自动化\n"
                     "  预装依赖: Python3 / requests / faster-whisper")
        tk.Label(ai_frame, text=info_text, font=("PingFang SC", 9),
                 bg="#1e1e1e", fg="#666", justify="left").pack(anchor="w", padx=25, pady=5)

        # 底部按钮
        btn_frame = tk.Frame(self, bg="#1e1e1e")
        btn_frame.pack(fill="x", padx=15, pady=(5,15))
        tk.Button(btn_frame, text="保存设置", bg="#007acc", fg="white",
                  relief="flat", padx=20, pady=6, command=self._save).pack(side="left")
        tk.Button(btn_frame, text="取消", bg="#3c3c3c", fg="#d4d4d4",
                  relief="flat", padx=15, pady=6, command=self.destroy).pack(side="right")

    def _browse_output(self):
        d = filedialog.askdirectory(title="选择清洗文件输出位置", initialdir=self.out_var.get())
        if d:
            self.out_var.set(d)

    def _save(self):
        self.cfg["output_dir"] = self.out_var.get()
        self.cfg["folder_strategy"] = self.strategy_var.get()
        self.cfg["pip_mirror"] = self.pip_var.get()
        self.cfg["hf_mirror"] = self.hf_var.get()
        self.cfg["whisper_model"] = self.model_var.get()
        save_config(self.cfg)
        if self.on_save:
            self.on_save(self.cfg)
        messagebox.showinfo("设置", "设置已保存，下次启动生效。", parent=self)
        self.destroy()


class App:
    def __init__(self):
        self.root = tk.Tk()
        _setup_styles()
        self.root.title("你是我的眼儿")
        self.root.geometry("720x600")
        self.root.resizable(True, True)
        self.root.configure(bg="#1e1e1e")
        # 设置窗口图标
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon_path):
            try:
                img = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, img)
                self._icon_img = img  # 保持引用防止被 GC
            except Exception:
                pass
        # === 内置 ffmpeg 优先级（P2C 部署：安装版优先使用内置 ffmpeg/ffprobe） ===
        _builtin_ffmpeg_dir = os.path.join(os.path.dirname(__file__), "ffmpeg")
        if os.path.isdir(_builtin_ffmpeg_dir):
            os.environ["PATH"] = _builtin_ffmpeg_dir + ":" + os.environ.get("PATH", "")

        self.cfg = load_config()

        # === Runtime Manifest ===
        self._write_runtime_manifest()

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _write_runtime_manifest(self):
        """GUI 启动时生成 runtime_manifest_latest.json"""
        import hashlib
        import datetime
        base = os.path.dirname(os.path.abspath(__file__))
        manifest = {
            "app_runtime_path": base,
            "python_executable": sys.executable,
            "cwd": os.getcwd(),
            "core_bilibili_path": os.path.join(base, "core", "bilibili.py"),
            "core_bilibili_sha256": "",
            "core_douyin_path": os.path.join(base, "core", "douyin.py"),
            "core_douyin_sha256": "",
            "core_transcribe_path": os.path.join(base, "core", "transcribe.py"),
            "core_transcribe_sha256": "",
            "config_path": os.path.join(base, "config.json"),
            "ffmpeg_path": os.path.join(base, "ffmpeg", "ffmpeg"),
            "ffprobe_path": os.path.join(base, "ffmpeg", "ffprobe"),
            "output_dir": self.cfg.get("output_dir", ""),
            "timestamp": datetime.datetime.now().isoformat(),
        }
        for key in ["core_bilibili_path", "core_douyin_path", "core_transcribe_path"]:
            fp = manifest[key]
            if os.path.isfile(fp):
                with open(fp, "rb") as f:
                    manifest[key.replace("_path", "_sha256")] = hashlib.sha256(f.read()).hexdigest()

        from core.state import ACCEPT_OUTPUT_DIR, RUNTIME_MANIFEST_PATH
        os.makedirs(ACCEPT_OUTPUT_DIR, exist_ok=True)
        manifest["manifest_path"] = RUNTIME_MANIFEST_PATH
        with open(manifest["manifest_path"], "w") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        self._debug_manifest = manifest

    def _log_manifest(self):
        m = self._debug_manifest
        self._log(f"[Runtime] 代码路径: {m['app_runtime_path']}")
        self._log(f"[Runtime] output_dir: {m['output_dir']}")
        self._log(f"[Runtime] manifest: {m['manifest_path']}")

    def _build_ui(self):
        # 标题
        title = tk.Label(self.root, text="你是我的眼儿",
                         font=("PingFang SC", 20, "bold"), bg="#1e1e1e", fg="#007acc")
        title.pack(pady=(20, 3))

        subtitle = tk.Label(self.root, text="AI一键式Websocket自动投喂器",
                            font=("PingFang SC", 11), bg="#1e1e1e", fg="#888")
        subtitle.pack(pady=(0, 10))

        # 顶部按钮栏
        top_btn = tk.Frame(self.root, bg="#1e1e1e")
        top_btn.pack(fill="x", padx=40, pady=(0, 5))

        ttk.Button(top_btn, text="设置", style="Top.TButton",
                  command=self._open_settings).pack(side="left", padx=(0, 5))

        ttk.Button(top_btn, text="环境检查", style="Top.TButton",
                  command=self._open_env_check).pack(side="left", padx=(0, 5))

        ttk.Button(top_btn, text="输出位置", style="Top.TButton",
                  command=self._browse_output).pack(side="left")

        self.output_label_var = tk.StringVar(value=self._short_path(self.cfg.get('output_dir', '')))
        tk.Label(top_btn, textvariable=self.output_label_var, font=("PingFang SC", 10),
                 bg="#1e1e1e", fg="#bbbbbb").pack(side="right", padx=(8, 0))

        # 输入区
        input_frame = tk.Frame(self.root, bg="#1e1e1e")
        input_frame.pack(fill="x", padx=40, pady=(10, 10))

        tk.Label(input_frame, text="视频链接", font=("PingFang SC", 12),
                 bg="#1e1e1e", fg="#d4d4d4").pack(anchor="w")

        url_row = tk.Frame(input_frame, bg="#1e1e1e")
        url_row.pack(fill="x", pady=(5, 0))

        self.url_var = tk.StringVar()
        url_entry = tk.Entry(url_row, textvariable=self.url_var,
                             font=("PingFang SC", 12), bg="#2d2d2d", fg="#d4d4d4",
                             insertbackground="#d4d4d4", relief="flat",
                             highlightthickness=1, highlightbackground="#3c3c3c")
        url_entry.pack(side="left", fill="x", expand=True, ipady=6)

        self.platform_var = tk.StringVar(value="")
        tk.Label(input_frame, textvariable=self.platform_var, font=("PingFang SC", 10),
                 bg="#1e1e1e", fg="#888").pack(anchor="w", pady=(3, 0))
        url_entry.bind("<KeyRelease>", self._on_url_change)

        # 进度条
        progress_frame = tk.Frame(self.root, bg="#1e1e1e")
        progress_frame.pack(fill="x", padx=40, pady=(5, 5))

        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                            maximum=100, mode="determinate")
        self.progress_bar.pack(fill="x", ipady=3)

        self.status_var = tk.StringVar(value="就绪")
        tk.Label(progress_frame, textvariable=self.status_var, font=("PingFang SC", 10),
                 bg="#1e1e1e", fg="#888").pack(anchor="w", pady=(2, 0))

        # 按钮
        btn_frame = tk.Frame(self.root, bg="#1e1e1e")
        btn_frame.pack(fill="x", padx=40, pady=(5, 10))

        self.start_btn = ttk.Button(btn_frame, text="开始投喂", style="Action.TButton",
                                    command=self._start_task)
        self.start_btn.pack(side="left")

        # 日志区
        tk.Label(self.root, text="处理日志", font=("PingFang SC", 11),
                 bg="#1e1e1e", fg="#d4d4d4").pack(anchor="w", padx=40, pady=(5, 3))

        log_container = tk.Frame(self.root, bg="#3c3c3c")
        log_container.pack(fill="both", expand=True, padx=40, pady=(0, 15))

        self.log_text = tk.Text(log_container, font=("Menlo", 10), bg="#252526",
                                fg="#d4d4d4", relief="flat", wrap="word", state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=1, pady=1)

        scrollbar = tk.Scrollbar(log_container, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)

    def _short_path(self, p):
        home = os.path.expanduser("~")
        if p.startswith(home):
            return "~" + p[len(home):]
        return p

    def _on_url_change(self, event=None):
        url = self.url_var.get().strip()
        if "bilibili.com" in url or "BV" in url:
            self.platform_var.set("平台: B站 (API直连)")
        elif "douyin.com" in url:
            self.platform_var.set("平台: 抖音 (浏览器模式)")
        elif url:
            self.platform_var.set("无法识别平台")
        else:
            self.platform_var.set("")

    def _log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="normal")

    def _set_progress(self, pct, status=None):
        self.progress_var.set(pct)
        if status:
            self.status_var.set(status)

    def _open_settings(self):
        def on_save(cfg):
            self.cfg = cfg
            self.output_label_var.set(self._short_path(cfg.get('output_dir', '')))
        SettingsDialog(self.root, on_save=on_save)

    def _open_env_check(self):
        EnvCheckDialog(self.root)

    def _install_for_douyin_done(self, ok, msg, url):
        """playwright 安装完成后的回调"""
        self.status_var.set("就绪")
        if ok:
            self._log(f"[系统] {msg}")
            self._log("[系统] 依赖就绪，重新触发投喂...")
            self.url_var.set(url)
            self._start_task()
        else:
            self._log(f"[错误] {msg}")
            self.start_btn.configure(state="normal", text="开始投喂")
            messagebox.showerror("安装失败",
                f"{msg}\n\n请检查网络后重试，或打开\"环境检查\"手动安装。")

    def _browse_output(self):
        d = filedialog.askdirectory(title="选择输出位置", initialdir=self.cfg.get("output_dir", ""))
        if d:
            self.cfg["output_dir"] = d
            save_config(self.cfg)
            self.output_label_var.set(self._short_path(d))

    def _start_task(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("提示", "请输入视频链接")
            return

        is_douyin = "douyin.com" in url
        is_bilibili = "bilibili.com" in url or extract_bv(url)

        if is_douyin:
            from core.env_check import is_playwright_ready, install_dependency
            from core.env_check import _find_python
            if not is_playwright_ready():
                py = _find_python()
                want = messagebox.askyesno(
                    "缺少依赖",
                    "抖音功能需要 Playwright + Chromium 浏览器（约150MB）。\n\n"
                    "是否立即自动安装？"
                )
                if want:
                    self._log("[系统] 正在安装 playwright + Chromium，首次约需1-2分钟...")
                    self.status_var.set("安装依赖中...")
                    def do_install():
                        ok1, msg1 = install_dependency(
                            f'"{py}" -m pip install playwright', "playwright")
                        if ok1:
                            ok2, msg2 = install_dependency(
                                f'"{py}" -m playwright install chromium', "Chromium")
                            final_msg = msg2
                        else:
                            final_msg = msg1
                        self.root.after(0, lambda: self._install_for_douyin_done(ok1, final_msg, url))
                    threading.Thread(target=do_install, daemon=True).start()
                return

        if not is_bilibili and not is_douyin:
            messagebox.showwarning("提示", "无法识别该链接，目前支持B站和抖音")
            return

        self.start_btn.configure(state="disabled", text="投喂中...")
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="normal")

        logger = TaskLogger(log_callback=self._log,
                            progress_callback=lambda p: self._set_progress(p))
        logger.set_steps(9 if is_bilibili else 6)

        self._log_manifest()

        def run():
            try:
                if is_bilibili:
                    self._process_bilibili(url, logger)
                else:
                    self._process_douyin(url, logger)
            except Exception as e:
                import traceback
                self._log(f"\n[错误] {e}")
                traceback.print_exc()
                self._set_progress(0, "失败")
            finally:
                self.root.after(0, lambda: self.start_btn.configure(state="normal", text="开始投喂"))

        threading.Thread(target=run, daemon=True).start()

    def _process_bilibili(self, url, logger):
        from core.adapters.bilibili_adapter import run as run_bilibili
        result = run_bilibili(url, logger)

        if result.status == "FAIL":
            raise Exception(result.error or "B站处理失败")

        logger.log(f"\n输出目录: {result.output_dir}")
        logger.log(f"  弹幕: {result.danmaku_json} | 评论: {result.comments_json} | 字幕: {result.transcript_json}")
        logger.done()

        self.root.after(0, lambda: messagebox.showinfo(
            "处理完成",
            f"B站视频已处理完成\n\n"
            f"文件已保存到:\n{result.output_dir}"
        ))

    def _process_douyin(self, url, logger):
        import asyncio
        from core.adapters.douyin_adapter import run as run_douyin

        async def _run():
            return run_douyin(url, logger)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_run())
        finally:
            loop.close()

        if result.status == "FAIL":
            raise Exception(result.error or "抖音处理失败")

        logger.log(f"\n输出目录: {result.output_dir}")
        logger.log(f"  评论: {result.comments_json} | 弹幕: {result.danmaku_json} | 字幕: {result.transcript_json}")

        self.root.after(0, lambda: messagebox.showinfo(
            "处理完成",
            f"抖音视频已处理完成\n\n"
            f"文件已保存到:\n{result.output_dir}"
        ))

    def _on_close(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    app = App()
    app.run()


if __name__ == "__main__":
    main()
