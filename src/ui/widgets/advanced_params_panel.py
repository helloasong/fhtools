"""高级约束参数面板

提供可折叠的高级参数配置界面，支持预分箱设置、箱子大小约束、
样本数约束、统计检验和正则化等高级选项。
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton,
    QGroupBox, QFormLayout, QToolButton, QSizePolicy,
    QApplication
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal
from typing import Dict, Any, Optional, Tuple


# Tooltip 内容
TOOLTIPS = {
    'max_n_prebins': '预分箱阶段的最大箱数，值越大精度越高但求解越慢',
    'min_prebin_size': '预分箱阶段每箱最小样本占比',
    'min_bin_size': '最终每箱最小样本占比，防止过拟合',
    'max_bin_size': '最终每箱最大样本占比',
    'min_bin_n_event': '每箱最小坏样本数',
    'min_bin_n_nonevent': '每箱最小好样本数',
    'max_pvalue': '箱间差异的最大p-value，超出则合并',
    'gamma': '正则化系数，越大箱子越均匀',
}

# 参数标签
PARAM_LABELS = {
    'max_n_prebins': '预分箱数:',
    'min_prebin_size': '预分箱最小占比:',
    'min_bin_size': '每箱最小占比:',
    'max_bin_size': '每箱最大占比:',
    'min_bin_n_event': '每箱最小坏样本数:',
    'min_bin_n_nonevent': '每箱最小好样本数:',
    'max_pvalue': '最大p-value:',
    'gamma': '正则化Gamma:',
}


class AdvancedParamsPanel(QWidget):
    """可折叠的高级参数面板
    
    提供8个高级参数的交互式配置，支持：
    - 展开/折叠动画
    - 参数启用/禁用（通过复选框控制None值）
    - 参数范围约束
    - 批量获取和设置
    
    Attributes:
        params_changed: 参数发生变化时发出的信号
    """
    
    params_changed = pyqtSignal()
    
    # 默认值
    DEFAULTS = {
        'max_n_prebins': 20,
        'min_prebin_size': 0.05,
        'min_bin_size': None,
        'max_bin_size': None,
        'min_bin_n_event': None,
        'min_bin_n_nonevent': None,
        'max_pvalue': None,
        'gamma': 0.0,
    }
    
    # 参数范围定义 (min, max, step, decimals)
    PARAM_RANGES = {
        'max_n_prebins': (5, 200, 1, 0),
        'min_prebin_size': (0.01, 0.5, 0.01, 2),
        'min_bin_size': (0.0, 0.5, 0.01, 2),
        'max_bin_size': (0.0, 1.0, 0.01, 2),
        'min_bin_n_event': (0, 1000, 1, 0),
        'min_bin_n_nonevent': (0, 1000, 1, 0),
        'max_pvalue': (0.0, 1.0, 0.01, 2),
        'gamma': (0.0, 1.0, 0.01, 2),
    }
    
    # 可为None的参数
    NULLABLE_PARAMS = {'min_bin_size', 'max_bin_size', 'min_bin_n_event', 
                       'min_bin_n_nonevent', 'max_pvalue'}
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_expanded = True
        self._init_ui()
        self._setup_tooltips()
        self._setup_connections()
        self._setup_animations()
        
    def _init_ui(self):
        """初始化界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 折叠按钮
        self.toggle_btn = QPushButton("▼ 高级选项")
        self.toggle_btn.setObjectName("toggleBtn")
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setStyleSheet("""
            QPushButton#toggleBtn {
                background: transparent;
                border: none;
                text-align: left;
                padding: 8px 4px;
                font-weight: bold;
                color: #333;
            }
            QPushButton#toggleBtn:hover {
                color: #1A73E8;
            }
        """)
        main_layout.addWidget(self.toggle_btn)
        
        # 内容容器
        self.content_widget = QWidget()
        self.content_widget.setObjectName("contentWidget")
        self.content_widget.setStyleSheet("""
            QWidget#contentWidget {
                background: #f8f9fa;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)
        
        # 创建参数表单
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        # 创建参数控件字典
        self._param_controls: Dict[str, Tuple[QCheckBox, QWidget]] = {}
        
        # max_n_prebins - 整数，不可为None
        row = self._create_int_param(
            'max_n_prebins', PARAM_LABELS['max_n_prebins'],
            self.DEFAULTS['max_n_prebins'],
            *self.PARAM_RANGES['max_n_prebins'][:2],
            nullable=False
        )
        form_layout.addRow(row[0], row[1])
        
        # min_prebin_size - 浮点数，不可为None
        row = self._create_float_param(
            'min_prebin_size', PARAM_LABELS['min_prebin_size'],
            self.DEFAULTS['min_prebin_size'],
            *self.PARAM_RANGES['min_prebin_size'][:2],
            nullable=False
        )
        form_layout.addRow(row[0], row[1])
        
        # min_bin_size - 浮点数，可为None
        row = self._create_float_param(
            'min_bin_size', PARAM_LABELS['min_bin_size'],
            self.DEFAULTS['min_bin_size'],
            *self.PARAM_RANGES['min_bin_size'][:2],
            nullable=True
        )
        form_layout.addRow(row[0], row[1])
        
        # max_bin_size - 浮点数，可为None
        row = self._create_float_param(
            'max_bin_size', PARAM_LABELS['max_bin_size'],
            self.DEFAULTS['max_bin_size'],
            *self.PARAM_RANGES['max_bin_size'][:2],
            nullable=True
        )
        form_layout.addRow(row[0], row[1])
        
        # min_bin_n_event - 整数，可为None
        row = self._create_int_param(
            'min_bin_n_event', PARAM_LABELS['min_bin_n_event'],
            self.DEFAULTS['min_bin_n_event'],
            *self.PARAM_RANGES['min_bin_n_event'][:2],
            nullable=True
        )
        form_layout.addRow(row[0], row[1])
        
        # min_bin_n_nonevent - 整数，可为None
        row = self._create_int_param(
            'min_bin_n_nonevent', PARAM_LABELS['min_bin_n_nonevent'],
            self.DEFAULTS['min_bin_n_nonevent'],
            *self.PARAM_RANGES['min_bin_n_nonevent'][:2],
            nullable=True
        )
        form_layout.addRow(row[0], row[1])
        
        # max_pvalue - 浮点数，可为None
        row = self._create_float_param(
            'max_pvalue', PARAM_LABELS['max_pvalue'],
            self.DEFAULTS['max_pvalue'],
            *self.PARAM_RANGES['max_pvalue'][:2],
            nullable=True
        )
        form_layout.addRow(row[0], row[1])
        
        # gamma - 浮点数，不可为None
        row = self._create_float_param(
            'gamma', PARAM_LABELS['gamma'],
            self.DEFAULTS['gamma'],
            *self.PARAM_RANGES['gamma'][:2],
            nullable=False
        )
        form_layout.addRow(row[0], row[1])
        
        content_layout.addLayout(form_layout)
        content_layout.addStretch()
        
        main_layout.addWidget(self.content_widget)
        
        # 设置初始值
        self.reset_to_defaults()
        
    def _create_int_param(self, name: str, label: str, default: Optional[int], 
                          min_val: int, max_val: int, nullable: bool = True) -> Tuple[QLabel, QWidget]:
        """创建整数参数行
        
        Args:
            name: 参数名
            label: 显示标签
            default: 默认值（None表示未启用）
            min_val: 最小值
            max_val: 最大值
            nullable: 是否可为None
            
        Returns:
            (标签控件, 参数行控件)元组
        """
        # 创建标签
        label_widget = QLabel(label)
        label_widget.setToolTip(TOOLTIPS.get(name, ''))
        
        # 创建行容器
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        
        # 创建复选框（仅nullable参数）
        checkbox = None
        if nullable:
            checkbox = QCheckBox()
            checkbox.setChecked(default is not None)
            checkbox.setToolTip("启用此参数")
            row_layout.addWidget(checkbox)
        
        # 创建SpinBox
        spinbox = QSpinBox()
        spinbox.setRange(min_val, max_val)
        spinbox.setSingleStep(1)
        spinbox.setFixedWidth(80)
        spinbox.setAlignment(Qt.AlignmentFlag.AlignRight)
        if default is not None:
            spinbox.setValue(default)
        spinbox.setEnabled(not nullable or default is not None)
        row_layout.addWidget(spinbox)
        
        # 帮助按钮
        help_btn = QToolButton()
        help_btn.setText("?")
        help_btn.setToolTip(TOOLTIPS.get(name, ''))
        help_btn.setStyleSheet("""
            QToolButton {
                background: #e3f2fd;
                color: #1976d2;
                border: none;
                border-radius: 10px;
                width: 20px;
                height: 20px;
                font-size: 11px;
                font-weight: bold;
            }
            QToolButton:hover {
                background: #bbdefb;
            }
        """)
        row_layout.addWidget(help_btn)
        
        row_layout.addStretch()
        
        # 保存控件引用
        self._param_controls[name] = (checkbox, spinbox)
        
        return label_widget, row_widget
        
    def _create_float_param(self, name: str, label: str, default: Optional[float],
                            min_val: float, max_val: float, nullable: bool = True,
                            decimals: int = 2) -> Tuple[QLabel, QWidget]:
        """创建浮点参数行
        
        Args:
            name: 参数名
            label: 显示标签
            default: 默认值（None表示未启用）
            min_val: 最小值
            max_val: 最大值
            nullable: 是否可为None
            decimals: 小数位数
            
        Returns:
            (标签控件, 参数行控件)元组
        """
        # 创建标签
        label_widget = QLabel(label)
        label_widget.setToolTip(TOOLTIPS.get(name, ''))
        
        # 创建行容器
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        
        # 创建复选框（仅nullable参数）
        checkbox = None
        if nullable:
            checkbox = QCheckBox()
            checkbox.setChecked(default is not None)
            checkbox.setToolTip("启用此参数")
            row_layout.addWidget(checkbox)
        
        # 创建DoubleSpinBox
        spinbox = QDoubleSpinBox()
        spinbox.setRange(min_val, max_val)
        spinbox.setSingleStep(0.01)
        spinbox.setDecimals(decimals)
        spinbox.setFixedWidth(80)
        spinbox.setAlignment(Qt.AlignmentFlag.AlignRight)
        if default is not None:
            spinbox.setValue(default)
        else:
            spinbox.setSpecialValueText("None")
            spinbox.setValue(min_val)
        spinbox.setEnabled(not nullable or default is not None)
        row_layout.addWidget(spinbox)
        
        # 帮助按钮
        help_btn = QToolButton()
        help_btn.setText("?")
        help_btn.setToolTip(TOOLTIPS.get(name, ''))
        help_btn.setStyleSheet("""
            QToolButton {
                background: #e3f2fd;
                color: #1976d2;
                border: none;
                border-radius: 10px;
                width: 20px;
                height: 20px;
                font-size: 11px;
                font-weight: bold;
            }
            QToolButton:hover {
                background: #bbdefb;
            }
        """)
        row_layout.addWidget(help_btn)
        
        row_layout.addStretch()
        
        # 保存控件引用
        self._param_controls[name] = (checkbox, spinbox)
        
        return label_widget, row_widget
        
    def _setup_tooltips(self):
        """设置控件 Tooltip 提示"""
        # Tooltips已在创建控件时设置
        self.toggle_btn.setToolTip("点击展开/折叠高级参数设置")
        
    def _setup_connections(self):
        """设置信号连接"""
        # 折叠按钮
        self.toggle_btn.clicked.connect(self._on_toggle_clicked)
        
        # 参数变化信号
        for name, (checkbox, spinbox) in self._param_controls.items():
            if checkbox:
                checkbox.stateChanged.connect(
                    lambda state, n=name: self._on_checkbox_changed(n, state)
                )
            if isinstance(spinbox, (QSpinBox, QDoubleSpinBox)):
                spinbox.valueChanged.connect(
                    lambda v, n=name: self._on_value_changed(n, v)
                )
                
    def _setup_animations(self):
        """设置折叠动画"""
        self._animation = QPropertyAnimation(self.content_widget, b"maximumHeight")
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
    def _on_toggle_clicked(self):
        """处理折叠按钮点击"""
        self.set_expanded(not self._is_expanded)
        
    def _on_checkbox_changed(self, name: str, state: int):
        """处理复选框状态变化"""
        checkbox, spinbox = self._param_controls[name]
        spinbox.setEnabled(state == Qt.CheckState.Checked.value)
        self.params_changed.emit()
        
    def _on_value_changed(self, name: str, value):
        """处理数值变化"""
        self.params_changed.emit()
        
    def get_params(self) -> Dict[str, Any]:
        """获取高级参数字典
        
        返回包含所有参数的 dict，None 值表示未启用（复选框未勾选）。
        对于不可为None的参数，始终返回当前值。
        
        Returns:
            参数字典，键包括:
            - max_n_prebins: 预分箱数
            - min_prebin_size: 预分箱最小占比
            - min_bin_size: 每箱最小占比（可为None）
            - max_bin_size: 每箱最大占比（可为None）
            - min_bin_n_event: 每箱最小坏样本数（可为None）
            - min_bin_n_nonevent: 每箱最小好样本数（可为None）
            - max_pvalue: 最大p-value（可为None）
            - gamma: 正则化系数
        """
        params = {}
        
        for name, (checkbox, spinbox) in self._param_controls.items():
            if checkbox and not checkbox.isChecked():
                # 复选框未勾选，返回None
                params[name] = None
            else:
                # 返回当前值
                if isinstance(spinbox, QSpinBox):
                    params[name] = spinbox.value()
                elif isinstance(spinbox, QDoubleSpinBox):
                    params[name] = spinbox.value()
                    
        return params
        
    def set_params(self, params: Dict[str, Any]):
        """设置参数值
        
        Args:
            params: 参数字典，可包含以下键:
                - max_n_prebins: int
                - min_prebin_size: float
                - min_bin_size: float或None
                - max_bin_size: float或None
                - min_bin_n_event: int或None
                - min_bin_n_nonevent: int或None
                - max_pvalue: float或None
                - gamma: float
        """
        for name, value in params.items():
            if name not in self._param_controls:
                continue
                
            checkbox, spinbox = self._param_controls[name]
            
            if value is None:
                # 设置为None（禁用）
                if checkbox:
                    checkbox.setChecked(False)
                    spinbox.setEnabled(False)
            else:
                # 设置值
                if checkbox:
                    checkbox.setChecked(True)
                    spinbox.setEnabled(True)
                    
                if isinstance(spinbox, QSpinBox):
                    spinbox.setValue(int(value))
                elif isinstance(spinbox, QDoubleSpinBox):
                    spinbox.setValue(float(value))
                    
    def reset_to_defaults(self):
        """重置为默认值"""
        self.set_params(self.DEFAULTS)
        
    def is_expanded(self) -> bool:
        """返回是否展开"""
        return self._is_expanded
        
    def set_expanded(self, expanded: bool):
        """设置展开/折叠状态
        
        Args:
            expanded: True为展开，False为折叠
        """
        self._is_expanded = expanded
        
        # 更新按钮文本
        self.toggle_btn.setText("▼ 高级选项" if expanded else "▶ 高级选项")
        
        # 执行动画
        if expanded:
            # 展开：先显示，然后动画到自然高度
            self.content_widget.setMaximumHeight(0)
            self.content_widget.show()
            
            # 计算目标高度
            self.content_widget.adjustSize()
            target_height = self.content_widget.sizeHint().height()
            
            self._animation.setStartValue(0)
            self._animation.setEndValue(target_height)
            self._animation.finished.connect(self._on_expand_finished)
        else:
            # 折叠：动画到0
            current_height = self.content_widget.height()
            self._animation.setStartValue(current_height)
            self._animation.setEndValue(0)
            self._animation.finished.connect(self._on_collapse_finished)
            
        self._animation.start()
        
    def _on_expand_finished(self):
        """展开动画完成回调"""
        self._animation.finished.disconnect(self._on_expand_finished)
        self.content_widget.setMaximumHeight(16777215)  # 解除高度限制
        
    def _on_collapse_finished(self):
        """折叠动画完成回调"""
        self._animation.finished.disconnect(self._on_collapse_finished)
        self.content_widget.hide()


if __name__ == '__main__':
    # 测试代码
    import sys
    
    app = QApplication(sys.argv)
    
    # 创建主窗口
    window = QWidget()
    window.setWindowTitle("AdvancedParamsPanel Test")
    window.resize(400, 600)
    
    layout = QVBoxLayout(window)
    
    # 添加面板
    panel = AdvancedParamsPanel()
    layout.addWidget(panel)
    layout.addStretch()
    
    # 添加测试按钮
    test_btn = QPushButton("获取参数")
    test_btn.clicked.connect(lambda: print(panel.get_params()))
    layout.addWidget(test_btn)
    
    reset_btn = QPushButton("重置")
    reset_btn.clicked.connect(panel.reset_to_defaults)
    layout.addWidget(reset_btn)
    
    window.show()
    sys.exit(app.exec())
