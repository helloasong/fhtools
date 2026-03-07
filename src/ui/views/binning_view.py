from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
    QTableWidget, QTableWidgetItem, QLabel, QSplitter, 
    QComboBox, QPushButton, QSpinBox, QMenu, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
import pyqtgraph as pg
import numpy as np
import pandas as pd
from src.controllers.project_controller import ProjectController
from src.data.models import ProjectState, BinningMetrics
from src.utils.formatting import format_bin_label, parse_precision_step, resolve_precision_step

class DraggableInfiniteLine(pg.InfiniteLine):
    """
    可拖动的切点线，拖动结束后发送信号。
    """
    sigDragFinished = pyqtSignal(object)

    def __init__(self, pos, **kwargs):
        super().__init__(pos, movable=True, angle=90, pen=pg.mkPen('r', width=2, style=Qt.PenStyle.DashLine), **kwargs)
        self.sigPositionChangeFinished.connect(self.on_drag_finished)

    def on_drag_finished(self):
        self.sigDragFinished.emit(self)

class BinningView(QWidget):
    """
    分箱视图：
    1. 变量选择
    2. 算法配置 (Method, Params)
    3. 交互式绘图 (直方图 + 拖拽切点)
    4. 结果展示 (WOE/IV 表格)
    """
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self.current_feature = None
        self.split_lines = [] # 存储当前的切点线对象
        
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 1. 左侧：变量列表
        self.feature_list = QListWidget()
        self.feature_list.itemClicked.connect(self.on_feature_selected)
        
        # 2. 中间：配置与图表
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        
        # 2.1 顶部工具栏
        toolbar = QHBoxLayout()
        
        self.method_combo = QComboBox()
        self.method_combo.addItems(["equal_freq", "equal_width", "decision_tree", "chi_merge", "best_ks", "manual"])
        self.missing_combo = QComboBox()
        self.missing_combo.addItems(["separate", "ignore", "merge"])
        self.missing_combo.currentTextChanged.connect(self.on_missing_strategy_changed)
        
        self.n_bins_spin = QSpinBox()
        self.n_bins_spin.setRange(2, 20)
        self.n_bins_spin.setValue(5)
        self.n_bins_spin.setPrefix("Bins: ")

        self.precision_mode_combo = QComboBox()
        for label, key in [("auto", "auto"), ("decimal places", "decimal"), ("integer places", "integer")]:
            self.precision_mode_combo.addItem(label, key)
        self.precision_digits_spin = QSpinBox()
        self.precision_digits_spin.setRange(0, 12)
        self.precision_digits_spin.setValue(0)

        self.precision_mode_combo.currentIndexChanged.connect(self._update_precision_inputs)
        self._update_precision_inputs()
        
        run_btn = QPushButton("Run Binning")
        run_btn.clicked.connect(self.run_binning)
        
        save_btn = QPushButton("Confirm & Save") # TODO: Implement save snapshot
        
        toolbar.addWidget(QLabel("Method:"))
        toolbar.addWidget(self.method_combo)
        toolbar.addWidget(self.n_bins_spin)
        toolbar.addWidget(QLabel("Precision:"))
        toolbar.addWidget(self.precision_mode_combo)
        toolbar.addWidget(self.precision_digits_spin)
        toolbar.addWidget(run_btn)
        toolbar.addWidget(QLabel("Missing:"))
        toolbar.addWidget(self.missing_combo)
        toolbar.addWidget(save_btn)
        toolbar.addStretch()
        
        # 2.2 交互式图表
        self.plot_widget = pg.PlotWidget(title="Binning Plot (Right Click to Add Split)")
        self.plot_widget.setBackground('w')
        # 启用鼠标交互
        self.plot_widget.scene().sigMouseClicked.connect(self.on_plot_clicked)
        self.plot_widget.scene().sigMouseMoved.connect(self.on_mouse_moved)
        self.hover_label = QLabel("")
        
        center_layout.addLayout(toolbar)
        center_layout.addWidget(self.plot_widget)
        center_layout.addWidget(self.hover_label)
        
        # 3. 右侧：结果表格 (WOE/IV)
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(6)
        self.result_table.setHorizontalHeaderLabels(["Bin", "Count", "Bad Rate", "WOE", "IV", "Bad/Total"])
        self.result_table.setFixedWidth(400)
        
        splitter.addWidget(self.feature_list)
        splitter.addWidget(center_panel)
        splitter.addWidget(self.result_table)
        splitter.setStretchFactor(1, 3)
        
        layout.addWidget(splitter)

    def setup_connections(self):
        self.controller.project_updated.connect(self.on_project_updated)
        self.controller.binning_finished.connect(self.on_binning_finished)

    def on_project_updated(self, state: ProjectState):
        self.feature_list.clear()
        if state.feature_cols:
            self.feature_list.addItems(state.feature_cols)

    def on_feature_selected(self, item):
        self.current_feature = item.text()
        # 如果已有结果，加载结果；否则清空
        if self.current_feature in self.controller.state.binning_results:
            metrics = self.controller.state.binning_results[self.current_feature]
            config = self.controller.state.binning_configs[self.current_feature]
            self._apply_display_config(config)
            self.render_result(metrics, config)
        else:
            # 默认运行一次等频分箱
            self.run_binning()

    def _apply_display_config(self, config):
        params = (config.params or {})
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

    def _update_precision_inputs(self):
        mode = self.precision_mode_combo.currentData()
        self.precision_digits_spin.setEnabled(mode != "auto")

    def run_binning(self):
        if not self.current_feature:
            return
            
        method = self.method_combo.currentText()
        n_bins = self.n_bins_spin.value()
        
        # 异步调用 Controller
        # 针对决策树等有监督算法，需要 max_leaf_nodes = n_bins
        kwargs = {'n_bins': n_bins}
        if method in ['decision_tree', 'chi_merge']:
            kwargs = {'max_leaf_nodes': n_bins, 'max_bins': n_bins}
        if method == 'best_ks':
            kwargs = {'max_bins': n_bins, 'initial_bins': 64}

        kwargs['boundary_precision_mode'] = self.precision_mode_combo.currentData()
        kwargs['boundary_precision_digits'] = int(self.precision_digits_spin.value())
        
        self.controller.run_binning(self.current_feature, method=method, **kwargs)

    def on_binning_finished(self, feature: str, metrics: BinningMetrics):
        if feature != self.current_feature:
            return
            
        # 获取最新的切点
        config = self.controller.state.binning_configs[feature]
        self._apply_display_config(config)
        self.render_result(metrics, config)

    def render_result(self, metrics: BinningMetrics, config):
        """渲染图表和表格"""
        precision = resolve_precision_step(config.params)
        splits = config.splits
        # 1. 渲染表格
        df = metrics.summary_table.reset_index()
        self.result_table.setRowCount(len(df))
        for i, row in df.iterrows():
            # Bin range
            self.result_table.setItem(i, 0, QTableWidgetItem(format_bin_label(row['bin'], precision=precision)))
            self.result_table.setItem(i, 1, QTableWidgetItem(str(row['total'])))
            self.result_table.setItem(i, 2, QTableWidgetItem(f"{row['bad_rate']:.2%}"))
            self.result_table.setItem(i, 3, QTableWidgetItem(f"{row['woe']:.4f}"))
            self.result_table.setItem(i, 4, QTableWidgetItem(f"{row['iv']:.4f}"))
            self.result_table.setItem(i, 5, QTableWidgetItem(f"{row['bad']}/{row['total']}"))
            
        # 2. 渲染图表
        self.plot_widget.clear()
        self.split_lines.clear()
        
        # 绘制背景直方图
        data = self.controller.df[self.current_feature].dropna()
        y, x = np.histogram(data, bins=50)
        bar_item = pg.BarGraphItem(x=x[:-1], height=y, width=(x[1]-x[0]), brush=pg.mkBrush(200, 200, 200, 100))
        self.plot_widget.addItem(bar_item)
        # 绘制 Bad Rate 折线
        df = metrics.summary_table.reset_index()
        centers = []
        bad_rates = []
        for _, row in df.iterrows():
            b = row['bin']
            if isinstance(b, pd.Interval):
                centers.append((b.left + b.right) / 2)
            else:
                try:
                    txt = str(b)
                    parts = txt.replace('(', '').replace(']', '').split(',')
                    centers.append((float(parts[0]) + float(parts[1])) / 2)
                except Exception:
                    centers.append(np.nan)
            bad_rates.append(row['bad_rate'])
        centers = np.array(centers)
        mask = ~np.isnan(centers)
        curve = pg.PlotCurveItem(x=centers[mask], y=np.array(bad_rates)[mask], pen=pg.mkPen('b', width=2))
        self.plot_widget.addItem(curve)
        
        # 绘制切点线
        for split in splits:
            if np.isinf(split):
                continue
            line = DraggableInfiniteLine(pos=split)
            line.sigDragFinished.connect(self.on_split_dragged)
            self.plot_widget.addItem(line)
            self.split_lines.append(line)

        self._current_metrics_df = df
        self._current_centers = centers
        self._current_bad_rates = bad_rates

    def on_split_dragged(self, line):
        """当切点被拖动后，收集所有切点并重新计算"""
        new_splits = []
        for l in self.split_lines:
            new_splits.append(l.value())
            
        new_splits.sort()
        # 自动补全 inf
        if new_splits[0] != -np.inf: new_splits.insert(0, -np.inf)
        if new_splits[-1] != np.inf: new_splits.append(np.inf)
        
        # 调用 Controller 更新 (Manual mode)
        self.controller.update_splits(self.current_feature, new_splits)

    def on_missing_strategy_changed(self, text):
        if not self.current_feature:
            return
        cfg = self.controller.state.binning_configs.get(self.current_feature)
        if cfg:
            cfg.missing_strategy = text
            self.controller.state.binning_configs[self.current_feature] = cfg
            self.run_binning()

    def on_plot_clicked(self, event):
        """右键点击添加切点"""
        if event.button() == Qt.MouseButton.RightButton:
            # 获取点击坐标
            pos = event.scenePos()
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            x_val = mouse_point.x()
            
            # 添加新切点
            # 这里的逻辑是：添加后立即触发重算
            current_splits = [l.value() for l in self.split_lines]
            current_splits.append(x_val)
            current_splits.sort()
            
            self.controller.update_splits(self.current_feature, current_splits)

    def on_mouse_moved(self, pos):
        mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
        x_val = mouse_point.x()
        if getattr(self, '_current_centers', None) is None:
            return
        centers = np.array(self._current_centers)
        bad_rates = np.array(self._current_bad_rates)
        if centers.size == 0:
            return
        idx = int(np.nanargmin(np.abs(centers - x_val)))
        row = self._current_metrics_df.iloc[idx]
        cfg = self.controller.state.binning_configs.get(self.current_feature)
        precision = (resolve_precision_step(cfg.params) if cfg else "auto")
        self.hover_label.setText(
            f"Bin: {format_bin_label(row['bin'], precision=precision)} | Count: {row['total']} | Bad Rate: {row['bad_rate']:.2%} | WOE: {row['woe']:.3f}"
        )
