#!/usr/bin/env python3
"""
彩灵·智策 — 极简GUI

老板只用来看一个画面：
- 左侧：遗漏值K线走势图（可切换号码）
- 右侧：AI今日推荐（号码+理由+信心）
- 底部：刷新按钮
"""
import sys, os, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QLineEdit, QSplitter, QFrame,
    QMessageBox
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    HAS_WEB = True
except ImportError:
    HAS_WEB = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("彩灵·智策")
        self.setMinimumSize(1000, 650)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)

        # 标题
        title = QLabel("🎯 彩灵·智策 — AI六合彩分析")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title)

        # 主区域：左(图表) + 右(推荐)
        splitter = QSplitter()

        # === 左侧：K线图 ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        chart_controls = QHBoxLayout()
        chart_controls.addWidget(QLabel("号码:"))
        self.number_input = QLineEdit("28")
        self.number_input.setMaximumWidth(60)
        chart_controls.addWidget(self.number_input)
        self.chart_btn = QPushButton("📈 查看走势")
        self.chart_btn.clicked.connect(self.refresh_chart)
        chart_controls.addWidget(self.chart_btn)
        chart_controls.addStretch()
        left_layout.addLayout(chart_controls)

        if HAS_WEB:
            self.webview = QWebEngineView()
            left_layout.addWidget(self.webview, 1)
        else:
            self.webview = None
            left_layout.addWidget(QLabel("安装 PyQtWebEngine 显示图表:\n pip install PyQtWebEngine"))
        splitter.addWidget(left_widget)

        # === 右侧：AI推荐 ===
        right_widget = QFrame()
        right_widget.setFrameStyle(QFrame.StyledPanel)
        right_layout = QVBoxLayout(right_widget)

        right_layout.addWidget(QLabel("🤖 AI 今日推荐"))
        right_layout.addSpacing(10)

        self.rec_label = QLabel("点击「刷新推荐」获取")
        self.rec_label.setFont(QFont("Arial", 12))
        self.rec_label.setWordWrap(True)
        right_layout.addWidget(self.rec_label)

        self.reason_text = QTextEdit()
        self.reason_text.setReadOnly(True)
        self.reason_text.setMaximumWidth(350)
        right_layout.addWidget(self.reason_text, 1)

        self.refresh_btn = QPushButton("🔄 刷新推荐")
        self.refresh_btn.setMinimumHeight(40)
        self.refresh_btn.setStyleSheet("background:#2196F3; color:white; font-size:14px;")
        self.refresh_btn.clicked.connect(self.refresh_recommend)
        right_layout.addWidget(self.refresh_btn)

        splitter.addWidget(right_widget)
        splitter.setSizes([650, 350])
        layout.addWidget(splitter, 1)

        # 启动时自动刷新
        self.refresh_recommend()
        self.refresh_chart()

    def refresh_chart(self):
        """刷新K线图"""
        if not self.webview:
            return
        try:
            number = int(self.number_input.text() or "28")
            from core.chart import render_kline_html
            html = render_kline_html(number, 200,
                                    ["ma5", "boll", "kdj", "macd", "rsi"])
            self.webview.setHtml(html)
        except Exception as e:
            if self.webview:
                self.webview.setHtml(f"<h3>❌ {e}</h3>")

    def refresh_recommend(self):
        """刷新AI推荐"""
        try:
            from core.recommender import get_recommendation
            rec = get_recommendation()
            nums = ", ".join(str(n) for n in rec.get("numbers", []))
            self.rec_label.setText(
                f"🎯 推荐号码\n\n"
                f"  {nums}\n\n"
                f"策略: {rec.get('strategy', '')}\n"
                f"信心: {rec.get('confidence', '')}\n"
                f"{rec.get('stats', '')}"
            )
            self.reason_text.setText(rec.get("reason", ""))
        except Exception as e:
            self.rec_label.setText(f"❌ 推荐失败: {e}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F5:
            self.refresh_recommend()
            self.refresh_chart()


def run():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run()
