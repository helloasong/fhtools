from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QDoubleSpinBox, QComboBox, QGroupBox, QCheckBox
)
from src.core.cross_binning import CrossBinningFilters


class CrossBinningParamsPanel(QGroupBox):
    """组合策略筛选参数配置面板"""

    def __init__(self, parent=None):
        super().__init__("筛选条件", parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 14, 10, 10)

        # 不过滤模式开关
        self.show_all_check = QCheckBox("展示全部组合（不过滤）")
        self.show_all_check.setToolTip(
            "勾选后显示所有组合的排序结果，不做任何筛选过滤。\n"
            "适合全面了解多变量交叉后的完整分布。"
        )
        self.show_all_check.stateChanged.connect(self._on_show_all_changed)
        layout.addWidget(self.show_all_check)

        # 最小样本占比
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("最小样本占比:"))
        self.min_sample_spin = QDoubleSpinBox()
        self.min_sample_spin.setRange(0.001, 0.20)
        self.min_sample_spin.setValue(0.005)
        self.min_sample_spin.setSingleStep(0.005)
        self.min_sample_spin.setDecimals(3)
        self.min_sample_spin.setSuffix(" (0.1%~20%)")
        self.min_sample_spin.setMinimumWidth(140)
        row1.addWidget(self.min_sample_spin)
        layout.addLayout(row1)

        # 高风险倍数
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("高风险倍数 (≥):"))
        self.high_mult_spin = QDoubleSpinBox()
        self.high_mult_spin.setRange(1.0, 10.0)
        self.high_mult_spin.setValue(2.0)
        self.high_mult_spin.setSingleStep(0.5)
        self.high_mult_spin.setDecimals(1)
        row2.addWidget(self.high_mult_spin)
        layout.addLayout(row2)

        # 优质客群倍数
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("优质客群倍数 (≤):"))
        self.low_mult_spin = QDoubleSpinBox()
        self.low_mult_spin.setRange(0.05, 1.0)
        self.low_mult_spin.setValue(0.5)
        self.low_mult_spin.setSingleStep(0.05)
        self.low_mult_spin.setDecimals(2)
        row3.addWidget(self.low_mult_spin)
        layout.addLayout(row3)

        # 最小 Lift
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("最小 Lift:"))
        self.min_lift_spin = QDoubleSpinBox()
        self.min_lift_spin.setRange(1.0, 10.0)
        self.min_lift_spin.setValue(1.0)
        self.min_lift_spin.setSingleStep(0.5)
        self.min_lift_spin.setDecimals(1)
        row4.addWidget(self.min_lift_spin)
        layout.addLayout(row4)

        # 排序方式
        row5 = QHBoxLayout()
        row5.addWidget(QLabel("排序方式:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("坏账率降序", "bad_rate_desc")
        self.sort_combo.addItem("Lift降序", "lift_desc")
        self.sort_combo.addItem("样本数降序", "sample_desc")
        row5.addWidget(self.sort_combo)
        layout.addLayout(row5)

        layout.addStretch()

    def _on_show_all_changed(self, state):
        """不过滤模式切换时禁用/启用筛选参数"""
        enabled = state == 0  # Qt.Unchecked
        self.min_sample_spin.setEnabled(enabled)
        self.high_mult_spin.setEnabled(enabled)
        self.low_mult_spin.setEnabled(enabled)
        self.min_lift_spin.setEnabled(enabled)

    def get_filters(self) -> CrossBinningFilters:
        """获取当前配置的筛选参数"""
        return CrossBinningFilters(
            min_sample_rate=self.min_sample_spin.value(),
            bad_rate_high_multiplier=self.high_mult_spin.value(),
            bad_rate_low_multiplier=self.low_mult_spin.value(),
            min_lift=self.min_lift_spin.value(),
            sort_by=self.sort_combo.currentData(),
            show_all=self.show_all_check.isChecked(),
        )
