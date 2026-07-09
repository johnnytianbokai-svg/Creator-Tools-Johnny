#!/usr/bin/env python3
"""运行时环境检查：输出 Python / 路径 / sha256"""
import sys, os, hashlib

def sha256(path):
    if not os.path.isfile(path):
        return "MISSING"
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def main():
    print("1. Python executable:", sys.executable)
    print("2. Working directory:", os.getcwd())
    base = os.path.dirname(os.path.abspath(__file__))
    print("3. Scripts dir:", os.path.dirname(os.path.abspath(__file__)))

    # Try to find project root (either cwd or inferred)
    project_root = os.getcwd()
    app_py = os.path.join(project_root, "app.py")
    if not os.path.isfile(app_py):
        project_root = os.path.dirname(os.path.dirname(base))

    print("4. app.py path:", os.path.join(project_root, "app.py"))
    print("5. core/bilibili.py path:", os.path.join(project_root, "core", "bilibili.py"))
    print("6. core/douyin.py path:", os.path.join(project_root, "core", "douyin.py"))
    print("7. core/transcribe.py path:", os.path.join(project_root, "core", "transcribe.py"))

    for label, fname in [
        ("app.py", "app.py"),
        ("core/bilibili.py", "core/bilibili.py"),
        ("core/douyin.py", "core/douyin.py"),
        ("core/transcribe.py", "core/transcribe.py"),
    ]:
        fp = os.path.join(project_root, fname)
        print(f"8. {label} sha256:", sha256(fp))

    config_path = os.path.join(project_root, "config.json")
    print("9. config.json path:", config_path)
    if os.path.isfile(config_path):
        import json
        try:
            with open(config_path) as f:
                cfg = json.load(f)
            print("9. output_dir:", cfg.get("output_dir", "NOT SET"))
        except Exception as e:
            print("9. config error:", e)

    print("10. sys.path (first 10):")
    for i, p in enumerate(sys.path[:10]):
        print(f"    [{i}] {p}")

if __name__ == "__main__":
    main()
