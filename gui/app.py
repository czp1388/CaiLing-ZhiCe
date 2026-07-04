#!/usr/bin/env python3
"""彩灵·智策 — 极简GUI·深色交易风格"""
import sys, os
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QTextEdit, QLineEdit, QSplitter,
    QFrame, QMessageBox)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont, QColor, QPalette

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    HAS_WEB = True
except ImportError:
    HAS_WEB = False

DARK_BG = "#0f0f1a"
DARK_CARD = "#1a1a2e"
GOLD = "#ffd700"
RED = "#ef5350"
GREEN = "#4caf50"
TEXT = "#e0e0e0"

def set_dark_theme(app):
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.Window, QColor(DARK_BG))
    p.setColor(QPalette.Base, QColor(DARK_CARD))
    p.setColor(QPalette.Text, QColor(TEXT))
    p.setColor(QPalette.WindowText, QColor(TEXT))
    p.setColor(QPalette.Button, QColor(DARK_CARD))
    p.setColor(QPalette.ButtonText, QColor(GOLD))
    app.setPalette(p)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("彩灵·智策")
        self.setMinimumSize(1000, 650)
        self.setStyleSheet(f"background:{DARK_BG};color:{TEXT}")
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        # Title
        t = QLabel("🎯 彩灵·智策 — AI六合彩分析")
        t.setStyleSheet(f"font-size:18px;font-weight:bold;color:{GOLD};padding:10px")
        layout.addWidget(t)
        splitter = QSplitter()
        # Left: chart
        lw = QWidget()
        ll = QVBoxLayout(lw)
        ll.setContentsMargins(0, 0, 0, 0)
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("号码:"))
        self.num_inp = QLineEdit("28")
        self.num_inp.setMaximumWidth(60)
        self.num_inp.setStyleSheet(f"background:{DARK_CARD};color:{TEXT};border:1px solid #333;padding:4px")
        ctrl.addWidget(self.num_inp)
        btn = QPushButton("📈 走势")
        btn.setStyleSheet(f"background:{GOLD};color:{DARK_BG};font-weight:bold;padding:4px 12px;border:none")
        btn.clicked.connect(self.refresh_chart)
        ctrl.addWidget(btn)
        ctrl.addStretch()
        ll.addLayout(ctrl)
        if HAS_WEB:
            self.web = QWebEngineView()
            self.web.setStyleSheet(f"background:{DARK_BG}")
            ll.addWidget(self.web)
        else:
            ll.addWidget(QLabel("安装 PyQtWebEngine 显示图表"))
        splitter.addWidget(lw)
        # Right: recommendation
        rw = QFrame()
        rw.setStyleSheet(f"background:{DARK_CARD};border-radius:8px;padding:10px")
        rl = QVBoxLayout(rw)
        rl.addWidget(QLabel("🤖 AI 今日推荐"))
        self.rec_lbl = QLabel("点击「刷新」")
        self.rec_lbl.setWordWrap(True)
        self.rec_lbl.setStyleSheet(f"font-size:14px;color:{TEXT}")
        rl.addWidget(self.rec_lbl)
        self.reason_txt = QTextEdit()
        self.reason_txt.setReadOnly(True)
        self.reason_txt.setMaximumWidth(350)
        self.reason_txt.setStyleSheet(f"background:{DARK_BG};color:{TEXT};border:1px solid #333;border-radius:4px;padding:8px;font-size:12px")
        rl.addWidget(self.reason_txt)
        
        self.hit_label = QLabel("📊 历史命中: 加载中...")
        self.hit_label.setStyleSheet(f"color:{GREEN};font-size:11px;padding:4px")
        rl.addWidget(self.hit_label)
        btn_r = QPushButton("🔄 刷新推荐")
        btn_r.setMinimumHeight(40)
        btn_r.setStyleSheet(f"background:{RED};color:white;font-size:14px;font-weight:bold;border:none;border-radius:6px")
        btn_r.clicked.connect(self.refresh_recommend)
        rl.addWidget(btn_r)
        splitter.addWidget(rw)
        splitter.setSizes([650, 350])
        layout.addWidget(splitter)
        self.refresh_recommend()
        self.refresh_chart()

    def refresh_chart(self):
        if not HAS_WEB or not hasattr(self, 'web'):
            return
        try:
            num = int(self.num_inp.text() or "28")
            from core.chart import render_kline_html
            html = render_kline_html(num, 150, ["ma5", "boll", "rsi"])
            self.web.setHtml(html)
        except Exception as e:
            self.web.setHtml(f"<h3 style='color:red'>❌ {e}</h3>")

    def refresh_recommend(self):
        try:
            from core.recommender import get_recommendation
            rec = get_recommendation()
            nums = ", ".join(str(n) for n in rec.get("numbers", []))
            c = rec.get("confidence", "")
            color = {"高": GREEN, "中": "#ff9800", "低": RED}.get(c, TEXT)
            self.rec_lbl.setText(
                f'<span style="font-size:20px;color:{GOLD}">{nums}</span><br><br>'
                f'信心: <span style="color:{color};font-weight:bold">{c}</span><br>'
                f'{rec.get("strategy", "")}<br>'
                f'{rec.get("avg_hit_rate", "")} / {rec.get("expected_rate", "")}'
            )
            self.reason_txt.setText(rec.get("reason", ""))
            try:
                from core.stats import accuracy_report
                ar = accuracy_report()
                self.hit_label.setText(f"📊 推荐{ar['total_recommendations']}次 命中率{ar['hit_rate']} (随机14.3%)")
            except:
                self.hit_label.setText("📊 历史命中: 数据不足")
        except Exception as e:
            self.rec_lbl.setText(f"❌ {e}")

def run():
    app = QApplication(sys.argv)
    set_dark_theme(app)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    run()
