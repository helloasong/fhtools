"""Optbinning 配置面板 - 紧凑版

优化布局，适应较小空间
"""
import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QPushButton,
    QFormLayout, QGroupBox, QMessageBox, QGridLayout,
    QDialog, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, Any, Optional

from src.utils.recommend_params import get_recommended_params, get_data_scale_label
from src.ui.widgets.advanced_params_panel_compact import AdvancedParamsPanel
from src.ui.widgets.rich_tooltip_label import RichTooltipHelper, get_param_tooltip
from src.ui.widgets.solve_status_widget import SolveStatusWidget


# 选项定义
# 注意：LS 求解器在 optbinning 0.21.0 中有 bug，暂时移除
SOLVER_OPTIONS = [
    ('cp', 'CP'),
    ('mip', 'MIP'),
    # ('ls', 'LS'),  # 0.21.0 版本有内部错误
]

DIVERGENCE_OPTIONS = [
    ('iv', 'IV'),
    ('js', 'JS'),
    ('hellinger', 'Hellinger'),
    ('triangular', 'Triangular'),
]

MONOTONIC_TREND_OPTIONS = [
    ('auto', '自动'),
    ('ascending', '递增'),
    ('descending', '递减'),
    ('peak', '单峰'),
    ('valley', '单谷'),
]

DTYPE_OPTIONS = [
    ('auto', '自动'),
    ('numerical', '数值'),
    ('categorical', '分类'),
]


class OptbinningConfigPanel(QWidget):
    """Optbinning 配置面板 - 紧凑版"""
    
    params_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.n_samples = 0
        self._init_ui()
        self._connect_signals()
        
    def _init_ui(self):
        """初始化界面 - 紧凑布局"""
        # 不设置最大高度，允许根据内容自适应
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)
        
        # === 第一行：变量类型 + 求解器 + 优化目标 ===
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        
        # 变量类型
        row1.addWidget(QLabel("类型:"))
        self.dtype_combo = QComboBox()
        for value, label in DTYPE_OPTIONS:
            self.dtype_combo.addItem(label, value)
        self.dtype_combo.setCurrentIndex(0)
        self.dtype_combo.setMinimumWidth(60)
        row1.addWidget(self.dtype_combo)
        
        # cat_cutoff (初始隐藏)
        self.cat_cutoff_spin = QDoubleSpinBox()
        self.cat_cutoff_spin.setRange(0, 1)
        self.cat_cutoff_spin.setDecimals(2)
        self.cat_cutoff_spin.setValue(0.05)
        self.cat_cutoff_spin.setSuffix("阈值")
        self.cat_cutoff_spin.setMinimumWidth(80)
        self.cat_cutoff_spin.setVisible(False)
        row1.addWidget(self.cat_cutoff_spin)
        
        row1.addSpacing(16)
        
        # 求解器
        row1.addWidget(QLabel("求解器:"))
        self.solver_combo = QComboBox()
        for value, label in SOLVER_OPTIONS:
            self.solver_combo.addItem(label, value)
        self.solver_combo.setCurrentIndex(0)
        self.solver_combo.setMinimumWidth(60)
        row1.addWidget(self.solver_combo)
        
        row1.addSpacing(16)
        
        # 优化目标
        row1.addWidget(QLabel("目标:"))
        self.divergence_combo = QComboBox()
        for value, label in DIVERGENCE_OPTIONS:
            self.divergence_combo.addItem(label, value)
        self.divergence_combo.setCurrentIndex(0)
        self.divergence_combo.setMinimumWidth(80)
        row1.addWidget(self.divergence_combo)
        
        row1.addStretch()
        main_layout.addLayout(row1)
        
        # === 第二行：单调性 + 箱数范围 + 时间限制 ===
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        
        # 单调性
        row2.addWidget(QLabel("单调性:"))
        self.monotonic_combo = QComboBox()
        for value, label in MONOTONIC_TREND_OPTIONS:
            self.monotonic_combo.addItem(label, value)
        self.monotonic_combo.setCurrentIndex(0)
        self.monotonic_combo.setMinimumWidth(70)
        row2.addWidget(self.monotonic_combo)
        
        row2.addSpacing(16)
        
        # 箱数范围
        row2.addWidget(QLabel("箱数:"))
        self.min_bins_spin = QSpinBox()
        self.min_bins_spin.setRange(2, 50)
        self.min_bins_spin.setValue(2)
        self.min_bins_spin.setFixedWidth(50)
        row2.addWidget(self.min_bins_spin)
        row2.addWidget(QLabel("-"))
        self.max_bins_spin = QSpinBox()
        self.max_bins_spin.setRange(2, 100)
        self.max_bins_spin.setValue(10)
        self.max_bins_spin.setFixedWidth(50)
        row2.addWidget(self.max_bins_spin)
        
        row2.addSpacing(16)
        
        # 时间限制
        row2.addWidget(QLabel("限时:"))
        self.time_limit_spin = QSpinBox()
        self.time_limit_spin.setRange(10, 600)
        self.time_limit_spin.setValue(100)
        self.time_limit_spin.setSuffix("s")
        self.time_limit_spin.setFixedWidth(70)
        row2.addWidget(self.time_limit_spin)
        
        row2.addStretch()
        main_layout.addLayout(row2)
        
        # === 第三行：特殊值 ===
        row3 = QHBoxLayout()
        row3.setSpacing(8)
        row3.addWidget(QLabel("特殊值:"))
        self.special_codes_input = QLineEdit()
        self.special_codes_input.setPlaceholderText("如: -999, 999 (逗号分隔)")
        row3.addWidget(self.special_codes_input)
        row3.addStretch()
        main_layout.addLayout(row3)
        
        # === 高级选项 ===
        self.advanced_panel = AdvancedParamsPanel()
        main_layout.addWidget(self.advanced_panel)
        
        # === 求解状态 (根据状态自动显示/隐藏) ===
        self.status_widget = SolveStatusWidget(detailed=False)  # 简洁模式
        self.status_widget.setMaximumHeight(40)
        # 注意：SolveStatusWidget 会根据状态自动显示/隐藏
        # UNKNOWN 状态时隐藏，其他状态（求解中、最优解等）时显示
        main_layout.addWidget(self.status_widget)
        
        # === 按钮 ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.recommend_btn = QPushButton("⚡ 恢复推荐")
        self.recommend_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        btn_layout.addWidget(self.recommend_btn)
        main_layout.addLayout(btn_layout)
        
        # 初始状态
        self._on_dtype_changed(0)
        
    def _connect_signals(self):
        """连接信号"""
        self.dtype_combo.currentIndexChanged.connect(self._on_dtype_changed)
        self.recommend_btn.clicked.connect(self._on_recommend_clicked)
        
        # 参数变化信号
        for combo in [self.dtype_combo, self.solver_combo, self.divergence_combo, 
                      self.monotonic_combo]:
            combo.currentIndexChanged.connect(self.params_changed.emit)
        for spin in [self.min_bins_spin, self.max_bins_spin, self.time_limit_spin,
                     self.cat_cutoff_spin]:
            spin.valueChanged.connect(self.params_changed.emit)
        self.special_codes_input.textChanged.connect(self.params_changed.emit)
        
    def _on_dtype_changed(self, index):
        """变量类型变化处理"""
        dtype = self.dtype_combo.currentData()
        is_categorical = (dtype == 'categorical')
        self.cat_cutoff_spin.setVisible(is_categorical)
        
    def validate_dtype_for_data(self, x: pd.Series) -> tuple[bool, str]:
        """验证类型选择是否适合数据
        
        Args:
            x: 特征数据
            
        Returns:
            (是否有效, 警告信息)
        """
        dtype = self.dtype_combo.currentData()
        n_unique = x.nunique()
        n_samples = len(x)
        
        if dtype == 'categorical':
            # 检查是否是数值型数据误用分类类型
            if pd.api.types.is_numeric_dtype(x) and n_unique > 100:
                avg_pct = 1.0 / n_unique
                cat_cutoff = self.cat_cutoff_spin.value()
                if avg_pct < cat_cutoff:
                    return False, (
                        f"该变量是数值型（{n_unique}个唯一值），"
                        f"但选择了'分类'类型且cat_cutoff={cat_cutoff}。\n"
                        f"这会导致所有类别被合并到'others'。\n\n"
                        f"建议：将类型改为'数值'或'自动'。"
                    )
        elif dtype == 'numerical':
            # 检查是否是分类型数据误用数值类型
            if not pd.api.types.is_numeric_dtype(x) and n_unique <= 20:
                return False, (
                    f"该变量是分类型（{n_unique}个类别），"
                    f"但选择了'数值'类型。\n\n"
                    f"建议：将类型改为'分类'或'自动'。"
                )
        
        return True, ""
        
    def _on_recommend_clicked(self):
        """恢复推荐参数"""
        if self.n_samples <= 0:
            QMessageBox.warning(self, "提示", "请先导入数据")
            return
            
        params = get_recommended_params(self.n_samples)
        
        # 确认对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("应用推荐参数")
        dialog.setMinimumWidth(350)
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel(f"数据规模: {get_data_scale_label(self.n_samples)}"))
        layout.addWidget(QLabel(f"将应用以下推荐值:"))
        
        info = QLabel(f"""
        <table>
        <tr><td>求解器:</td><td><b>{params['solver'].upper()}</b></td></tr>
        <tr><td>预分箱数:</td><td>{params['max_n_prebins']}</td></tr>
        <tr><td>最小箱大小:</td><td>{params['min_bin_size']:.0%}</td></tr>
        <tr><td>时间限制:</td><td>{params['time_limit']}秒</td></tr>
        </table>
        """)
        info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        apply_btn = QPushButton("应用")
        apply_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        apply_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(apply_btn)
        layout.addLayout(btn_layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.set_config(params)
            self.advanced_panel.set_expanded(True)
            
    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        config = {
            'dtype': self.dtype_combo.currentData(),
            'solver': self.solver_combo.currentData(),
            'divergence': self.divergence_combo.currentData(),
            'monotonic_trend': self.monotonic_combo.currentData(),
            'min_n_bins': self.min_bins_spin.value(),
            'max_n_bins': self.max_bins_spin.value(),
            'time_limit': self.time_limit_spin.value(),
            'special_codes': self.special_codes_input.text() or None,
        }
        
        if config['dtype'] == 'categorical':
            config['cat_cutoff'] = self.cat_cutoff_spin.value()
            
        advanced = self.advanced_panel.get_params()
        config.update(advanced)
        
        return config
        
    def set_config(self, config: Dict[str, Any]):
        """设置配置"""
        if 'dtype' in config:
            idx = self.dtype_combo.findData(config['dtype'])
            if idx >= 0:
                self.dtype_combo.setCurrentIndex(idx)
                
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
        if 'cat_cutoff' in config:
            self.cat_cutoff_spin.setValue(config['cat_cutoff'])
        if 'special_codes' in config:
            self.special_codes_input.setText(config['special_codes'] or '')
            
        # 高级参数
        advanced_keys = ['max_n_prebins', 'min_prebin_size', 'min_bin_size',
                        'max_bin_size', 'min_bin_n_event', 'min_bin_n_nonevent',
                        'max_pvalue', 'gamma']
        advanced_params = {k: config.get(k) for k in advanced_keys if k in config}
        self.advanced_panel.set_params(advanced_params)
        
    def set_n_samples(self, n: int):
        """设置样本数"""
        self.n_samples = n
        
    def set_solving_status(self, is_solving: bool):
        """设置求解状态"""
        if is_solving:
            self.status_widget.set_status(SolveStatusWidget.SOLVING)
        else:
            self.status_widget.set_status(SolveStatusWidget.UNKNOWN)
            
    def set_solve_result(self, status: str, info: Dict[str, Any] = None):
        """设置求解结果"""
        self.status_widget.set_status(status)
        if info:
            self.status_widget.set_info(info)
            
    def reset_to_defaults(self):
        """重置默认值"""
        self.set_config({
            'dtype': 'auto',
            'solver': 'cp',
            'divergence': 'iv',
            'monotonic_trend': 'auto',
            'min_n_bins': 2,
            'max_n_bins': 10,
            'time_limit': 100,
            'special_codes': '',
        })
        self.advanced_panel.reset_to_defaults()
