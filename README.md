# 彩灵·智策 — 六合彩智能分析系统

全命令行驱动，JSON/CSV输出。GUI为辅助。

## 快速开始
```bash
pip install -r requirements.txt
python3 -m core.database --init     # 初始化数据库
python3 -m core.fetcher --fetch      # 拉取历史数据
```

## 模块
- `core/database.py` — 数据底座（SQLite）
- `core/fetcher.py` — 数据采集
- `core/analyzer.py` — 冷热号/遗漏值分析
- `core/backtest.py` — 五膽拖回测
- `core/ev.py` — 期望值计算
- `gui/app.py` — PyQt5图形界面
