"""
过滤效果预览面板

展示过滤前后样本数对比，卡片式容器。
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel

from src.core.filtering.engine import FilterPreviewResult


class FilterPreviewPanel(QWidget):
    """过滤效果预览面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            FilterPreviewPanel {
                background: linear-gradient(to bottom, #FFFFFF, #F4F7FB);
                border: 1px solid #E3E6EA;
                border-radius: 10px;
                padding: 12px 16px;
            }
            QLabel {
                font-size: 13px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 12, 16, 12)

        self.lbl_total = QLabel("过滤前: -")
        self.lbl_total.setStyleSheet("color: #333;")

        self.lbl_filtered = QLabel("过滤后: -")
        self.lbl_filtered.setStyleSheet("color: #4CAF50; font-weight: bold;")

        self.lbl_removed = QLabel("已过滤: -")
        self.lbl_removed.setStyleSheet("color: #E53935;")

        self.lbl_ratio = QLabel("比例: -")
        self.lbl_ratio.setStyleSheet("color: #666;")

        layout.addWidget(self.lbl_total)
        layout.addWidget(QLabel("|"))
        layout.addWidget(self.lbl_filtered)
        layout.addWidget(QLabel("|"))
        layout.addWidget(self.lbl_removed)
        layout.addWidget(QLabel("|"))
        layout.addWidget(self.lbl_ratio)
        layout.addStretch()

    def set_result(self, result: FilterPreviewResult):
        """设置预览结果"""
        self.lbl_total.setText(f"过滤前: {result.total_samples:,}")
        self.lbl_filtered.setText(f"过滤后: {result.filtered_samples:,}")
        self.lbl_removed.setText(f"已过滤: {result.removed_samples:,}")
        self.lbl_ratio.setText(f"比例: {result.removal_ratio:.2%}")

    def clear(self):
        """清空预览"""
        self.lbl_total.setText("过滤前: -")
        self.lbl_filtered.setText("过滤后: -")
        self.lbl_removed.setText("已过滤: -")
        self.lbl_ratio.setText("比例: -")
