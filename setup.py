#!/usr/bin/env python3
"""彩灵·智策 一键安装"""
import subprocess, sys
deps = ["requests", "PyQt5", "PyQtWebEngine", "plotly", "numpy", "pandas"]
print("📦 安装依赖...")
for d in deps:
    r = subprocess.run([sys.executable, "-m", "pip", "install", d, "--break-system-packages"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        print(f"  ✅ {d}")
    else:
        print(f"  ⚠️ {d}: {r.stderr[-100:]}")
print("\\n✅ 安装完成！运行: python3 cli.py init")
