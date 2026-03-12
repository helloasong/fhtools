"""智能单调分箱配置面板

提供智能分箱算法的专属参数配置，包含基础参数和高级选项。
每个参数都配有详细说明，帮助用户理解算法原理。
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QSpinBox, QGroupBox, QToolButton, QSizePolicy
)
from PyQt6.QtCore import Qt


class SmartMonotonicConfigPanel(QWidget):
    """智能单调分箱配置面板
    
    算法核心：预分箱(50箱) → 最优合并 → 保证单调性
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        """构建UI - 紧凑布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # ========== 第一行：通用配置 ==========
        common_layout = QHBoxLayout()
        common_layout.setSpacing(8)
        
        # 预分箱数（紧凑）
        self.prebins_spin = QSpinBox()
        self.prebins_spin.setRange(20, 100)
        self.prebins_spin.setValue(50)
        self.prebins_spin.setSingleStep(5)
        self.prebins_spin.setFixedWidth(55)
        self.prebins_spin.setToolTip("初始等频分箱的箱数，作为后续合并的基础\n"
                                    "• 值越大：找到最优单调解的可能性越高，但计算时间增加\n"
                                    "• 推荐值：50（在质量和速度间取得平衡）")
        common_layout.addWidget(self._create_label("预分箱:"))
        common_layout.addWidget(self.prebins_spin)
        
        # 最小样本数
        self.min_samples_spin = QSpinBox()
        self.min_samples_spin.setRange(10, 1000)
        self.min_samples_spin.setValue(50)
        self.min_samples_spin.setSingleStep(10)
        self.min_samples_spin.setFixedWidth(55)
        self.min_samples_spin.setToolTip("每箱最小样本数，防止过拟合\n"
                                        "• 过小：可能导致过拟合，泛化能力差\n"
                                        "• 过大：可能无法达到目标箱数\n"
                                        "• 建议：总样本量的 1%-5%")
        common_layout.addWidget(self._create_label("最小样本:"))
        common_layout.addWidget(self.min_samples_spin)
        
        # 单调趋势
        self.trend_combo = QComboBox()
        self.trend_combo.addItem("📊 自动", "auto")
        self.trend_combo.addItem("↗️ 递增", "ascending")
        self.trend_combo.addItem("↘️ 递减", "descending")
        self.trend_combo.setFixedWidth(90)
        self.trend_combo.setToolTip("bad_rate 随分数的变化趋势\n"
                                   "• 自动：根据数据相关性自动判断\n"
                                   "• 递增：分数越高，bad_rate越高\n"
                                   "• 递减：分数越高，bad_rate越低")
        common_layout.addWidget(self._create_label("单调趋势:"))
        common_layout.addWidget(self.trend_combo)
        
        common_layout.addStretch()
        layout.addLayout(common_layout)
        
        # ========== 高级选项（可折叠） ==========
        self.advanced_toggle = QToolButton()
        self.advanced_toggle.setText("▼ 高级选项")
        self.advanced_toggle.setStyleSheet("""
            QToolButton {
                border: none;
                color: #666;
                font-size: 12px;
                padding: 2px 4px;
            }
            QToolButton:hover {
                color: #333;
                background: #f0f0f0;
                border-radius: 3px;
            }
        """)
        self.advanced_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.advanced_toggle.clicked.connect(self._toggle_advanced)
        layout.addWidget(self.advanced_toggle, alignment=Qt.AlignmentFlag.AlignLeft)
        
        # 高级选项面板 - 水平紧凑布局
        self.advanced_panel = QWidget()
        advanced_layout = QHBoxLayout(self.advanced_panel)
        advanced_layout.setContentsMargins(0, 4, 0, 0)
        advanced_layout.setSpacing(8)
        
        # 单调容忍度
        self.tolerance_combo = QComboBox()
        self.tolerance_combo.addItem("严格", 1e-9)
        self.tolerance_combo.addItem("标准★", 1e-6)
        self.tolerance_combo.addItem("宽松", 1e-3)
        self.tolerance_combo.setCurrentIndex(1)
        self.tolerance_combo.setFixedWidth(75)
        self.tolerance_combo.setToolTip("判定单调性的数值容差\n"
                                       "• 严格：要求bad_rate严格单调\n"
                                       "• 标准：允许微小浮点误差，推荐\n"
                                       "• 宽松：允许小幅度波动")
        advanced_layout.addWidget(self._create_label("容忍度:"))
        advanced_layout.addWidget(self.tolerance_combo)
        
        # 合并策略
        self.merge_strategy_combo = QComboBox()
        self.merge_strategy_combo.addItem("平衡★", "balanced")
        self.merge_strategy_combo.addItem("单调优先", "monotonic_first")
        self.merge_strategy_combo.addItem("IV优先", "iv_first")
        self.merge_strategy_combo.setFixedWidth(90)
        self.merge_strategy_combo.setToolTip("合并时的优先级策略\n"
                                            "• 平衡：同时考虑单调性和IV损失\n"
                                            "• 单调优先：先解决所有单调违反\n"
                                            "• IV优先：允许轻微非单调获更高IV")
        advanced_layout.addWidget(self._create_label("合并策略:"))
        advanced_layout.addWidget(self.merge_strategy_combo)
        
        # 保底策略
        self.fallback_combo = QComboBox()
        self.fallback_combo.addItem("简单★", "simple")
        self.fallback_combo.addItem("等频", "equal_freq")
        self.fallback_combo.addItem("决策树", "decision_tree")
        self.fallback_combo.setFixedWidth(80)
        self.fallback_combo.setToolTip("智能合并失败时的降级方案\n"
                                      "• 简单切分：按样本等分\n"
                                      "• 等频分箱：强制等频\n"
                                      "• 决策树：使用决策树切分")
        advanced_layout.addWidget(self._create_label("保底策略:"))
        advanced_layout.addWidget(self.fallback_combo)
        
        # 最大迭代
        self.max_iter_spin = QSpinBox()
        self.max_iter_spin.setRange(0, 5000)
        self.max_iter_spin.setValue(0)
        self.max_iter_spin.setSpecialValueText("自动")
        self.max_iter_spin.setFixedWidth(60)
        self.max_iter_spin.setToolTip("合并迭代次数上限\n"
                                     "• 自动：根据数据自动计算\n"
                                     "• 手动：限制最大迭代次数")
        advanced_layout.addWidget(self._create_label("最大迭代:"))
        advanced_layout.addWidget(self.max_iter_spin)
        
        advanced_layout.addStretch()
        layout.addWidget(self.advanced_panel)
        layout.addStretch()
        
    def _create_label(self, text: str) -> QLabel:
        """创建紧凑型标签"""
        label = QLabel(text)
        label.setStyleSheet("color: #555; font-size: 12px;")
        return label
        
    def _toggle_advanced(self):
        """切换高级选项显示/隐藏"""
        is_visible = self.advanced_panel.isVisible()
        self.advanced_panel.setVisible(not is_visible)
        self.advanced_toggle.setText("▼ 高级选项" if not is_visible else "▶ 高级选项")
        
    def get_config(self) -> dict:
        """获取配置参数"""
        return {
            'prebins': self.prebins_spin.value(),
            'min_samples_per_bin': self.min_samples_spin.value(),
            'monotonic_trend': self.trend_combo.currentData(),
            'tolerance': self.tolerance_combo.currentData(),
            'merge_strategy': self.merge_strategy_combo.currentData(),
            'fallback': self.fallback_combo.currentData(),
            'max_iterations': self.max_iter_spin.value() if self.max_iter_spin.value() > 0 else None,
        }
        
    def set_config(self, config: dict):
        """设置配置参数"""
        if 'prebins' in config:
            self.prebins_spin.setValue(config['prebins'])
        if 'min_samples_per_bin' in config:
            self.min_samples_spin.setValue(config['min_samples_per_bin'])
        if 'monotonic_trend' in config:
            idx = self.trend_combo.findData(config['monotonic_trend'])
            if idx >= 0:
                self.trend_combo.setCurrentIndex(idx)
        if 'tolerance' in config:
            idx = self.tolerance_combo.findData(config['tolerance'])
            if idx >= 0:
                self.tolerance_combo.setCurrentIndex(idx)
        if 'merge_strategy' in config:
            idx = self.merge_strategy_combo.findData(config['merge_strategy'])
            if idx >= 0:
                self.merge_strategy_combo.setCurrentIndex(idx)
        if 'fallback' in config:
            idx = self.fallback_combo.findData(config['fallback'])
            if idx >= 0:
                self.fallback_combo.setCurrentIndex(idx)
        if 'max_iterations' in config and config['max_iterations']:
            self.max_iter_spin.setValue(config['max_iterations'])
