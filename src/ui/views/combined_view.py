from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLabel, QSplitter,
    QComboBox, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QAbstractScrollArea, QMessageBox,
    QStackedWidget, QProgressDialog, QDialog, QProgressBar, QTextEdit, QListWidgetItem as QListWidgetItemClass,
    QGroupBox, QGridLayout, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QGridLayout, QGraphicsDropShadowEffect
import pyqtgraph as pg
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional

from src.controllers.project_controller import ProjectController
from src.data.models import ProjectState, VariableStats, BinningMetrics, BinningConfig
from src.services.recommendation_service import recommend_method, method_to_cn
from src.utils.formatting import format_bin_label, parse_precision_step, resolve_precision_step
from src.ui.widgets.optbinning_config_panel_compact import OptbinningConfigPanel
from src.core.binning import OPTBINNING_AVAILABLE

# 单调性趋势图标映射
TREND_ICONS = {
    'auto': '📊',
    'auto_heuristic': '📊',
    'ascending': '↗️',
    'descending': '↘️',
    'concave': '⌣',
    'convex': '⌢',
    'peak': '⛰️',
    'valley': '🏞️',
    'peak_heuristic': '⛰️',
    'valley_heuristic': '🏞️',
    'auto_asc_desc': '📊',
}

TREND_LABELS = {
    'auto': '自动',
    'auto_asc_desc': '自动(增或减)',
    'ascending': '递增',
    'descending': '递减',
    'concave': '凹形',
    'convex': '凸形',
    'peak': '单峰',
    'valley': '单谷',
}


class BatchBinningDialog(QDialog):
    """批量分箱进度对话框"""
    
    cancelled = pyqtSignal()
    
    def __init__(self, parent=None, total_count: int = 0):
        super().__init__(parent)
        self.total_count = total_count
        self.cancelled_flag = False
        self.results = {}  # 存储每个变量的结果
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("批量分箱")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # 标题和进度
        self.title_label = QLabel(f"正在批量分箱 ({self.total_count} 个变量)")
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.title_label)
        
        # 总体进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(self.total_count)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% (%v/%m)")
        layout.addWidget(self.progress_bar)
        
        # 当前变量
        self.current_label = QLabel("准备开始...")
        self.current_label.setStyleSheet("color: #666;")
        layout.addWidget(self.current_label)
        
        # 变量状态列表
        self.status_group = QGroupBox("处理状态")
        status_layout = QVBoxLayout(self.status_group)
        
        self.status_list = QListWidget()
        self.status_list.setMaximumHeight(200)
        status_layout.addWidget(self.status_list)
        
        layout.addWidget(self.status_group)
        
        # 统计信息
        self.stats_label = QLabel("成功: 0 | 失败: 0 | 等待: 0")
        layout.addWidget(self.stats_label)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.on_cancel)
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # 初始化状态列表
        self._init_status_list()
    
    def _init_status_list(self):
        """初始化状态列表（将在设置变量名后调用）"""
        pass
    
    def set_variable_names(self, var_names: List[str]):
        """设置要处理的变量名列表"""
        self.var_names = var_names
        self.status_items = {}
        self.status_list.clear()
        
        for name in var_names:
            item = QListWidgetItemClass(f"⏳ {name} - 等待中...")
            self.status_list.addItem(item)
            self.status_items[name] = item
        
        self._update_stats()
    
    def update_progress(self, current: int, total: int, var_name: str):
        """更新进度"""
        self.progress_bar.setValue(current)
        self.current_label.setText(f"正在处理: {var_name}")
        
        # 更新当前变量状态为处理中
        if var_name in self.status_items:
            self.status_items[var_name].setText(f"🟡 {var_name} - 求解中...")
    
    def mark_success(self, var_name: str, iv_value: float = None):
        """标记变量处理成功"""
        if var_name in self.status_items:
            iv_str = f"IV: {iv_value:.4f}" if iv_value is not None else ""
            self.status_items[var_name].setText(f"🟢 {var_name} - 完成 {iv_str}")
            self.results[var_name] = {'success': True, 'iv': iv_value}
        self._update_stats()
    
    def mark_failed(self, var_name: str, error: str = ""):
        """标记变量处理失败"""
        if var_name in self.status_items:
            error_short = error[:30] + "..." if len(error) > 30 else error
            self.status_items[var_name].setText(f"🔴 {var_name} - 失败 ({error_short})")
            self.results[var_name] = {'success': False, 'error': error}
        self._update_stats()
    
    def _update_stats(self):
        """更新统计信息"""
        success = sum(1 for r in self.results.values() if r.get('success'))
        failed = sum(1 for r in self.results.values() if not r.get('success'))
        waiting = self.total_count - len(self.results)
        self.stats_label.setText(f"成功: {success} | 失败: {failed} | 等待: {waiting}")
    
    def on_cancel(self):
        """取消操作"""
        self.cancelled_flag = True
        self.cancelled.emit()
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("正在取消...")
    
    def is_cancelled(self) -> bool:
        """检查是否已取消"""
        return self.cancelled_flag
    
    def show_summary(self, success_list: List[str], failed_list: List[Tuple[str, str]]):
        """显示完成后的汇总信息"""
        self.title_label.setText("批量分箱完成")
        self.current_label.setText(f"完成: {len(success_list)} 成功, {len(failed_list)} 失败")
        self.cancel_btn.setText("关闭")
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.clicked.disconnect()
        self.cancel_btn.clicked.connect(self.accept)


class SingleBinningWorker(QThread):
    """单变量分箱工作线程"""
    
    finished = pyqtSignal(str, object, bool, str)  # 变量名, 指标, 是否成功, 错误信息
    
    def __init__(self, controller: ProjectController, feature: str, method: str, **kwargs):
        super().__init__()
        self.controller = controller
        self.feature = feature
        self.method = method
        self.kwargs = kwargs
    
    def run(self):
        """执行单变量分箱"""
        try:
            # 设置 emit_error=False 避免重复弹窗（错误会通过 finished 信号传递）
            self.controller.run_binning(self.feature, method=self.method, emit_error=False, **self.kwargs)
            metrics = self.controller.state.binning_results.get(self.feature)
            self.finished.emit(self.feature, metrics, True, "")
        except Exception as e:
            self.finished.emit(self.feature, None, False, str(e))


class BatchBinningWorker(QThread):
    """批量分箱工作线程"""
    
    progress = pyqtSignal(int, int, str)  # 当前进度, 总数, 当前变量
    item_finished = pyqtSignal(str, object, bool, str)  # 变量名, 指标, 是否成功, 错误信息
    finished_with_result = pyqtSignal(list, list)  # 成功列表, 失败列表
    
    def __init__(self, controller: ProjectController, features: List[str], method: str, **kwargs):
        super().__init__()
        self.controller = controller
        self.features = features
        self.method = method
        self.kwargs = kwargs
        self._cancelled = False
    
    def cancel(self):
        """标记取消"""
        self._cancelled = True
    
    def run(self):
        """执行批量分箱"""
        success_list = []
        failed_list = []
        
        for i, feature in enumerate(self.features):
            if self._cancelled:
                break
            
            self.progress.emit(i + 1, len(self.features), feature)
            
            try:
                # 设置 emit_error=False 避免重复弹窗（错误会通过 item_finished 信号传递）
                self.controller.run_binning(feature, method=self.method, emit_error=False, **self.kwargs)
                metrics = self.controller.state.binning_results.get(feature)
                success_list.append(feature)
                self.item_finished.emit(feature, metrics, True, "")
            except Exception as e:
                failed_list.append((feature, str(e)))
                self.item_finished.emit(feature, None, False, str(e))
        
        self.finished_with_result.emit(success_list, failed_list)


class CombinedView(QWidget):
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self.current_feature = None
        self.split_lines = []
        self._current_metrics_df = None
        self._current_centers = None
        self._current_bad_rates = None
        self._skip_autorange_once = False
        self.batch_dialog = None
        self.batch_worker = None
        self._binning_worker = None  # 单变量分箱工作线程
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：变量列表 + 搜索（简化为列表）
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        
        # 批量分箱按钮和选择计数
        self.batch_btn_layout = QHBoxLayout()
        self.batch_btn = QPushButton("批量分箱")
        self.batch_btn.setToolTip("Ctrl+点击 或 Shift+点击 选择多个变量")
        self.batch_btn.clicked.connect(self.on_batch_binning)
        self.batch_btn.setEnabled(False)  # 初始禁用，等有选择时启用
        
        self.selection_count_label = QLabel("已选择: 0")
        self.selection_count_label.setStyleSheet("color: #666; font-size: 12px;")
        
        self.batch_btn_layout.addWidget(self.batch_btn)
        self.batch_btn_layout.addWidget(self.selection_count_label)
        self.batch_btn_layout.addStretch()
        
        left_layout.addLayout(self.batch_btn_layout)
        
        # 变量列表 - 启用多选模式
        self.feature_list = QListWidget()
        self.feature_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.feature_list.itemClicked.connect(self.on_feature_selected)
        self.feature_list.itemSelectionChanged.connect(self._update_selection_count)
        
        left_layout.addWidget(self.feature_list)
        
        # 多选提示
        self.multi_select_hint = QLabel("💡 Ctrl+点击多选, Shift+范围选择")
        self.multi_select_hint.setStyleSheet("color: #888; font-size: 10px;")
        left_layout.addWidget(self.multi_select_hint)

        # 右侧：使用 QScrollArea 包装内容，支持滚动
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 设置滚动区域大小策略
        right_scroll.setSizePolicy(
            right_scroll.sizePolicy().horizontalPolicy(),
            right_scroll.sizePolicy().verticalPolicy()
        )
        
        # 右侧内容容器
        right_content = QWidget()
        right_layout = QVBoxLayout(right_content)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(6)

        # 顶部：基础统计（横向栅格卡片）
        self.stats_panel = QWidget()
        self.stats_panel.setProperty("card", True)
        self.stats_grid = QGridLayout(self.stats_panel)
        self.stats_grid.setContentsMargins(8, 8, 8, 8)
        self.stats_grid.setSpacing(8)
        self._apply_shadow(self.stats_panel)

        # 建议标签
        # 目标变量提示
        self.target_label = QLabel("")
        self.target_label.setProperty("card", True)
        self._apply_shadow(self.target_label)
        self.target_label.setStyleSheet("padding:6px; background:#E9F6EC; border:1px solid #CBE6D1; border-radius:8px; color:#2E7D32;")

        self.recommend_label = QLabel("")
        self.recommend_label.setStyleSheet("color:#888;font-size:12px;")

        # 中部：分布图（带双轴：左轴样本数，右轴坏样本率）
        self.dist_plot = pg.PlotWidget(title="分布图")
        self.dist_plot.setMinimumHeight(150)
        self.dist_plot.setMaximumHeight(250)
        self._compact_plot(self.dist_plot, height=180)
        self._setup_bottom_anchor(self.dist_plot)
        
        # 创建右侧Y轴用于显示坏样本率
        self.dist_plot_right_axis = pg.ViewBox()
        self.dist_plot.plotItem.scene().addItem(self.dist_plot_right_axis)
        self.dist_plot.plotItem.getAxis('right').linkToView(self.dist_plot_right_axis)
        self.dist_plot.plotItem.getAxis('right').setLabel('坏样本率', color='red')
        self.dist_plot.plotItem.getAxis('right').setPen('red')
        self.dist_plot.plotItem.showAxis('right')
        
        # 禁用右侧ViewBox的鼠标交互，让它完全跟随主ViewBox
        self.dist_plot_right_axis.setMouseEnabled(x=False, y=False)
        self.dist_plot_right_axis.enableAutoRange(axis='x', enable=False)
        self.dist_plot_right_axis.enableAutoRange(axis='y', enable=True)
        
        # 同步左右两个ViewBox的X轴范围
        def update_right_axis_range():
            xmin, xmax = self.dist_plot.plotItem.vb.viewRange()[0]
            self.dist_plot_right_axis.setXRange(xmin, xmax, padding=0)
        
        # 同步主ViewBox的几何变化到右侧ViewBox
        def update_right_axis_geometry():
            # 确保右侧ViewBox的几何位置与主ViewBox一致
            self.dist_plot_right_axis.setGeometry(self.dist_plot.plotItem.vb.sceneBoundingRect())
        
        # 同步Y轴自动缩放
        def update_right_y_range():
            # 当主ViewBox的Y轴变化时，保持右侧ViewBox的Y轴自动调整
            pass  # 右侧Y轴有自己的数据范围
        
        self.dist_plot.plotItem.vb.sigXRangeChanged.connect(update_right_axis_range)
        self.dist_plot.plotItem.vb.sigResized.connect(update_right_axis_geometry)
        
        self.dist_card = self._wrap_card(self.dist_plot)

        # 中部：分箱图
        self.bin_plot = pg.PlotWidget(title="分箱图")
        self.bin_plot.setMinimumHeight(150)
        self.bin_plot.setMaximumHeight(250)
        self._compact_plot(self.bin_plot, height=180)
        self._setup_bottom_anchor(self.bin_plot)
        self.bin_plot.scene().sigMouseMoved.connect(self.on_mouse_moved)
        self.bin_card = self._wrap_card(self.bin_plot)
        
        # 分箱图提示（双击分割线设置切点）
        self.bin_hint_label = QLabel("💡 提示：双击红色分割线可设置精确切点值")
        self.bin_hint_label.setStyleSheet("color:#666; font-size:11px; padding:2px 4px;")

        # 分箱明细表
        self.bin_table = QTableWidget()
        self.bin_table.setColumnCount(10)
        self.bin_table.setHorizontalHeaderLabels(["范围", "样本数", "占比", "坏样本数", "坏样本率", "好样本数", "好样本率", "WOE", "IV", "Lift"])
        # 禁用垂直滚动条，完整展示所有行
        self.bin_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.bin_table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.bin_table.setMinimumHeight(100)
        self.bin_table_card = self._wrap_card(self.bin_table)

        # 下部：分箱配置（紧凑工具栏）
        # 首先创建设置控件
        self.n_bins_spin = QSpinBox()
        self.n_bins_spin.setRange(2, 20)
        self.n_bins_spin.setValue(5)
        self.n_bins_spin.setPrefix("箱数：")
        
        self.missing_combo = QComboBox()
        for label, key in [("单独成箱", "separate"), ("忽略", "ignore"), ("归并", "merge")]:
            self.missing_combo.addItem(label, key)

        self.precision_mode_combo = QComboBox()
        for label, key in [("自动", "auto"), ("小数点后几位", "decimal"), ("整数位（前几位）", "integer")]:
            self.precision_mode_combo.addItem(label, key)
        
        self.precision_digits_spin = QSpinBox()
        self.precision_digits_spin.setRange(0, 12)
        self.precision_digits_spin.setValue(0)
        
        # 智能单调分箱专用配置
        self.smart_monotonic_trend_combo = QComboBox()
        for label, key in [("自动", "auto"), ("递增", "ascending"), ("递减", "descending")]:
            self.smart_monotonic_trend_combo.addItem(label, key)
        self.smart_monotonic_trend_combo.setVisible(False)  # 默认隐藏
        
        self.run_btn = QPushButton("运行")
        self.save_btn = QPushButton("确认并保存")
        
        # 配置面板区域（使用 QStackedWidget 切换）
        self.config_stack = QStackedWidget()
        
        # 传统配置面板（将原有控件移入）
        self.traditional_config = QWidget()
        self.traditional_config.setMaximumHeight(80)  # 限制最大高度
        trad_layout = QHBoxLayout(self.traditional_config)
        trad_layout.setContentsMargins(8, 8, 8, 8)
        trad_layout.setSpacing(12)
        
        # 将原有配置控件移到传统面板
        trad_layout.addWidget(QLabel("箱数："))
        trad_layout.addWidget(self.n_bins_spin)
        trad_layout.addWidget(QLabel("缺失值策略："))
        trad_layout.addWidget(self.missing_combo)
        trad_layout.addWidget(QLabel("边界精度："))
        trad_layout.addWidget(self.precision_mode_combo)
        trad_layout.addWidget(self.precision_digits_spin)
        # 智能单调分箱配置（动态显示/隐藏）
        self.smart_monotonic_trend_label = QLabel("单调趋势：")
        trad_layout.addWidget(self.smart_monotonic_trend_label)
        trad_layout.addWidget(self.smart_monotonic_trend_combo)
        self.smart_monotonic_trend_label.setVisible(False)
        trad_layout.addStretch()  # 添加弹性空间
        
        self.config_stack.addWidget(self.traditional_config)
        
        # Optbinning 配置面板（仅当 optbinning 可用时创建）
        self.optbinning_config = None
        if OPTBINNING_AVAILABLE:
            self.optbinning_config = OptbinningConfigPanel()
            self.optbinning_config.set_n_samples(self.controller.get_sample_count())
            self.config_stack.addWidget(self.optbinning_config)
            self.config_stack.setCurrentIndex(1)  # 显示 Optbinning
        else:
            self.config_stack.setCurrentIndex(0)  # 显示传统
        
        # 构建工具栏（第一行：分箱方法 + 运行按钮）
        toolbar_line1 = QHBoxLayout()
        toolbar_line1.setSpacing(6)
        
        # 分箱方法下拉框
        self.method_combo = QComboBox()
        
        # 构建方法列表，将最优分箱置顶
        method_map = []
        if OPTBINNING_AVAILABLE:
            method_map.append(("🎯 最优分箱 (推荐)", "optimal"))
            method_map.append(("───────────────", "separator"))
        
        method_map.extend([
            ("智能单调分箱", "smart_monotonic"),  # 新增：自动追求单调，100%有解
            ("等频分箱", "equal_freq"),
            ("等距分箱", "equal_width"),
            ("决策树分箱", "decision_tree"),
            ("卡方分箱", "chi_merge"),
            ("Best-KS 分箱", "best_ks"),
            ("自定义切点", "manual"),
        ])
        
        for label, key in method_map:
            if key == "separator":
                self.method_combo.addItem(label)
                idx = self.method_combo.count() - 1
                self.method_combo.setItemData(idx, False, Qt.ItemDataRole.UserRole - 1)
            else:
                self.method_combo.addItem(label, key)
        
        if OPTBINNING_AVAILABLE:
            self.method_combo.setCurrentIndex(0)
        
        toolbar_line1.addWidget(QLabel("分箱方法："))
        toolbar_line1.addWidget(self.method_combo)
        toolbar_line1.addStretch()
        toolbar_line1.addWidget(self.run_btn)
        toolbar_line1.addWidget(self.save_btn)
        
        # 配置面板区域（单独一行，垂直布局）
        config_container = QWidget()
        config_container.setMinimumWidth(400)  # 确保最小宽度
        config_layout = QVBoxLayout(config_container)
        config_layout.setContentsMargins(0, 0, 0, 0)
        config_layout.setSpacing(4)
        
        # 配置堆叠面板设置 - 设置为固定高度策略
        self.config_stack.setSizePolicy(
            self.config_stack.sizePolicy().horizontalPolicy(),
            self.config_stack.sizePolicy().verticalPolicy()
        )
        
        config_layout.addWidget(self.config_stack, stretch=0)
        # 设置配置容器固定高度，防止拉伸
        config_container.setMaximumHeight(120)
        
        # 汇总到右侧布局
        right_layout.addWidget(self.stats_panel)
        right_layout.addWidget(self.target_label)
        right_layout.addWidget(self.recommend_label)
        right_layout.addWidget(self.dist_card, stretch=0)  # 分布图固定高度
        right_layout.addWidget(self.bin_card, stretch=0)   # 分箱图固定高度
        right_layout.addWidget(self.bin_hint_label)        # 分箱图提示
        right_layout.addLayout(toolbar_line1)
        right_layout.addWidget(config_container, stretch=0)  # 配置面板固定高度
        right_layout.addWidget(self.bin_table_card, stretch=0)
        
        # 将内容容器添加到滚动区域
        right_scroll.setWidget(right_content)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_scroll)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)

        # 事件绑定
        self.method_combo.currentIndexChanged.connect(self.on_method_changed)
        self.run_btn.clicked.connect(self.run_binning)
        self.missing_combo.currentTextChanged.connect(self.on_missing_strategy_changed)
        self.precision_mode_combo.currentIndexChanged.connect(self._update_precision_inputs)
        self._update_precision_inputs()

    def _update_selection_count(self):
        """更新选择计数显示"""
        count = len(self.feature_list.selectedItems())
        self.selection_count_label.setText(f"已选择: {count}")
        self.batch_btn.setEnabled(count > 0)
        if count > 0:
            self.batch_btn.setText(f"批量分箱 ({count})")
        else:
            self.batch_btn.setText("批量分箱")

    def on_batch_binning(self):
        """处理批量分箱按钮点击"""
        selected_items = self.feature_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选择变量")
            return
        
        # 获取选择的变量名
        var_names = [item.text() for item in selected_items]
        
        # 检查目标变量
        method_key = self.method_combo.currentData()
        supervised_methods = ['decision_tree', 'chi_merge', 'best_ks', 'optimal', 'smart_monotonic']
        
        if method_key in supervised_methods and not self.controller.state.target_col:
            QMessageBox.warning(self, "提示", "未设置目标变量，请先设置目标变量")
            return
        
        # 确认对话框
        var_list_text = "\n".join(var_names[:15])
        if len(var_names) > 15:
            var_list_text += f"\n... 等共 {len(var_names)} 个变量"
        
        reply = QMessageBox.question(
            self, "批量分箱确认",
            f"将对以下 {len(var_names)} 个变量执行分箱:\n\n{var_list_text}\n\n分箱方法: {self.method_combo.currentText()}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._start_batch_binning(var_names)

    def _start_batch_binning(self, var_names: List[str]):
        """启动批量分箱"""
        method_key = self.method_combo.currentData()
        
        # 获取分箱参数
        if method_key == 'optimal':
            kwargs = self.optbinning_config.get_config()
        else:
            n_bins = self.n_bins_spin.value()
            kwargs = {'n_bins': n_bins}
            if method_key in ['decision_tree', 'chi_merge']:
                kwargs = {'max_leaf_nodes': n_bins, 'max_bins': n_bins}
            if method_key == 'best_ks':
                kwargs = {'max_bins': n_bins, 'initial_bins': 64}
            if method_key == 'smart_monotonic':
                # 智能单调分箱参数
                trend = self.smart_monotonic_trend_combo.currentData()
                kwargs = {
                    'max_bins': n_bins,
                    'min_bins': 2,
                    'monotonic_trend': trend,
                }
            kwargs['boundary_precision_mode'] = self.precision_mode_combo.currentData()
            kwargs['boundary_precision_digits'] = int(self.precision_digits_spin.value())
        
        # 创建进度对话框
        self.batch_dialog = BatchBinningDialog(self, len(var_names))
        self.batch_dialog.set_variable_names(var_names)
        self.batch_dialog.cancelled.connect(self._cancel_batch_binning)
        
        # 创建工作线程
        self.batch_worker = BatchBinningWorker(
            self.controller, var_names, method_key or 'optimal', **kwargs
        )
        self.batch_worker.progress.connect(self._on_batch_progress)
        self.batch_worker.item_finished.connect(self._on_batch_item_finished)
        self.batch_worker.finished_with_result.connect(self._on_batch_finished)
        
        self.batch_worker.start()
        self.batch_dialog.exec()

    def _on_batch_progress(self, current: int, total: int, var_name: str):
        """处理批量分箱进度更新"""
        if self.batch_dialog:
            self.batch_dialog.update_progress(current, total, var_name)

    def _on_batch_item_finished(self, var_name: str, metrics: BinningMetrics, success: bool, error: str):
        """处理单个变量分箱完成"""
        if not self.batch_dialog:
            return
        
        if success and metrics:
            # 计算 IV 值
            iv_total = metrics.summary_table['iv'].sum() if 'iv' in metrics.summary_table.columns else 0
            self.batch_dialog.mark_success(var_name, iv_total)
        else:
            self.batch_dialog.mark_failed(var_name, error)

    def _on_batch_finished(self, success_list: List[str], failed_list: List[Tuple[str, str]]):
        """批量分箱完成"""
        if self.batch_dialog:
            self.batch_dialog.show_summary(success_list, failed_list)
        
        # 刷新当前选中变量的显示
        if self.current_feature and self.current_feature in success_list:
            if self.current_feature in self.controller.state.binning_results:
                metrics = self.controller.state.binning_results[self.current_feature]
                cfg = self.controller.state.binning_configs[self.current_feature]
                self.render_binning(metrics, cfg)
        
        # 显示完成提示
        if failed_list:
            QMessageBox.warning(
                self, "批量分箱完成",
                f"完成! {len(success_list)} 个成功, {len(failed_list)} 个失败。\n\n"
                f"失败变量:\n" + "\n".join([f"{name}: {err}" for name, err in failed_list[:5]])
            )
        else:
            QMessageBox.information(self, "批量分箱完成", f"全部 {len(success_list)} 个变量分箱成功!")

    def _cancel_batch_binning(self):
        """取消批量分箱"""
        if self.batch_worker:
            self.batch_worker.cancel()

    def _update_precision_inputs(self):
        mode = self.precision_mode_combo.currentData()
        self.precision_digits_spin.setEnabled(mode != "auto")

    def _compact_plot(self, plot: pg.PlotWidget, height: int = 220):
        plot.setBackground('w')
        plot.setFixedHeight(height)
        plot.getPlotItem().layout.setContentsMargins(0, 0, 0, 0)
        small_font = QFont('SansSerif', 8)
        plot.getPlotItem().getAxis('left').setStyle(tickFont=small_font)
        plot.getPlotItem().getAxis('bottom').setStyle(tickFont=small_font)

    def _wrap_card(self, inner_widget: QWidget) -> QWidget:
        card = QWidget()
        card.setProperty("card", True)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.addWidget(inner_widget)
        self._apply_shadow(card)
        return card

    def _apply_shadow(self, w: QWidget):
        try:
            effect = QGraphicsDropShadowEffect()
            from PyQt6.QtGui import QColor
            effect.setColor(QColor(0, 0, 0, 40))
            effect.setBlurRadius(16)
            effect.setOffset(0, 4)
            w.setGraphicsEffect(effect)
        except Exception:
            pass

    def _setup_bottom_anchor(self, plot: pg.PlotWidget):
        try:
            pi = plot.getPlotItem()
            pi.disableAutoRange(axis='y')
            vb = pi.getViewBox()
            vb.sigRangeChanged.connect(lambda _vb, _r: self._force_bottom(vb))
        except Exception:
            pass

    def _force_bottom(self, vb):
        try:
            ymin, ymax = vb.viewRange()[1]
            if ymin != 0:
                vb.setYRange(0, ymax, padding=0)
        except Exception:
            pass

    def setup_connections(self):
        self.controller.project_updated.connect(self.on_project_updated)
        self.controller.binning_finished.connect(self.on_binning_finished)
        self.controller.error_occurred.connect(self.on_error)

    def on_project_updated(self, state: ProjectState):
        self.feature_list.clear()
        if state.feature_cols:
            self.feature_list.addItems(state.feature_cols)
        # 更新样本数
        if OPTBINNING_AVAILABLE and self.optbinning_config is not None:
            self.optbinning_config.set_n_samples(self.controller.get_sample_count())

    def on_error(self, msg: str):
        """处理分箱错误，显示友好的提示"""
        from PyQt6.QtWidgets import QMessageBox
        
        # 检查是否是无解错误
        if "【分箱无解】" in msg:
            # 使用信息框而不是错误框，因为这不是程序错误
            QMessageBox.information(self, "分箱无解 - 建议调整参数", msg)
        else:
            # 其他错误使用错误框
            QMessageBox.critical(self, "错误", msg)

    def on_feature_selected(self, item):
        self.current_feature = item.text()
        self.refresh_stats_and_plots()
        # 如果已有分箱结果，渲染结果和配置
        if self.current_feature in self.controller.state.binning_results:
            metrics = self.controller.state.binning_results[self.current_feature]
            cfg = self.controller.state.binning_configs[self.current_feature]
            self._apply_display_config(cfg)
            self.render_binning(metrics, cfg)
        else:
            # 没有分箱结果时，默认选择最优分箱
            self._set_default_optimal_config()

    def _apply_display_config(self, cfg: BinningConfig):
        """应用保存的配置到 UI"""
        # 恢复分箱方法
        method = cfg.method
        try:
            method_idx = self.method_combo.findData(method)
            if method_idx != -1:
                self.method_combo.setCurrentIndex(method_idx)
                # 触发方法切换，更新配置面板
                self.on_method_changed(method_idx)
        except Exception:
            pass
        
        # 恢复 Optbinning 配置（如果是最优分箱）
        if method == 'optimal' and self.optbinning_config is not None:
            try:
                self.optbinning_config.set_config(cfg.params or {})
            except Exception:
                pass
        
        # 恢复传统配置参数
        params = (cfg.params or {})
        precision_mode = params.get("boundary_precision_mode", "auto")
        precision_digits = params.get("boundary_precision_digits", 0)
        if "boundary_precision_mode" not in params and "boundary_precision" in params:
            precision_mode, precision_digits = parse_precision_step(str(params.get("boundary_precision")))
        try:
            pidx = self.precision_mode_combo.findData(precision_mode)
            if pidx != -1:
                self.precision_mode_combo.setCurrentIndex(pidx)
        except Exception:
            pass
        try:
            self.precision_digits_spin.setValue(int(precision_digits))
        except Exception:
            self.precision_digits_spin.setValue(0)
        self._update_precision_inputs()

    def _set_default_optimal_config(self):
        """设置默认配置为最优分箱，并清空之前的结果展示"""
        try:
            # 默认选择最优分箱
            idx = self.method_combo.findData('optimal')
            if idx != -1:
                self.method_combo.setCurrentIndex(idx)
                self.on_method_changed(idx)
            
            # 重置 Optbinning 配置为默认
            if self.optbinning_config is not None:
                self.optbinning_config.set_config({})
                
            # 清空分箱结果展示
            self._clear_binning_display()
        except Exception:
            pass
    
    def _clear_binning_display(self):
        """清空分箱结果展示区域"""
        # 清空分箱图
        if self.bin_plot is not None:
            self.bin_plot.clear()
            self.split_lines.clear()
        
        # 清空分箱明细表
        if self.bin_table is not None:
            self.bin_table.clearContents()
            self.bin_table.setRowCount(0)
            # 重置表格高度
            self.bin_table.setFixedHeight(100)
        
        # 隐藏单调性趋势指示器
        if hasattr(self, '_trend_indicator_label'):
            self._trend_indicator_label.hide()
        
        # 重置内部状态
        self._current_metrics_df = None
        self._current_centers = None
        self._current_bad_rates = None

    def refresh_stats_and_plots(self):
        if not self.current_feature: return
        # 统计
        stats = self.controller.state.variable_stats.get(self.current_feature)
        if stats:
            # 清空并横向填充栅格
            while self.stats_grid.count():
                item = self.stats_grid.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()
            metrics = [
                ("类型", stats.dtype),
                ("样本数", str(stats.n_samples)),
                ("缺失", f"{stats.n_missing} ({stats.missing_pct:.2%})"),
                ("唯一值", str(stats.n_unique)),
                ("最小值", f"{stats.min_val:.4f}" if stats.min_val is not None else "-"),
                ("最大值", f"{stats.max_val:.4f}" if stats.max_val is not None else "-"),
                ("均值", f"{stats.mean_val:.4f}" if stats.mean_val is not None else "-"),
                ("标准差", f"{stats.std_val:.4f}" if stats.std_val is not None else "-"),
            ]
            for idx, (k, v) in enumerate(metrics):
                lab_k = QLabel(k); lab_k.setProperty("title", True)
                lab_v = QLabel(v)
                r = idx // 4; c = (idx % 4) * 2
                self.stats_grid.addWidget(lab_k, r, c)
                self.stats_grid.addWidget(lab_v, r, c + 1)
        # 目标变量提示
        if self.controller.state and self.controller.state.target_col:
            self.target_label.setText(f"目标变量：{self.controller.state.target_col}")
        else:
            self.target_label.setText("未设置目标变量：请在数据导入页右键列名进行设置")
        # 建议（仅显示，不自动更改用户选择）
        target = self.controller.df[self.controller.state.target_col] if self.controller.state and self.controller.state.target_col else None
        rec = recommend_method(self.controller.df[self.current_feature], target)
        self.recommend_label.setText(f"分箱建议：{method_to_cn(rec)}")
        # 分布图
        self.dist_plot.clear()
        # 清理右侧Y轴的内容
        for item in list(self.dist_plot_right_axis.addedItems):
            self.dist_plot_right_axis.removeItem(item)
        
        series = self.controller.df[self.current_feature].dropna()
        target = None
        if self.controller.state and self.controller.state.target_col:
            target = self.controller.df[self.controller.state.target_col]
        
        if pd.api.types.is_numeric_dtype(series):
            y, x = np.histogram(series, bins=20)
            width = x[1] - x[0]
            x_centers = x[:-1] + width/2
            bar = pg.BarGraphItem(x=x_centers, height=y, width=width*0.9, brush=pg.mkBrush(120, 160, 220, 160))
            self.dist_plot.addItem(bar)
            
            # 如果有目标变量，计算每个区间的坏样本率并绘制
            if target is not None:
                bad_rates = []
                valid_centers = []
                for i in range(len(x) - 1):
                    left, right = x[i], x[i + 1]
                    # 找到当前区间的样本
                    mask = (series >= left) & (series < right)
                    if i == len(x) - 2:  # 最后一个区间包含右边界
                        mask = (series >= left) & (series <= right)
                    
                    bin_samples = mask.sum()
                    if bin_samples > 0:
                        # 获取对应的目标值
                        bin_target = target[series.index[mask]]
                        bad_rate = bin_target.mean() if bin_target.count() > 0 else 0
                        bad_rates.append(bad_rate)
                        valid_centers.append(x_centers[i])
                
                if bad_rates:
                    # 在右侧Y轴绘制坏样本率曲线
                    curve = pg.PlotCurveItem(
                        x=valid_centers, 
                        y=bad_rates, 
                        pen=pg.mkPen('red', width=2),
                        symbol='o',
                        symbolSize=4,
                        symbolBrush='red'
                    )
                    self.dist_plot_right_axis.addItem(curve)
                    # 设置Y轴范围并启用自动调整
                    self.dist_plot_right_axis.setYRange(0, max(bad_rates) * 1.2 if max(bad_rates) > 0 else 1)
                    self.dist_plot_right_axis.enableAutoRange(axis='y', enable=True)
            
            try:
                xmin, xmax = float(x.min()), float(x.max())
                ymax = float(y.max()) if y.size else 1.0
                self.dist_plot.getPlotItem().setRange(xRange=(xmin, xmax), yRange=(0, ymax * 1.05), padding=0.0)
                self.dist_plot_right_axis.setXRange(xmin, xmax, padding=0)
                # 强制同步几何位置
                self.dist_plot_right_axis.setGeometry(self.dist_plot.plotItem.vb.sceneBoundingRect())
            except Exception:
                pass
        else:
            counts = series.value_counts().head(20)
            x = np.arange(len(counts))
            bar = pg.BarGraphItem(x=x, height=counts.values, width=0.6, brush=pg.mkBrush(160, 200, 120, 160))
            self.dist_plot.addItem(bar)
            
            # 如果有目标变量，计算每个类别的坏样本率
            if target is not None:
                bad_rates = []
                valid_x = []
                for i, category in enumerate(counts.index):
                    mask = series == category
                    bin_samples = mask.sum()
                    if bin_samples > 0:
                        bin_target = target[series.index[mask]]
                        bad_rate = bin_target.mean() if bin_target.count() > 0 else 0
                        bad_rates.append(bad_rate)
                        valid_x.append(i)
                
                if bad_rates:
                    curve = pg.PlotCurveItem(
                        x=valid_x, 
                        y=bad_rates, 
                        pen=pg.mkPen('red', width=2),
                        symbol='o',
                        symbolSize=4,
                        symbolBrush='red'
                    )
                    self.dist_plot_right_axis.addItem(curve)
                    self.dist_plot_right_axis.setYRange(0, max(bad_rates) * 1.2 if max(bad_rates) > 0 else 1)
                    self.dist_plot_right_axis.enableAutoRange(axis='y', enable=True)
            
            try:
                n = len(counts)
                ymax = float(counts.values.max()) if n else 1.0
                self.dist_plot.getPlotItem().setRange(xRange=(-0.5, n - 0.5), yRange=(0, ymax * 1.05), padding=0.0)
                self.dist_plot_right_axis.setXRange(-0.5, n - 0.5, padding=0)
                # 强制同步几何位置
                self.dist_plot_right_axis.setGeometry(self.dist_plot.plotItem.vb.sceneBoundingRect())
            except Exception:
                pass

    def on_method_changed(self, index):
        """分箱方法切换处理 - 动态切换配置面板"""
        method = self.method_combo.currentData()
        
        if method == "optimal" and self.optbinning_config is not None:
            self.config_stack.setCurrentIndex(1)  # 显示 Optbinning 配置面板
            # 更新样本数参考
            self.optbinning_config.set_n_samples(self.controller.get_sample_count())
            # 调整容器高度以容纳展开的高级选项
            self.config_stack.parentWidget().setMaximumHeight(16777215)  # 取消高度限制
        else:
            self.config_stack.setCurrentIndex(0)  # 显示传统配置面板
            # 限制容器高度，防止传统配置面板占用太多空间
            self.config_stack.parentWidget().setMaximumHeight(120)
        
        # 控制智能单调分箱配置的显示/隐藏
        is_smart_monotonic = (method == "smart_monotonic")
        self.smart_monotonic_trend_combo.setVisible(is_smart_monotonic)
        self.smart_monotonic_trend_label.setVisible(is_smart_monotonic)

    def run_binning(self):
        if not self.current_feature: 
            return
        
        # 以中文选项映射到内部方法键
        method_key = self.method_combo.currentData()
        method = method_key if method_key else self.method_combo.currentText()
        
        # 检查是否为监督学习方法且未设置目标变量
        supervised = method in ['decision_tree', 'chi_merge', 'best_ks', 'optimal', 'smart_monotonic']
        if supervised and not (self.controller.state and self.controller.state.target_col):
            QMessageBox.warning(self, "提示", "未设置目标变量，当前建议为监督分箱，请先设置目标变量")
            return
        
        # 如果已有正在运行的任务，先停止
        if self._binning_worker is not None and self._binning_worker.isRunning():
            QMessageBox.information(self, "提示", "正在处理中，请稍候...")
            return
        
        # 准备参数
        kwargs = {}
        if method_key == 'optimal':
            # 获取 Optbinning 配置
            kwargs = self.optbinning_config.get_config()
            
            # 类型验证：检查类型选择是否适合数据
            if self.optbinning_config is not None and self.current_feature:
                import pandas as pd
                feature_data = self.controller.df[self.current_feature]
                valid, warning_msg = self.optbinning_config.validate_dtype_for_data(feature_data)
                if not valid:
                    reply = QMessageBox.question(
                        self, "类型不匹配警告",
                        warning_msg + "\n\n是否继续运行？",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.No:
                        return
        else:
            # 传统配置
            n_bins = self.n_bins_spin.value()
            kwargs = {'n_bins': n_bins}
            if method_key in ['decision_tree', 'chi_merge']:
                kwargs = {'max_leaf_nodes': n_bins, 'max_bins': n_bins}
            if method_key == 'best_ks':
                kwargs = {'max_bins': n_bins, 'initial_bins': 64}
            if method_key == 'smart_monotonic':
                # 智能单调分箱参数
                trend = self.smart_monotonic_trend_combo.currentData()
                kwargs = {
                    'max_bins': n_bins,
                    'min_bins': 2,
                    'monotonic_trend': trend,
                }
            kwargs['boundary_precision_mode'] = self.precision_mode_combo.currentData()
            kwargs['boundary_precision_digits'] = int(self.precision_digits_spin.value())
        
        # 运行按钮 loading 状态
        self.run_btn.setEnabled(False)
        self._run_btn_original_text = self.run_btn.text()
        self.run_btn.setText("运行中...")
        
        # 设置全局等待光标（提示用户正在处理）
        from PyQt6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        # 创建并启动工作线程
        self._binning_worker = SingleBinningWorker(
            self.controller, self.current_feature, method, **kwargs
        )
        self._binning_worker.finished.connect(self._on_single_binning_finished)
        self._binning_worker.start()
    
    def _on_single_binning_finished(self, feature: str, metrics, success: bool, error_msg: str):
        """单变量分箱完成的回调"""
        # 恢复光标
        from PyQt6.QtWidgets import QApplication
        QApplication.restoreOverrideCursor()
        
        # 恢复按钮状态
        self.run_btn.setEnabled(True)
        if hasattr(self, '_run_btn_original_text'):
            self.run_btn.setText(self._run_btn_original_text)
        
        # 清理工作线程
        self._binning_worker = None
        
        if not success:
            # 显示错误信息
            from PyQt6.QtWidgets import QMessageBox
            if "【分箱无解】" in error_msg:
                QMessageBox.information(self, "分箱无解 - 建议调整参数", error_msg)
            else:
                QMessageBox.critical(self, "错误", f"分箱失败: {error_msg}")
            return
        
        # 分箱成功，更新显示
        # 注意：controller 已经发送了 binning_finished 信号，on_binning_finished 会被调用

    def on_binning_finished(self, feature: str, metrics: BinningMetrics):
        if feature != self.current_feature: return
        cfg = self.controller.state.binning_configs[feature]
        self._apply_display_config(cfg)
        self.render_binning(metrics, cfg)
        
        # 检查是否有趋势警告（peak/valley 约束未生效）
        self._check_and_show_trend_warning(cfg)

    def render_binning(self, metrics: BinningMetrics, cfg: BinningConfig):
        precision = resolve_precision_step(cfg.params)
        splits = cfg.splits
        
        # 添加单调性趋势指示器
        self._update_trend_indicator(cfg)
        # 清理并绘制直方图+坏率折线（小图）
        self.bin_plot.clear(); self.split_lines.clear()
        data = self.controller.df[self.current_feature].dropna()
        y, x = np.histogram(data, bins=50)
        bin_width = (x[1]-x[0]) if x.size > 1 else 1.0
        bar = pg.BarGraphItem(x=x[:-1], height=y, width=bin_width, brush=pg.mkBrush(200, 200, 200, 100))
        self.bin_plot.addItem(bar)

        df = metrics.summary_table.reset_index()
        centers, bad_rates = [], []
        for _, row in df.iterrows():
            b = row['bin']
            if isinstance(b, pd.Interval):
                # 处理可能的 inf 值
                left = b.left if np.isfinite(b.left) else np.nan
                right = b.right if np.isfinite(b.right) else np.nan
                if np.isfinite(left) and np.isfinite(right):
                    centers.append((left + right) / 2)
                elif np.isfinite(left):
                    centers.append(left)
                elif np.isfinite(right):
                    centers.append(right)
                else:
                    centers.append(np.nan)
            else:
                try:
                    txt = str(b).replace('(', '').replace(']', '').replace('[', '').replace(')', '')
                    parts = txt.split(',')
                    left = float(parts[0])
                    right = float(parts[1]) if len(parts) > 1 else left
                    # 处理 inf 值
                    left = left if np.isfinite(left) else np.nan
                    right = right if np.isfinite(right) else np.nan
                    if np.isfinite(left) and np.isfinite(right):
                        centers.append((left + right) / 2)
                    elif np.isfinite(left):
                        centers.append(left)
                    elif np.isfinite(right):
                        centers.append(right)
                    else:
                        centers.append(np.nan)
                except Exception:
                    centers.append(np.nan)
            bad_rates.append(row['bad_rate'])
        centers = np.array(centers)
        mask = ~np.isnan(centers)
        curve = pg.PlotCurveItem(x=centers[mask], y=np.array(bad_rates)[mask], pen=pg.mkPen('b', width=2))
        self.bin_plot.addItem(curve)

        for i, split in enumerate(splits):
            if np.isinf(split):
                continue
            line = pg.InfiniteLine(pos=split, movable=True, angle=90, pen=pg.mkPen('r', width=2, style=Qt.PenStyle.DashLine))
            line.sigPositionChangeFinished.connect(self.on_split_dragged)
            # 添加双击事件 - 打开输入对话框设置精确值
            line.setCursor(Qt.CursorShape.PointingHandCursor)
            line._split_index = i  # 保存索引用于识别
            line._split_value = split  # 保存原始值
            self.bin_plot.addItem(line)
            self.split_lines.append(line)
        
        # 在 plot 上安装事件过滤器来捕获双击事件
        self.bin_plot.viewport().installEventFilter(self)

        self._current_metrics_df = df
        self._current_centers = centers
        self._current_bad_rates = bad_rates

        # 视窗范围与限制：确保有效数据居中可见
        try:
            if not self._skip_autorange_once:
                xmin, xmax = float(x.min()), float(x.max())
                ymax = float(np.max(y)) if y.size else 1.0
                self.bin_plot.getPlotItem().setRange(xRange=(xmin, xmax + bin_width), yRange=(0, ymax * 1.05), padding=0.0)
        except Exception:
            pass
        self._skip_autorange_once = False

        # 填充分箱明细表
        self.bin_table.clearContents()
        # 明细行 + 合计行
        self.bin_table.setRowCount(len(df) + 1)
        for i, row in df.iterrows():
            values = [
                format_bin_label(row['bin'], precision=precision),
                str(row['total']),
                f"{row['total_pct']:.2%}",
                str(row['bad']),
                f"{row['bad_rate']:.2%}",
                str(row['good']),
                f"{row['good'] / max(row['total'], 1):.2%}",
                f"{row['woe']:.4f}",
                f"{row['iv']:.4f}",
                f"{row['lift']:.2f}",
            ]
            for j, v in enumerate(values):
                self.bin_table.setItem(i, j, QTableWidgetItem(v))
        # 合计行
        total = int(df['total'].sum())
        bad_sum = int(df['bad'].sum())
        good_sum = int(df['good'].sum())
        total_pct = "100.00%"
        # 使用全局坏样本率
        if self.controller.state and self.controller.state.target_col:
            overall_bad_rate = float(self.controller.df[self.controller.state.target_col].mean())
        else:
            overall_bad_rate = bad_sum / max(total, 1)
        overall_good_rate = 1.0 - overall_bad_rate
        sum_values = [
            "合计",
            str(total),
            total_pct,
            str(bad_sum),
            f"{overall_bad_rate:.2%}",
            str(good_sum),
            f"{overall_good_rate:.2%}",
            "—",
            "—",
            "—",
        ]
        last_idx = len(df)
        for j, v in enumerate(sum_values):
            self.bin_table.setItem(last_idx, j, QTableWidgetItem(v))

        # 根据内容自适应高度，完整展示所有行
        try:
            self.bin_table.resizeRowsToContents()
            header_h = self.bin_table.horizontalHeader().height()
            rows_h = sum(self.bin_table.rowHeight(i) for i in range(self.bin_table.rowCount()))
            margins = 24
            # 使用固定高度确保完整展示
            self.bin_table.setFixedHeight(header_h + rows_h + margins)
            # 触发父布局更新
            self.bin_table.updateGeometry()
            self.bin_table.parentWidget().adjustSize()
        except Exception:
            pass

    def _check_and_show_trend_warning(self, cfg: BinningConfig) -> None:
        """检查并显示单调性趋势约束的警告信息。
        
        当用户选择 peak/valley 但约束未生效时，显示提示信息。
        """
        if not cfg or not cfg.params:
            return
        
        trend = cfg.params.get('monotonic_trend', 'auto')
        if trend not in ['peak', 'valley', 'peak_heuristic', 'valley_heuristic']:
            return
        
        # 从分箱结果中检查实际趋势
        if not self.controller.state.binning_results.get(self.current_feature):
            return
        
        metrics = self.controller.state.binning_results[self.current_feature]
        if metrics.summary_table is None or len(metrics.summary_table) < 3:
            return
        
        # 获取坏样本率
        bad_rates = metrics.summary_table['bad_rate'].tolist()
        if not bad_rates:
            return
        
        # 检测实际趋势
        increasing = decreasing = 0
        for i in range(len(bad_rates) - 1):
            if bad_rates[i+1] > bad_rates[i]:
                increasing += 1
            elif bad_rates[i+1] < bad_rates[i]:
                decreasing += 1
        
        # 判断实际趋势
        actual_trend = None
        if increasing > 0 and decreasing == 0:
            actual_trend = 'ascending'
        elif decreasing > 0 and increasing == 0:
            actual_trend = 'descending'
        elif increasing > 0 and decreasing > 0:
            max_idx = bad_rates.index(max(bad_rates))
            min_idx = bad_rates.index(min(bad_rates))
            if max_idx not in [0, len(bad_rates)-1]:
                actual_trend = 'peak'
            elif min_idx not in [0, len(bad_rates)-1]:
                actual_trend = 'valley'
        
        # 检查是否符合预期
        expected_base = trend.replace('_heuristic', '')
        if actual_trend and actual_trend != expected_base:
            # 在标题栏显示警告
            trend_names = {'peak': '单峰', 'valley': '单谷', 'ascending': '递增', 'descending': '递减'}
            expected_cn = trend_names.get(expected_base, expected_base)
            actual_cn = trend_names.get(actual_trend, actual_trend)
            
            QMessageBox.information(
                self,
                f"{expected_cn}约束未生效",
                f"期望的『{expected_cn}』趋势未生效，实际分箱结果为『{actual_cn}』趋势。\n\n"
                f"可能原因：\n"
                f"1. 数据本身的分布特性决定了最优解是{actual_cn}的\n"
                f"2. 预分箱数不足，无法形成有效的转折点\n"
                f"3. 其他约束条件（如最小占比）限制了形状\n\n"
                f"建议尝试：\n"
                f"• 增加『预分箱数』到 50-100\n"
                f"• 使用『{expected_base}_heuristic』求解方式\n"
                f"• 暂时接受当前结果，或改用其他分箱方法"
            )

    def _update_trend_indicator(self, cfg: BinningConfig):
        """更新单调性趋势指示器"""
        trend = cfg.params.get('monotonic_trend', 'auto') if cfg.params else 'auto'
        
        icon = TREND_ICONS.get(trend, '📊')
        label = TREND_LABELS.get(trend, trend)
        
        if not hasattr(self, '_trend_indicator'):
            self._trend_indicator = QLabel(self.bin_plot)
            self._trend_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._trend_indicator.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 255, 255, 0.9);
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-size: 11px;
                    color: #495057;
                }
            """)
        
        self._trend_indicator.setText(f"{icon} {label}")
        self._trend_indicator.adjustSize()
        
        # 定位到右上角 (相对于 bin_plot)
        plot_width = self.bin_plot.width()
        indicator_width = self._trend_indicator.width()
        self._trend_indicator.move(plot_width - indicator_width - 10, 10)
        self._trend_indicator.raise_()  # 确保在最上层
        self._trend_indicator.show()

    def resizeEvent(self, event):
        """窗口大小变化时重新定位指示器"""
        super().resizeEvent(event)
        if hasattr(self, '_trend_indicator') and self._trend_indicator.isVisible():
            # 重新定位到右上角
            plot_width = self.bin_plot.width()
            indicator_width = self._trend_indicator.width()
            self._trend_indicator.move(plot_width - indicator_width - 10, 10)

    def _connect_line_double_click(self, line):
        """为分割线连接双击事件"""
        # 检查 scene 是否可用
        scene = line.scene()
        if scene is None:
            # 如果 scene 为 None，延迟连接
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, lambda: self._connect_line_double_click(line))
            return
        
        # 使用自定义属性存储是否处于双击检测状态
        line._click_count = 0
        line._click_timer = None
        
        def on_line_clicked(line=line):
            """处理点击事件，区分单击和双击"""
            line._click_count += 1
            if line._click_count == 1:
                # 第一次点击，启动定时器
                from PyQt6.QtCore import QTimer
                line._click_timer = QTimer()
                line._click_timer.setSingleShot(True)
                line._click_timer.timeout.connect(lambda: self._on_split_single_click(line))
                line._click_timer.start(200)  # 200ms 内第二次点击视为双击
            elif line._click_count == 2:
                # 第二次点击，是双击
                if line._click_timer:
                    line._click_timer.stop()
                    line._click_timer = None
                line._click_count = 0
                self._on_split_double_click(line)
        
        # 使用 scene 的鼠标点击事件
        try:
            scene.sigMouseClicked.connect(lambda evt, l=line: on_line_clicked(l) if self._is_line_clicked(l, evt) else None)
        except Exception:
            pass  # 忽略连接错误
    
    def eventFilter(self, obj, event):
        """事件过滤器 - 处理分割线的双击事件"""
        from PyQt6.QtCore import QEvent, QPointF
        # 检查是否是 plot viewport 的双击事件
        if obj == self.bin_plot.viewport() and event.type() == QEvent.Type.MouseButtonDblClick:
            # 获取鼠标在屏幕上的位置
            mouse_pos = event.pos()
            
            # 找到最近的分割线（基于屏幕像素距离）
            closest_line = None
            closest_pixel_dist = float('inf')
            
            for line in self.split_lines:
                if not line.isVisible():
                    continue
                # 获取分割线在屏幕上的位置（转换为 QPointF）
                line_val = float(line.value())  # 转换为 Python float
                line_view_pos = QPointF(line_val, 0)
                line_scene_pos = self.bin_plot.getViewBox().mapViewToScene(line_view_pos)
                line_pixel_pos = self.bin_plot.mapFromScene(line_scene_pos).x()
                
                # 计算像素距离
                pixel_dist = abs(mouse_pos.x() - line_pixel_pos)
                
                if pixel_dist < closest_pixel_dist:
                    closest_pixel_dist = pixel_dist
                    closest_line = line
            
            # 如果距离足够近（小于30像素），认为是点击了该分割线
            if closest_line and closest_pixel_dist < 30:
                self._on_split_double_click(closest_line)
                return True  # 事件已处理
        
        return super().eventFilter(obj, event)
    
    def _is_line_clicked(self, line, evt):
        """检查是否点击了指定的分割线"""
        if not line.isVisible():
            return False
        # 获取鼠标位置并检查是否在线附近
        mouse_pos = evt.scenePos()
        line_pos = line.pos()
        # 简单的距离检查（垂直线，检查 x 坐标）
        return abs(mouse_pos.x() - line_pos.x()) < 10  # 10像素容错
    
    def _on_split_single_click(self, line):
        """单击分割线 - 重置计数"""
        line._click_count = 0
    
    def _on_split_double_click(self, line):
        """双击分割线 - 打开输入对话框设置精确值"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel
        
        current_value = line.value()
        
        # 创建对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("设置切点值")
        dialog.setMinimumWidth(250)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 当前值标签
        layout.addWidget(QLabel(f"当前值: {current_value:.4f}"))
        
        # 输入框
        layout.addWidget(QLabel("新值:"))
        input_field = QLineEdit()
        input_field.setText(f"{current_value:.4f}")
        input_field.selectAll()
        layout.addWidget(input_field)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        confirm_btn = QPushButton("确认")
        confirm_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        confirm_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(confirm_btn)
        
        layout.addLayout(btn_layout)
        
        # 显示对话框并处理结果
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                new_value = float(input_field.text())
                # 更新分割线位置
                line.setValue(new_value)
                # 触发重新计算
                self.on_split_dragged()
            except ValueError:
                QMessageBox.warning(self, "输入错误", "请输入有效的数字")
    
    def on_split_dragged(self):
        self._skip_autorange_once = True
        new_splits = []
        for l in self.split_lines:
            new_splits.append(l.value())
        new_splits.sort()
        if new_splits and new_splits[0] != -np.inf: new_splits.insert(0, -np.inf)
        if new_splits and new_splits[-1] != np.inf: new_splits.append(np.inf)
        self.controller.update_splits(self.current_feature, new_splits)

    def on_mouse_moved(self, pos):
        mouse_point = self.bin_plot.plotItem.vb.mapSceneToView(pos)
        x_val = mouse_point.x()
        if self._current_centers is None: return
        centers = np.array(self._current_centers)
        bad_rates = np.array(self._current_bad_rates)
        if centers.size == 0: return
        # 检查是否所有 centers 都是 NaN
        if np.all(np.isnan(centers)):
            return
        idx = int(np.nanargmin(np.abs(centers - x_val)))
        row = self._current_metrics_df.iloc[idx]
        cfg = self.controller.state.binning_configs.get(self.current_feature)
        precision = (resolve_precision_step(cfg.params) if cfg else "auto")
        # 使用标题显示简短提示（紧凑）
        self.bin_plot.setTitle(
            f"箱：{format_bin_label(row['bin'], precision=precision)} | 样本数：{row['total']} | 坏样本率：{row['bad_rate']:.2%} | WOE：{row['woe']:.3f}"
        )

    def on_missing_strategy_changed(self, text):
        if not self.current_feature: return
        # 中文策略映射
        mapping = {"单独成箱": "separate", "忽略": "ignore", "归并": "merge"}
        internal = mapping.get(text, text)
        cfg = self.controller.state.binning_configs.get(self.current_feature)
        if cfg:
            cfg.missing_strategy = internal
            self.controller.state.binning_configs[self.current_feature] = cfg
            self.run_binning()
