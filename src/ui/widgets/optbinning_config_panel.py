"""Optbinning 配置面板（Phase 2 增强版）

集成高级参数面板、富文本提示和求解状态显示，提供完整的 Optbinning 配置界面。
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QPushButton,
    QFormLayout, QGroupBox, QMessageBox, QGridLayout,
    QDialog, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, Any, Optional

from src.utils.recommend_params import get_recommended_params, get_data_scale_label
from src.ui.widgets.advanced_params_panel import AdvancedParamsPanel
from src.ui.widgets.rich_tooltip_label import RichTooltipHelper, get_param_tooltip
from src.ui.widgets.solve_status_widget import SolveStatusWidget


# 求解器选项
SOLVER_OPTIONS = [
    ('cp', 'CP (约束编程)'),
    ('mip', 'MIP (混合整数规划)'),
    ('ls', 'LS (LocalSolver)'),
]

# 优化目标（散度度量）选项
DIVERGENCE_OPTIONS = [
    ('iv', 'IV (信息值)'),
    ('js', 'JS (Jensen-Shannon)'),
    ('hellinger', 'Hellinger 散度'),
    ('triangular', '三角判别'),
]

# 单调性趋势选项
MONOTONIC_TREND_OPTIONS = [
    ('auto', '自动检测'),
    ('ascending', '递增'),
    ('descending', '递减'),
    ('concave', '凹形'),
    ('convex', '凸形'),
    ('peak', '单峰'),
    ('valley', '单谷'),
]

# 默认配置
DEFAULT_CONFIG = {
    'solver': 'cp',
    'divergence': 'iv',
    'monotonic_trend': 'auto',
    'min_n_bins': 2,
    'max_n_bins': 10,
    'special_codes': '',
    'time_limit': 100,
    'dtype': 'auto',
    'cat_cutoff': 0.05,
}

# 变量类型选项
DTYPE_OPTIONS = [
    ('auto', '🔍 自动检测'),
    ('numerical', '🔢 数值型'),
    ('categorical', '🏷️ 分类型'),
]

# 高级参数键名列表
ADVANCED_PARAM_KEYS = [
    'max_n_prebins', 'min_prebin_size', 'min_bin_size',
    'max_bin_size', 'min_bin_n_event', 'min_bin_n_nonevent',
    'max_pvalue', 'gamma'
]


class RecommendConfirmDialog(QDialog):
    """推荐参数确认对话框"""
    
    def __init__(self, n_samples: int, recommended: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.n_samples = n_samples
        self.recommended = recommended
        self.setWindowTitle("应用推荐参数")
        self.setMinimumWidth(450)
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # 数据规模说明
        scale_label = QLabel(f"当前数据规模: {get_data_scale_label(self.n_samples)}")
        scale_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #1A73E8;")
        layout.addWidget(scale_label)
        
        # 推荐参数表格
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["参数", "推荐值"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # 参数显示映射
        param_labels = {
            'solver': '求解器',
            'divergence': '优化目标',
            'monotonic_trend': '单调性趋势',
            'max_n_bins': '最大箱数',
            'min_n_bins': '最小箱数',
            'time_limit': '求解时间限制(秒)',
            'max_n_prebins': '预分箱数量',
            'min_prebin_size': '预分箱最小占比',
            'min_bin_size': '每箱最小占比',
            'max_bin_size': '每箱最大占比',
            'min_bin_n_event': '每箱最小坏样本数',
            'min_bin_n_nonevent': '每箱最小好样本数',
            'max_pvalue': '最大p-value',
            'gamma': '正则化系数',
        }
        
        # 选项映射
        solver_labels = {
            'cp': 'CP (约束编程)',
            'mip': 'MIP (混合整数规划)',
            'ls': 'LS (LocalSolver)',
        }
        divergence_labels = {
            'iv': 'IV (信息值)',
            'js': 'JS (Jensen-Shannon)',
            'hellinger': 'Hellinger 散度',
            'triangular': '三角判别',
        }
        monotonic_labels = {
            'auto': '自动检测',
            'ascending': '递增',
            'descending': '递减',
            'concave': '凹形',
            'convex': '凸形',
            'peak': '单峰',
            'valley': '单谷',
        }
        
        # 填充表格
        display_params = []
        
        # 基础参数
        if 'solver' in self.recommended:
            display_params.append(('solver', solver_labels.get(self.recommended.get('solver', 'cp'), 'CP')))
        if 'divergence' in self.recommended:
            display_params.append(('divergence', divergence_labels.get(self.recommended.get('divergence', 'iv'), 'IV')))
        if 'monotonic_trend' in self.recommended:
            display_params.append(('monotonic_trend', monotonic_labels.get(self.recommended.get('monotonic_trend', 'auto'), '自动检测')))
        if 'max_n_bins' in self.recommended:
            display_params.append(('max_n_bins', str(self.recommended.get('max_n_bins', 10))))
        if 'min_n_bins' in self.recommended:
            display_params.append(('min_n_bins', str(self.recommended.get('min_n_bins', 2))))
        if 'time_limit' in self.recommended:
            display_params.append(('time_limit', str(self.recommended.get('time_limit', 100))))
            
        # 高级参数
        for key in ADVANCED_PARAM_KEYS:
            if key in self.recommended and self.recommended[key] is not None:
                value = self.recommended[key]
                if isinstance(value, float):
                    value = f"{value:.4f}"
                display_params.append((key, str(value)))
        
        table.setRowCount(len(display_params))
        for row, (key, value) in enumerate(display_params):
            table.setItem(row, 0, QTableWidgetItem(param_labels.get(key, key)))
            table.setItem(row, 1, QTableWidgetItem(str(value)))
        
        table.setMaximumHeight(min(300, table.verticalHeader().length() + 50))
        layout.addWidget(table)
        
        # 说明文字
        note = QLabel("系统将自动调整求解器、箱数范围、时间限制和高级参数以获得最佳效果。")
        note.setWordWrap(True)
        note.setStyleSheet("color: #666; margin-top: 8px;")
        layout.addWidget(note)
        
        # 按钮
        from PyQt6.QtWidgets import QDialogButtonBox
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.button(QDialogButtonBox.StandardButton.Apply).setText("应用")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)


class OptbinningConfigPanel(QWidget):
    """Optbinning 配置面板（含高级参数和状态显示）
    
    提供 Optbinning 专属配置界面，集成：
    - 基础配置（求解器、优化目标、单调性等）
    - 特殊值处理
    - 高级参数面板（可折叠）
    - 求解状态显示
    - 推荐参数恢复
    
    Attributes:
        solver_combo: 求解器下拉框
        divergence_combo: 优化目标下拉框
        monotonic_combo: 单调性趋势下拉框
        min_bins_spin: 最小箱数 SpinBox
        max_bins_spin: 最大箱数 SpinBox
        time_limit_spin: 求解时间限制 SpinBox
        special_codes_edit: 特殊值输入框
        advanced_panel: 高级参数面板
        status_widget: 求解状态显示
        recommend_btn: 恢复推荐按钮
    """
    
    # 信号：参数变化时发出
    params_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.n_samples = 0
        self._init_ui()
        self._connect_signals()
        # 初始化 dtype 相关控件的可见性
        self._on_dtype_changed()
        
    def _init_ui(self):
        """初始化界面"""
        # 设置面板整体尺寸限制
        self.setMaximumHeight(500)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        
        # === 基础配置组 ===
        basic_group = self._create_basic_config_group()
        basic_group.setMaximumHeight(200)
        main_layout.addWidget(basic_group)
        
        # === 特殊值处理组 ===
        special_group = self._create_special_codes_group()
        special_group.setMaximumHeight(80)
        main_layout.addWidget(special_group)
        
        # === 高级参数面板（可折叠） ===
        self.advanced_panel = AdvancedParamsPanel()
        self.advanced_panel.setMaximumHeight(200)
        main_layout.addWidget(self.advanced_panel)
        
        # === 求解状态显示 ===
        self.status_widget = SolveStatusWidget(detailed=True)
        self.status_widget.setMaximumHeight(100)
        main_layout.addWidget(self.status_widget)
        
        # === 操作按钮 ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.recommend_btn = QPushButton("⚡ 恢复推荐")
        self.recommend_btn.setObjectName("recommendBtn")
        self.recommend_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.recommend_btn.setStyleSheet("""
            QPushButton#recommendBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4CAF50, stop:1 #45A049);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton#recommendBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #45A049, stop:1 #3D8B40);
            }
            QPushButton#recommendBtn:pressed {
                background: #3D8B40;
            }
        """)
        btn_layout.addWidget(self.recommend_btn)
        main_layout.addLayout(btn_layout)
        
        main_layout.addStretch()
        
        # 设置整体样式
        self._setup_styles()
        
    def _create_basic_config_group(self) -> QGroupBox:
        """创建基础配置组"""
        basic_group = QGroupBox("基础配置")
        basic_layout = QFormLayout(basic_group)
        basic_layout.setSpacing(12)
        basic_layout.setContentsMargins(16, 20, 16, 16)
        basic_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # 变量类型（带富文本提示）
        dtype_layout = QHBoxLayout()
        dtype_layout.setSpacing(8)
        self.dtype_combo = QComboBox()
        for value, label in DTYPE_OPTIONS:
            self.dtype_combo.addItem(label, value)
        self.dtype_combo.setCurrentIndex(0)
        dtype_layout.addWidget(self.dtype_combo, stretch=1)
        dtype_tip = RichTooltipHelper(get_param_tooltip('dtype'))
        dtype_layout.addWidget(dtype_tip)
        basic_layout.addRow("变量类型:", dtype_layout)
        
        # cat_cutoff 输入框（分类型特有，默认隐藏）
        cat_cutoff_layout = QHBoxLayout()
        cat_cutoff_layout.setSpacing(8)
        self.cat_cutoff_spin = QDoubleSpinBox()
        self.cat_cutoff_spin.setRange(0, 1)
        self.cat_cutoff_spin.setDecimals(3)
        self.cat_cutoff_spin.setSingleStep(0.01)
        self.cat_cutoff_spin.setValue(0.05)  # 默认 5%
        self.cat_cutoff_spin.setSuffix(" (低频合并阈值)")
        self.cat_cutoff_spin.setFixedWidth(150)
        cat_cutoff_layout.addWidget(self.cat_cutoff_spin)
        cat_cutoff_layout.addStretch()
        cat_cutoff_tip = RichTooltipHelper(get_param_tooltip('cat_cutoff'))
        cat_cutoff_layout.addWidget(cat_cutoff_tip)
        self._cat_cutoff_label = QLabel("类别阈值:")
        basic_layout.addRow(self._cat_cutoff_label, cat_cutoff_layout)
        self.cat_cutoff_spin.setVisible(False)
        self._cat_cutoff_label.setVisible(False)
        
        # 求解器（带富文本提示）
        solver_layout = QHBoxLayout()
        solver_layout.setSpacing(8)
        self.solver_combo = QComboBox()
        for value, label in SOLVER_OPTIONS:
            self.solver_combo.addItem(label, value)
        self.solver_combo.setCurrentIndex(0)
        solver_layout.addWidget(self.solver_combo, stretch=1)
        solver_tip = RichTooltipHelper(get_param_tooltip('solver'))
        solver_layout.addWidget(solver_tip)
        basic_layout.addRow("求解器:", solver_layout)
        
        # 优化目标（带富文本提示）
        divergence_layout = QHBoxLayout()
        divergence_layout.setSpacing(8)
        self.divergence_combo = QComboBox()
        for value, label in DIVERGENCE_OPTIONS:
            self.divergence_combo.addItem(label, value)
        self.divergence_combo.setCurrentIndex(0)
        divergence_layout.addWidget(self.divergence_combo, stretch=1)
        divergence_tip = RichTooltipHelper(get_param_tooltip('divergence'))
        divergence_layout.addWidget(divergence_tip)
        basic_layout.addRow("优化目标:", divergence_layout)
        
        # 单调性趋势（带富文本提示）
        monotonic_layout = QHBoxLayout()
        monotonic_layout.setSpacing(8)
        self.monotonic_combo = QComboBox()
        for value, label in MONOTONIC_TREND_OPTIONS:
            self.monotonic_combo.addItem(label, value)
        self.monotonic_combo.setCurrentIndex(0)
        monotonic_layout.addWidget(self.monotonic_combo, stretch=1)
        monotonic_tip = RichTooltipHelper(get_param_tooltip('monotonic_trend'))
        monotonic_layout.addWidget(monotonic_tip)
        basic_layout.addRow("单调性:", monotonic_layout)
        
        # 箱数范围
        bins_layout = QHBoxLayout()
        bins_layout.setSpacing(8)
        self.min_bins_spin = QSpinBox()
        self.min_bins_spin.setRange(2, 50)
        self.min_bins_spin.setValue(2)
        self.min_bins_spin.setFixedWidth(80)
        self.max_bins_spin = QSpinBox()
        self.max_bins_spin.setRange(2, 100)
        self.max_bins_spin.setValue(10)
        self.max_bins_spin.setFixedWidth(80)
        bins_layout.addWidget(QLabel("最小:"))
        bins_layout.addWidget(self.min_bins_spin)
        bins_layout.addSpacing(16)
        bins_layout.addWidget(QLabel("最大:"))
        bins_layout.addWidget(self.max_bins_spin)
        bins_layout.addStretch()
        max_bins_tip = RichTooltipHelper(get_param_tooltip('max_n_bins'))
        bins_layout.addWidget(max_bins_tip)
        basic_layout.addRow("箱数范围:", bins_layout)
        
        # 求解时间限制
        time_layout = QHBoxLayout()
        time_layout.setSpacing(8)
        self.time_limit_spin = QSpinBox()
        self.time_limit_spin.setRange(1, 3600)
        self.time_limit_spin.setValue(100)
        self.time_limit_spin.setSuffix(" 秒")
        self.time_limit_spin.setFixedWidth(100)
        time_layout.addWidget(self.time_limit_spin)
        time_layout.addStretch()
        basic_layout.addRow("求解限制:", time_layout)
        
        return basic_group
        
    def _create_special_codes_group(self) -> QGroupBox:
        """创建特殊值处理组"""
        special_group = QGroupBox("特殊值处理")
        special_layout = QVBoxLayout(special_group)
        special_layout.setContentsMargins(16, 20, 16, 16)
        special_layout.setSpacing(12)
        
        # 特殊值说明 + 提示
        desc_layout = QHBoxLayout()
        special_desc = QLabel("需要单独处理的标记值，多个值用逗号分隔")
        special_desc.setStyleSheet("color: #666; font-size: 11px;")
        desc_layout.addWidget(special_desc)
        desc_layout.addStretch()
        special_tip = RichTooltipHelper(get_param_tooltip('special_codes'))
        desc_layout.addWidget(special_tip)
        special_layout.addLayout(desc_layout)
        
        # 特殊值输入框
        self.special_codes_edit = QLineEdit()
        self.special_codes_edit.setPlaceholderText("例如: -999, 999, -1")
        special_layout.addWidget(self.special_codes_edit)
        
        return special_group
        
    def _setup_styles(self):
        """设置样式"""
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
    def _connect_signals(self):
        """连接信号"""
        self.recommend_btn.clicked.connect(self._on_recommend_clicked)
        
        # 参数变化时发出信号
        self.dtype_combo.currentIndexChanged.connect(self._on_dtype_changed)
        self.dtype_combo.currentIndexChanged.connect(lambda: self.params_changed.emit())
        self.cat_cutoff_spin.valueChanged.connect(lambda: self.params_changed.emit())
        self.solver_combo.currentIndexChanged.connect(lambda: self.params_changed.emit())
        self.divergence_combo.currentIndexChanged.connect(lambda: self.params_changed.emit())
        self.monotonic_combo.currentIndexChanged.connect(lambda: self.params_changed.emit())
        self.min_bins_spin.valueChanged.connect(lambda: self.params_changed.emit())
        self.max_bins_spin.valueChanged.connect(lambda: self.params_changed.emit())
        self.time_limit_spin.valueChanged.connect(lambda: self.params_changed.emit())
        self.special_codes_edit.textChanged.connect(lambda: self.params_changed.emit())
        self.advanced_panel.params_changed.connect(self.params_changed.emit)
        
    def _on_dtype_changed(self):
        """处理变量类型变化"""
        dtype = self.dtype_combo.currentData()
        is_categorical = (dtype == 'categorical')
        
        # 显示/隐藏 cat_cutoff 相关控件
        self.cat_cutoff_spin.setVisible(is_categorical)
        if hasattr(self, '_cat_cutoff_label'):
            self._cat_cutoff_label.setVisible(is_categorical)
        
    def _on_recommend_clicked(self):
        """处理恢复推荐按钮点击"""
        # 使用默认样本数，实际使用时应该从外部传入
        n_samples = getattr(self, 'n_samples', 10000)
        self.apply_recommended_params(n_samples)
        
    def get_config(self) -> Dict[str, Any]:
        """获取完整配置（基础 + 高级）
        
        Returns:
            包含所有配置项的字典，键包括:
            - solver: 求解器类型
            - divergence: 优化目标
            - monotonic_trend: 单调性趋势
            - min_n_bins: 最小箱数
            - max_n_bins: 最大箱数
            - time_limit: 求解时间限制（秒）
            - special_codes: 特殊值列表（解析后的列表）
            - 高级参数: max_n_prebins, min_prebin_size, min_bin_size等
        """
        # 解析特殊值
        special_codes_str = self.special_codes_edit.text().strip()
        special_codes = []
        if special_codes_str:
            for code in special_codes_str.split(','):
                code = code.strip()
                if code:
                    try:
                        if '.' in code:
                            special_codes.append(float(code))
                        else:
                            special_codes.append(int(code))
                    except ValueError:
                        special_codes.append(code)
        
        # 基础配置
        config = {
            'solver': self.solver_combo.currentData(),
            'divergence': self.divergence_combo.currentData(),
            'monotonic_trend': self.monotonic_combo.currentData(),
            'min_n_bins': self.min_bins_spin.value(),
            'max_n_bins': self.max_bins_spin.value(),
            'time_limit': self.time_limit_spin.value(),
            'special_codes': special_codes if special_codes else None,
            'dtype': self.dtype_combo.currentData(),
        }
        
        # 分类型特有参数
        if config['dtype'] == 'categorical':
            config['cat_cutoff'] = self.cat_cutoff_spin.value()
        
        # 合并高级参数
        advanced_params = self.advanced_panel.get_params()
        config.update(advanced_params)
        
        return config
        
    def set_config(self, config: Dict[str, Any]):
        """设置完整配置
        
        Args:
            config: 配置字典，可包含以下键:
                - solver: 求解器类型
                - divergence: 优化目标
                - monotonic_trend: 单调性趋势
                - min_n_bins: 最小箱数
                - max_n_bins: 最大箱数
                - time_limit: 求解时间限制
                - special_codes: 特殊值（字符串或列表）
                - 高级参数: max_n_prebins, min_prebin_size等
        """
        # 设置基础参数
        if 'dtype' in config:
            idx = self.dtype_combo.findData(config['dtype'])
            if idx >= 0:
                self.dtype_combo.setCurrentIndex(idx)
        
        if 'cat_cutoff' in config:
            self.cat_cutoff_spin.setValue(config['cat_cutoff'])
                
        if 'solver' in config:
            idx = self.solver_combo.findData(config['solver'])
            if idx >= 0:
                self.solver_combo.setCurrentIndex(idx)
                
        if 'divergence' in config:
            idx = self.divergence_combo.findData(config['divergence'])
            if idx >= 0:
                self.divergence_combo.setCurrentIndex(idx)
                
        if 'monotonic_trend' in config:
            idx = self.monotonic_combo.findData(config['monotonic_trend'])
            if idx >= 0:
                self.monotonic_combo.setCurrentIndex(idx)
                
        if 'min_n_bins' in config:
            self.min_bins_spin.setValue(config['min_n_bins'])
            
        if 'max_n_bins' in config:
            self.max_bins_spin.setValue(config['max_n_bins'])
            
        if 'time_limit' in config:
            self.time_limit_spin.setValue(config['time_limit'])
            
        if 'special_codes' in config:
            codes = config['special_codes']
            if codes is None:
                self.special_codes_edit.setText('')
            elif isinstance(codes, list):
                self.special_codes_edit.setText(', '.join(str(c) for c in codes))
            else:
                self.special_codes_edit.setText(str(codes))
        
        # 设置高级参数
        advanced_params = {k: config.get(k) for k in ADVANCED_PARAM_KEYS if k in config}
        if advanced_params:
            self.advanced_panel.set_params(advanced_params)
        
        # 更新 dtype 相关控件的可见性
        self._on_dtype_changed()
            
    def set_n_samples(self, n: int):
        """设置样本数
        
        Args:
            n: 样本数量
        """
        self.n_samples = n
        
    def apply_recommended_params(self, n_samples: int = None):
        """应用推荐参数（包含高级参数）
        
        Args:
            n_samples: 样本数量，如果为None则使用已设置的n_samples
        """
        if n_samples is not None:
            self.n_samples = n_samples
        else:
            n_samples = getattr(self, 'n_samples', 10000)
            
        params = get_recommended_params(n_samples)
        
        # 显示确认对话框
        dialog = RecommendConfirmDialog(n_samples, params, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 应用推荐参数
            self.set_config(params)
            
            # 展开高级面板显示推荐值
            self.advanced_panel.set_expanded(True)
            
    def set_solving_status(self, is_solving: bool):
        """设置求解状态
        
        Args:
            is_solving: 是否正在求解中
        """
        if is_solving:
            self.status_widget.set_status(SolveStatusWidget.SOLVING)
            self.status_widget.clear()
        else:
            # 保持当前状态或设为未知
            pass
            
    def set_solve_result(self, status: str, info: Dict[str, Any] = None):
        """设置求解结果
        
        Args:
            status: 状态常量 (optimal, feasible, infeasible, timeout)
            info: 求解信息字典，可包含:
                - solve_time: 求解时间(秒)
                - objective_value: 目标函数值
                - n_iterations: 迭代次数
                - n_constraints_violated: 约束违反数
        """
        self.status_widget.set_status(status)
        if info:
            self.status_widget.set_info(info)
            
    def get_dtype(self) -> str:
        """获取当前选择的变量类型
        
        Returns:
            'auto', 'numerical', 或 'categorical'
        """
        return self.dtype_combo.currentData()
    
    def reset_to_defaults(self):
        """重置为默认值"""
        self.set_config(DEFAULT_CONFIG)
        self.advanced_panel.reset_to_defaults()
        self.status_widget.clear()


# 保持向后兼容
OptbinningConfigPanelWidget = OptbinningConfigPanel


if __name__ == '__main__':
    # 测试代码
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 创建主窗口
    window = QWidget()
    window.setWindowTitle("OptbinningConfigPanel Test")
    window.resize(500, 700)
    
    layout = QVBoxLayout(window)
    
    # 添加配置面板
    panel = OptbinningConfigPanel()
    panel.set_n_samples(50000)
    layout.addWidget(panel)
    
    # 添加测试按钮
    test_layout = QHBoxLayout()
    
    get_config_btn = QPushButton("获取配置")
    get_config_btn.clicked.connect(lambda: print(panel.get_config()))
    test_layout.addWidget(get_config_btn)
    
    set_solving_btn = QPushButton("模拟求解中")
    set_solving_btn.clicked.connect(lambda: panel.set_solving_status(True))
    test_layout.addWidget(set_solving_btn)
    
    set_optimal_btn = QPushButton("模拟最优解")
    set_optimal_btn.clicked.connect(lambda: panel.set_solve_result(
        SolveStatusWidget.OPTIMAL,
        {'solve_time': 5.23, 'objective_value': 0.456, 'n_iterations': 42}
    ))
    test_layout.addWidget(set_optimal_btn)
    
    set_timeout_btn = QPushButton("模拟超时")
    set_timeout_btn.clicked.connect(lambda: panel.set_solve_result(
        SolveStatusWidget.TIMEOUT,
        {'solve_time': 100.0, 'n_iterations': 128}
    ))
    test_layout.addWidget(set_timeout_btn)
    
    reset_btn = QPushButton("重置")
    reset_btn.clicked.connect(panel.reset_to_defaults)
    test_layout.addWidget(reset_btn)
    
    layout.addLayout(test_layout)
    layout.addStretch()
    
    window.show()
    sys.exit(app.exec())
