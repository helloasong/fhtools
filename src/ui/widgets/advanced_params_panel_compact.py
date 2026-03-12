"""高级约束参数面板 - 紧凑美化版"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton,
    QGridLayout, QComboBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, Any, Optional


class AdvancedParamsPanel(QWidget):
    """高级约束参数面板 - 紧凑美化版
    
    参数分组展示，支持Nullable参数（checkbox+输入框联动）
    """
    
    params_changed = pyqtSignal()
    
    # 默认值
    DEFAULTS = {
        'max_n_prebins': 20,
        'min_prebin_size': 0.05,
        'prebinning_method': 'cart',
        'min_bin_size': None,
        'max_bin_size': None,
        'min_bin_n_event': None,
        'max_bin_n_event': None,
        'min_bin_n_nonevent': None,
        'max_bin_n_nonevent': None,
        'min_event_rate_diff': 0.0,
        'max_pvalue': None,
        'max_pvalue_policy': 'consecutive',
        'split_digits': None,
        'gamma': 0.0,
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = False
        self._init_ui()
        
    def _init_ui(self):
        """初始化界面 - 美化版"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)
        
        # 折叠按钮
        self.toggle_btn = QPushButton("▶ 高级选项")
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                text-align: left;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 12px;
                color: #555;
            }
            QPushButton:hover {
                color: #000;
            }
        """)
        self.toggle_btn.clicked.connect(self._toggle)
        main_layout.addWidget(self.toggle_btn)
        
        # 内容容器 - 带边框卡片样式
        self.content_widget = QWidget()
        self.content_widget.setVisible(False)
        # 折叠时不占用空间
        self.content_widget.setSizePolicy(
            self.content_widget.sizePolicy().horizontalPolicy(),
            self.content_widget.sizePolicy().verticalPolicy().Ignored
        )
        self.content_widget.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
            }
        """)
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(12)
        
        # ===== 第一组：预分箱参数 =====
        prebin_group = self._create_group("预分箱设置")
        prebin_grid = QGridLayout()
        prebin_grid.setSpacing(8)
        prebin_grid.setColumnStretch(1, 1)
        prebin_grid.setColumnStretch(3, 1)
        
        # 预分箱方法
        prebin_grid.addWidget(QLabel("预分箱方法:"), 0, 0)
        self.prebin_method_combo = QComboBox()
        for val, label in [('cart', 'CART(决策树)'), ('quantile', '等频'), ('uniform', '等距')]:
            self.prebin_method_combo.addItem(label, val)
        self.prebin_method_combo.setFixedWidth(110)
        prebin_grid.addWidget(self.prebin_method_combo, 0, 1)
        
        # 预分箱数
        prebin_grid.addWidget(QLabel("预分箱数:"), 0, 2)
        self.max_n_prebins_spin = QSpinBox()
        self.max_n_prebins_spin.setRange(5, 200)
        self.max_n_prebins_spin.setValue(20)
        self.max_n_prebins_spin.setFixedWidth(70)
        prebin_grid.addWidget(self.max_n_prebins_spin, 0, 3)
        
        # 预分箱最小占比
        prebin_grid.addWidget(QLabel("最小占比:"), 1, 0)
        self.min_prebin_size_spin = QDoubleSpinBox()
        self.min_prebin_size_spin.setRange(0.01, 0.5)
        self.min_prebin_size_spin.setValue(0.05)
        self.min_prebin_size_spin.setDecimals(2)
        self.min_prebin_size_spin.setFixedWidth(70)
        prebin_grid.addWidget(self.min_prebin_size_spin, 1, 1)
        
        prebin_group.layout().addLayout(prebin_grid)
        content_layout.addWidget(prebin_group)
        
        # ===== 第二组：分箱大小约束 =====
        size_group = self._create_group("分箱大小约束 (可选)")
        size_grid = QGridLayout()
        size_grid.setSpacing(8)
        size_grid.setColumnStretch(1, 1)
        size_grid.setColumnStretch(3, 1)
        size_grid.setColumnStretch(5, 1)
        size_grid.setColumnStretch(7, 1)
        
        # 参数定义: (key, label, min, max, is_int, default, col)
        size_params = [
            ('min_bin_size', '最小占比:', 0.0, 0.5, False, 0.01),
            ('max_bin_size', '最大占比:', 0.0, 1.0, False, 0.5),
            ('min_bin_n_event', '最少坏样本:', 0, 10000, True, 1),
            ('max_bin_n_event', '最多坏样本:', 0, 100000, True, 1000),
            ('min_bin_n_nonevent', '最少好样本:', 0, 10000, True, 1),
            ('max_bin_n_nonevent', '最多好样本:', 0, 100000, True, 1000),
        ]
        
        self._size_controls = {}
        for i, (key, label, min_v, max_v, is_int, default) in enumerate(size_params):
            row = i // 2
            col = (i % 2) * 4  # 0, 4
            
            # 复选框 + 标签
            chk = QCheckBox(label)
            chk.setStyleSheet("font-size: 11px;")
            size_grid.addWidget(chk, row, col)
            
            # 输入框
            if is_int:
                spin = QSpinBox()
                spin.setRange(min_v, max_v)
                spin.setValue(default)
            else:
                spin = QDoubleSpinBox()
                spin.setRange(min_v, max_v)
                spin.setDecimals(2 if 'size' in key else 0)
                spin.setValue(default)
            spin.setFixedWidth(70)
            spin.setEnabled(False)
            spin.setStyleSheet("padding: 2px;")
            size_grid.addWidget(spin, row, col + 1)
            
            chk.stateChanged.connect(lambda state, s=spin: s.setEnabled(state == Qt.CheckState.Checked.value))
            chk.stateChanged.connect(self.params_changed.emit)
            spin.valueChanged.connect(self.params_changed.emit)
            
            self._size_controls[key] = (chk, spin)
        
        size_group.layout().addLayout(size_grid)
        content_layout.addWidget(size_group)
        
        # ===== 第三组：统计约束 =====
        stat_group = self._create_group("统计约束")
        stat_grid = QGridLayout()
        stat_grid.setSpacing(8)
        stat_grid.setColumnStretch(1, 1)
        stat_grid.setColumnStretch(3, 1)
        
        # 最大p值
        stat_grid.addWidget(QLabel("最大p值:"), 0, 0)
        self.max_pvalue_chk = QCheckBox()
        stat_grid.addWidget(self.max_pvalue_chk, 0, 1, alignment=Qt.AlignmentFlag.AlignRight)
        self.max_pvalue_spin = QDoubleSpinBox()
        self.max_pvalue_spin.setRange(0.0, 1.0)
        self.max_pvalue_spin.setValue(0.05)
        self.max_pvalue_spin.setDecimals(3)
        self.max_pvalue_spin.setFixedWidth(70)
        self.max_pvalue_spin.setEnabled(False)
        stat_grid.addWidget(self.max_pvalue_spin, 0, 2)
        
        # p值策略
        stat_grid.addWidget(QLabel("p值策略:"), 0, 3)
        self.pvalue_policy_combo = QComboBox()
        for val, label in [('consecutive', '相邻'), ('all', '全部')]:
            self.pvalue_policy_combo.addItem(label, val)
        self.pvalue_policy_combo.setFixedWidth(80)
        stat_grid.addWidget(self.pvalue_policy_combo, 0, 4)
        
        # 最小事件率差异
        stat_grid.addWidget(QLabel("最小事件率差异:"), 1, 0)
        self.min_event_rate_diff_spin = QDoubleSpinBox()
        self.min_event_rate_diff_spin.setRange(0.0, 0.5)
        self.min_event_rate_diff_spin.setValue(0.0)
        self.min_event_rate_diff_spin.setDecimals(3)
        self.min_event_rate_diff_spin.setFixedWidth(70)
        stat_grid.addWidget(self.min_event_rate_diff_spin, 1, 1)
        
        # 切点精度
        stat_grid.addWidget(QLabel("切点精度:"), 1, 3)
        self.split_digits_chk = QCheckBox()
        stat_grid.addWidget(self.split_digits_chk, 1, 4, alignment=Qt.AlignmentFlag.AlignRight)
        self.split_digits_spin = QSpinBox()
        self.split_digits_spin.setRange(0, 12)
        self.split_digits_spin.setValue(2)
        self.split_digits_spin.setFixedWidth(70)
        self.split_digits_spin.setEnabled(False)
        stat_grid.addWidget(self.split_digits_spin, 1, 5)
        
        # Gamma正则化
        stat_grid.addWidget(QLabel("Gamma正则化:"), 2, 0)
        self.gamma_spin = QDoubleSpinBox()
        self.gamma_spin.setRange(0.0, 1.0)
        self.gamma_spin.setValue(0.0)
        self.gamma_spin.setDecimals(2)
        self.gamma_spin.setFixedWidth(70)
        stat_grid.addWidget(self.gamma_spin, 2, 1)
        
        # 信号连接
        self.max_pvalue_chk.stateChanged.connect(
            lambda s: self.max_pvalue_spin.setEnabled(s == Qt.CheckState.Checked.value))
        self.max_pvalue_chk.stateChanged.connect(self.params_changed.emit)
        self.max_pvalue_spin.valueChanged.connect(self.params_changed.emit)
        self.pvalue_policy_combo.currentIndexChanged.connect(self.params_changed.emit)
        self.min_event_rate_diff_spin.valueChanged.connect(self.params_changed.emit)
        self.split_digits_chk.stateChanged.connect(
            lambda s: self.split_digits_spin.setEnabled(s == Qt.CheckState.Checked.value))
        self.split_digits_chk.stateChanged.connect(self.params_changed.emit)
        self.split_digits_spin.valueChanged.connect(self.params_changed.emit)
        self.gamma_spin.valueChanged.connect(self.params_changed.emit)
        self.prebin_method_combo.currentIndexChanged.connect(self.params_changed.emit)
        self.max_n_prebins_spin.valueChanged.connect(self.params_changed.emit)
        self.min_prebin_size_spin.valueChanged.connect(self.params_changed.emit)
        
        stat_group.layout().addLayout(stat_grid)
        content_layout.addWidget(stat_group)
        
        main_layout.addWidget(self.content_widget)
        self._update_toggle_btn()
        
    def _create_group(self, title: str) -> QFrame:
        """创建带标题的分组框"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)
        
        # 标题
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("""
            font-size: 11px;
            font-weight: bold;
            color: #333;
            padding-bottom: 4px;
            border-bottom: 1px solid #eee;
        """)
        layout.addWidget(title_lbl)
        
        return frame
        
    def _toggle(self):
        """切换折叠状态"""
        self._expanded = not self._expanded
        self.content_widget.setVisible(self._expanded)
        
        # 根据展开状态调整大小策略
        if self._expanded:
            self.content_widget.setSizePolicy(
                self.content_widget.sizePolicy().horizontalPolicy(),
                self.content_widget.sizePolicy().verticalPolicy().Preferred
            )
        else:
            self.content_widget.setSizePolicy(
                self.content_widget.sizePolicy().horizontalPolicy(),
                self.content_widget.sizePolicy().verticalPolicy().Ignored
            )
        
        self._update_toggle_btn()
        
        # 触发布局更新，确保滚动区域能正确计算大小
        if self.parentWidget():
            self.adjustSize()
            self.parentWidget().adjustSize()
        
    def _update_toggle_btn(self):
        """更新按钮文本"""
        arrow = "▼" if self._expanded else "▶"
        self.toggle_btn.setText(f"{arrow} 高级选项")
        
    def get_params(self) -> Dict[str, Any]:
        """获取参数"""
        params = {
            'prebinning_method': self.prebin_method_combo.currentData(),
            'max_n_prebins': self.max_n_prebins_spin.value(),
            'min_prebin_size': self.min_prebin_size_spin.value(),
            'min_event_rate_diff': self.min_event_rate_diff_spin.value(),
            'max_pvalue_policy': self.pvalue_policy_combo.currentData(),
            'gamma': self.gamma_spin.value(),
        }
        
        # 可选参数
        if self.max_pvalue_chk.isChecked():
            params['max_pvalue'] = self.max_pvalue_spin.value()
        if self.split_digits_chk.isChecked():
            params['split_digits'] = self.split_digits_spin.value()
            
        # 大小约束参数
        for key, (chk, spin) in self._size_controls.items():
            if chk.isChecked():
                params[key] = spin.value()
                
        return params
        
    def set_params(self, params: Dict[str, Any]):
        """设置参数"""
        # 预分箱方法
        if 'prebinning_method' in params:
            idx = self.prebin_method_combo.findData(params['prebinning_method'])
            if idx >= 0:
                self.prebin_method_combo.setCurrentIndex(idx)
        if 'max_n_prebins' in params:
            self.max_n_prebins_spin.setValue(params['max_n_prebins'])
        if 'min_prebin_size' in params:
            self.min_prebin_size_spin.setValue(params['min_prebin_size'])
            
        # 大小约束
        for key, (chk, spin) in self._size_controls.items():
            if key in params:
                value = params[key]
                if value is None:
                    chk.setChecked(False)
                    spin.setEnabled(False)
                else:
                    chk.setChecked(True)
                    spin.setEnabled(True)
                    spin.setValue(value)
                    
        # 统计约束
        if 'max_pvalue' in params:
            if params['max_pvalue'] is None:
                self.max_pvalue_chk.setChecked(False)
            else:
                self.max_pvalue_chk.setChecked(True)
                self.max_pvalue_spin.setValue(params['max_pvalue'])
        if 'max_pvalue_policy' in params:
            idx = self.pvalue_policy_combo.findData(params['max_pvalue_policy'])
            if idx >= 0:
                self.pvalue_policy_combo.setCurrentIndex(idx)
        if 'min_event_rate_diff' in params:
            self.min_event_rate_diff_spin.setValue(params['min_event_rate_diff'])
        if 'split_digits' in params:
            if params['split_digits'] is None:
                self.split_digits_chk.setChecked(False)
            else:
                self.split_digits_chk.setChecked(True)
                self.split_digits_spin.setValue(params['split_digits'])
        if 'gamma' in params:
            self.gamma_spin.setValue(params['gamma'])
                    
    def reset_to_defaults(self):
        """重置为默认值"""
        self.prebin_method_combo.setCurrentIndex(0)
        self.max_n_prebins_spin.setValue(self.DEFAULTS['max_n_prebins'])
        self.min_prebin_size_spin.setValue(self.DEFAULTS['min_prebin_size'])
        self.min_event_rate_diff_spin.setValue(self.DEFAULTS['min_event_rate_diff'])
        self.pvalue_policy_combo.setCurrentIndex(0)
        self.gamma_spin.setValue(self.DEFAULTS['gamma'])
        
        self.max_pvalue_chk.setChecked(False)
        self.split_digits_chk.setChecked(False)
        
        for key, (chk, spin) in self._size_controls.items():
            chk.setChecked(False)
            spin.setEnabled(False)
                    
    def set_expanded(self, expanded: bool):
        """设置展开状态"""
        self._expanded = expanded
        self.content_widget.setVisible(expanded)
        self._update_toggle_btn()
        
    def is_expanded(self) -> bool:
        """是否展开"""
        return self._expanded
