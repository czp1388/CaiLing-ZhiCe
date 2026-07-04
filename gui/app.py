#!/usr/bin/env python3
"""
彩灵·智策 — PyQt5图形界面
主窗口：冷热号、遗漏值、五膽拖、期望值
"""
import sys, os, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QLabel, QTextEdit, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QFrame,
    QGridLayout, QGroupBox, QMessageBox, QComboBox, QCheckBox
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont, QColor, QPalette

# QWebEngineView 用于显示Plotly图表
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False


# ========== 冷热号面板 ==========
class HotColdPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        btn = QPushButton("📊 分析冷热号")
        btn.clicked.connect(self.analyze)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(btn)
        layout.addWidget(self.output)
        self.setLayout(layout)

    def analyze(self):
        from core.analyzer import hot_cold_numbers, missing_stats
        hc = hot_cold_numbers()
        m = missing_stats()
        lines = ["🔥 热号 Top 10:", ""]
        for num, count in hc["hot"]:
            bar = "█" * min(count, 20)
            lines.append(f"  {num:2d}: {count:2d}次 {bar}")
        lines.extend(["", "❄️ 冷号 Top 10:", ""])
        for num, count in hc["cold"]:
            bar = "█" * min(count, 20)
            lines.append(f"  {num:2d}: {count:2d}次 {bar}")
        lines.extend(["", "📈 遗漏值 Top 15:", ""])
        for num, days in m[:15]:
            bar = "█" * min(days, 30)
            lines.append(f"  {num:2d}: {days}期未出 {bar}")
        self.output.setText("\n".join(lines))


# ========== 五膽拖面板 ==========
class BacktestPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        form = QHBoxLayout()
        form.addWidget(QLabel("胆码(5个):"))
        self.input = QLineEdit()
        self.input.setPlaceholderText("如: 12 23 34 41 48")
        form.addWidget(self.input)
        btn = QPushButton("▶ 回测")
        btn.clicked.connect(self.run)
        form.addWidget(btn)
        auto_btn = QPushButton("🎲 自动扫描")
        auto_btn.clicked.connect(self.auto)
        form.addWidget(auto_btn)
        layout.addLayout(form)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)
        self.setLayout(layout)

    def run(self):
        from core.backtest import backtest_5drag, format_backtest
        text = self.input.text().strip()
        try:
            cores = [int(x) for x in text.split()]
            if len(cores) != 5:
                self.output.setText("❌ 需要5个号码")
                return
            result = backtest_5drag(cores)
            self.output.setText(format_backtest(result))
        except:
            self.output.setText("❌ 输入格式错误")

    def auto(self):
        from core.backtest import auto_backtest, format_backtest
        self.output.setText("⏳ 扫描中...")
        QApplication.processEvents()
        best = auto_backtest(trials=500)
        text = format_backtest(best["result"])
        text += f"\n\n推荐胆码: {best['cores']}"
        self.output.setText(text)


# ========== 期望值面板 ==========
class EVPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        form = QHBoxLayout()
        form.addWidget(QLabel("号码(6个):"))
        self.input = QLineEdit()
        self.input.setPlaceholderText("如: 12 23 34 41 48 49")
        form.addWidget(self.input)
        btn = QPushButton("📈 计算期望值")
        btn.clicked.connect(self.calc)
        form.addWidget(btn)
        layout.addLayout(form)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)
        self.setLayout(layout)

    def calc(self):
        import json
        from core.ev import calculate_ev
        text = self.input.text().strip()
        try:
            picks = [int(x) for x in text.split()]
            if len(picks) != 6:
                self.output.setText("❌ 需要6个号码")
                return
            result = calculate_ev(picks)
            parts = [f"📈 期望值分析: {picks}", ""]
            for b in result.get("breakdown", []):
                parts.append(f"  {b['level']}: 1/{b['prob_1in']:,} × ${b['prize']:,} = ${b['expected']}")
            parts.append(f"\n总期望值: ${result.get('ev_total', 0)} (成本$10)")
            if result.get("is_positive"):
                parts.append("\n✅ 正期望值！")
            else:
                parts.append(f"\n❌ 负期望值, 每注亏 ${10 - result.get('ev_total', 0):.2f}")
            self.output.setText("\n".join(parts))
        except:
            self.output.setText("❌ 输入格式错误")


# ========== K线图面板 ==========
class KlinePanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        # 控制栏
        controls = QHBoxLayout()
        controls.addWidget(QLabel("号码:"))
        self.number_input = QLineEdit()
        self.number_input.setPlaceholderText("1-49")
        self.number_input.setMaximumWidth(60)
        controls.addWidget(self.number_input)

        controls.addWidget(QLabel("期数:"))
        self.window_input = QLineEdit("200")
        self.window_input.setMaximumWidth(80)
        controls.addWidget(self.window_input)

        controls.addWidget(QLabel("指标:"))
        self.ma5_cb = QCheckBox("MA5")
        self.ma5_cb.setChecked(True)
        self.boll_cb = QCheckBox("布林")
        self.boll_cb.setChecked(True)
        self.kdj_cb = QCheckBox("KDJ")
        self.macd_cb = QCheckBox("MACD")
        self.rsi_cb = QCheckBox("RSI")
        controls.addWidget(self.ma5_cb)
        controls.addWidget(self.boll_cb)
        controls.addWidget(self.kdj_cb)
        controls.addWidget(self.macd_cb)
        controls.addWidget(self.rsi_cb)

        btn = QPushButton("📈 生成K线图")
        btn.clicked.connect(self.generate)
        controls.addWidget(btn)
        layout.addLayout(controls)

        # 图表显示
        if HAS_WEBENGINE:
            self.webview = QWebEngineView()
            self.webview.setMinimumHeight(600)
            layout.addWidget(self.webview, 1)
        else:
            self.webview = None
            layout.addWidget(QLabel("需要安装 PyQtWebEngine 才能显示图表:\n  pip install PyQtWebEngine\n\n或者用命令行生成:\n  python3 cli.py chart --number 28"))

        self.setLayout(layout)

    def generate(self):
        if not self.webview:
            return
        try:
            number = int(self.number_input.text() or "28")
            window = int(self.window_input.text() or "200")
            indicators = []
            if self.ma5_cb.isChecked(): indicators.append("ma5")
            if self.boll_cb.isChecked(): indicators.append("boll")
            if self.kdj_cb.isChecked(): indicators.append("kdj")
            if self.macd_cb.isChecked(): indicators.append("macd")
            if self.rsi_cb.isChecked(): indicators.append("rsi")
            if not indicators:
                indicators = ["ma5", "boll"]

            from core.chart import render_kline_html
            html = render_kline_html(number, window, indicators)
            self.webview.setHtml(html)
        except Exception as e:
            self.webview.setHtml(f"<h3>❌ {e}</h3>")


# ========== 主窗口 ==========
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("彩灵·智策 v1.0")
        self.setMinimumSize(900, 650)

        tabs = QTabWidget()
        tabs.addTab(HotColdPanel(), "📊 冷热号分析")
        tabs.addTab(KlinePanel(), "📈 K线图+技术指标")
        tabs.addTab(BacktestPanel(), "🎯 五膽拖回测")
        tabs.addTab(EVPanel(), "💰 期望值计算")

        self.setCentralWidget(tabs)
        self.show()


def run():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run()
