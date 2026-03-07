from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLabel, QSplitter,
    QComboBox, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QAbstractScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QGridLayout, QGraphicsDropShadowEffect
import pyqtgraph as pg
import numpy as np
import pandas as pd

from src.controllers.project_controller import ProjectController
from src.data.models import ProjectState, VariableStats, BinningMetrics, BinningConfig
from src.services.recommendation_service import recommend_method, method_to_cn
from src.utils.formatting import format_bin_label, parse_precision_step, resolve_precision_step


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
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：变量列表 + 搜索（简化为列表）
        self.feature_list = QListWidget()
        self.feature_list.itemClicked.connect(self.on_feature_selected)

        # 右侧：紧凑信息 + 小图 + 配置
        right = QWidget()
        right_layout = QVBoxLayout(right)
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

        # 中部：分布图（小型）
        self.dist_plot = pg.PlotWidget(title="分布图")
        self._compact_plot(self.dist_plot, height=200)
        self._setup_bottom_anchor(self.dist_plot)
        self.dist_card = self._wrap_card(self.dist_plot)

        # 中部：分箱图（小型）：柱状=样本数，折线=Bad Rate
        self.bin_plot = pg.PlotWidget(title="分箱图")
        self._compact_plot(self.bin_plot, height=220)
        self._setup_bottom_anchor(self.bin_plot)
        self.bin_plot.scene().sigMouseMoved.connect(self.on_mouse_moved)
        self.bin_card = self._wrap_card(self.bin_plot)

        # 分箱明细表
        self.bin_table = QTableWidget()
        self.bin_table.setColumnCount(10)
        self.bin_table.setHorizontalHeaderLabels(["范围", "样本数", "占比", "坏样本数", "坏样本率", "好样本数", "好样本率", "WOE", "IV", "Lift"])
        # 移除固定高度，按内容自适应
        self.bin_table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.bin_table_card = self._wrap_card(self.bin_table)

        # 下部：分箱配置（紧凑工具栏）
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        self.method_combo = QComboBox()
        method_map = [
            ("等频分箱", "equal_freq"),
            ("等距分箱", "equal_width"),
            ("决策树分箱", "decision_tree"),
            ("卡方分箱", "chi_merge"),
            ("Best-KS 分箱", "best_ks"),
            ("自定义切点", "manual"),
        ]
        for label, key in method_map:
            self.method_combo.addItem(label, key)
        self.n_bins_spin = QSpinBox(); self.n_bins_spin.setRange(2, 20); self.n_bins_spin.setValue(5)
        self.n_bins_spin.setPrefix("箱数：")
        self.missing_combo = QComboBox();
        for label, key in [("单独成箱", "separate"), ("忽略", "ignore"), ("归并", "merge")]:
            self.missing_combo.addItem(label, key)

        self.precision_mode_combo = QComboBox()
        for label, key in [("自动", "auto"), ("小数点后几位", "decimal"), ("整数位（前几位）", "integer")]:
            self.precision_mode_combo.addItem(label, key)
        self.precision_digits_spin = QSpinBox()
        self.precision_digits_spin.setRange(0, 12)
        self.precision_digits_spin.setValue(0)
        self.run_btn = QPushButton("运行")
        self.save_btn = QPushButton("确认并保存")
        toolbar.addWidget(QLabel("分箱方法：")); toolbar.addWidget(self.method_combo)
        toolbar.addWidget(self.n_bins_spin)
        toolbar.addWidget(QLabel("缺失值策略：")); toolbar.addWidget(self.missing_combo)
        toolbar.addWidget(QLabel("边界精度："))
        toolbar.addWidget(self.precision_mode_combo)
        toolbar.addWidget(self.precision_digits_spin)
        toolbar.addWidget(self.run_btn); toolbar.addWidget(self.save_btn)
        toolbar.addStretch()

        # 汇总到右侧布局
        right_layout.addWidget(self.stats_panel)
        right_layout.addWidget(self.target_label)
        right_layout.addWidget(self.recommend_label)
        right_layout.addWidget(self.dist_card)
        right_layout.addWidget(self.bin_card)
        right_layout.addLayout(toolbar)
        right_layout.addWidget(self.bin_table_card)

        splitter.addWidget(self.feature_list)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)

        # 事件绑定
        self.run_btn.clicked.connect(self.run_binning)
        self.missing_combo.currentTextChanged.connect(self.on_missing_strategy_changed)
        self.precision_mode_combo.currentIndexChanged.connect(self._update_precision_inputs)
        self._update_precision_inputs()

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

    def on_project_updated(self, state: ProjectState):
        self.feature_list.clear()
        if state.feature_cols:
            self.feature_list.addItems(state.feature_cols)

    def on_feature_selected(self, item):
        self.current_feature = item.text()
        self.refresh_stats_and_plots()
        # 如果已有分箱结果，渲染，否则默认运行一次等频
        if self.current_feature in self.controller.state.binning_results:
            metrics = self.controller.state.binning_results[self.current_feature]
            cfg = self.controller.state.binning_configs[self.current_feature]
            self._apply_display_config(cfg)
            self.render_binning(metrics, cfg)
        else:
            self.run_binning()

    def _apply_display_config(self, cfg: BinningConfig):
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
        # 建议
        target = self.controller.df[self.controller.state.target_col] if self.controller.state and self.controller.state.target_col else None
        rec = recommend_method(self.controller.df[self.current_feature], target)
        self.recommend_label.setText(f"分箱建议：{method_to_cn(rec)}")
        try:
            idx = self.method_combo.findData(rec)
            if idx != -1:
                self.method_combo.setCurrentIndex(idx)
        except Exception:
            pass
        # 分布图
        self.dist_plot.clear()
        series = self.controller.df[self.current_feature].dropna()
        if pd.api.types.is_numeric_dtype(series):
            y, x = np.histogram(series, bins=20)
            width = x[1] - x[0]
            x_centers = x[:-1] + width/2
            bar = pg.BarGraphItem(x=x_centers, height=y, width=width*0.9, brush=pg.mkBrush(120, 160, 220, 160))
            self.dist_plot.addItem(bar)
            try:
                xmin, xmax = float(x.min()), float(x.max())
                ymax = float(y.max()) if y.size else 1.0
                self.dist_plot.getPlotItem().setRange(xRange=(xmin, xmax), yRange=(0, ymax * 1.05), padding=0.0)
            except Exception:
                pass
        else:
            counts = series.value_counts().head(20)
            x = np.arange(len(counts))
            bar = pg.BarGraphItem(x=x, height=counts.values, width=0.6, brush=pg.mkBrush(160, 200, 120, 160))
            self.dist_plot.addItem(bar)
            try:
                n = len(counts)
                ymax = float(counts.values.max()) if n else 1.0
                self.dist_plot.getPlotItem().setRange(xRange=(-0.5, n - 0.5), yRange=(0, ymax * 1.05), padding=0.0)
            except Exception:
                pass

    def run_binning(self):
        if not self.current_feature: return
        # 以中文选项映射到内部方法键
        method_key = self.method_combo.currentData()
        method = method_key if method_key else self.method_combo.currentText()
        supervised = method in ['decision_tree', 'chi_merge', 'best_ks']
        if supervised and not (self.controller.state and self.controller.state.target_col):
            QMessageBox.warning(self, "提示", "未设置目标变量，当前建议为监督分箱，请先设置目标变量")
            return
        n_bins = self.n_bins_spin.value()
        kwargs = {'n_bins': n_bins}
        if method in ['decision_tree', 'chi_merge']:
            kwargs = {'max_leaf_nodes': n_bins, 'max_bins': n_bins}
        if method == 'best_ks':
            kwargs = {'max_bins': n_bins, 'initial_bins': 64}
        kwargs['boundary_precision_mode'] = self.precision_mode_combo.currentData()
        kwargs['boundary_precision_digits'] = int(self.precision_digits_spin.value())
        self.controller.run_binning(self.current_feature, method=method, **kwargs)

    def on_binning_finished(self, feature: str, metrics: BinningMetrics):
        if feature != self.current_feature: return
        cfg = self.controller.state.binning_configs[feature]
        self._apply_display_config(cfg)
        self.render_binning(metrics, cfg)

    def render_binning(self, metrics: BinningMetrics, cfg: BinningConfig):
        precision = resolve_precision_step(cfg.params)
        splits = cfg.splits
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
                centers.append((b.left + b.right) / 2)
            else:
                try:
                    txt = str(b).replace('(', '').replace(']', '')
                    parts = txt.split(',')
                    centers.append((float(parts[0]) + float(parts[1])) / 2)
                except Exception:
                    centers.append(np.nan)
            bad_rates.append(row['bad_rate'])
        centers = np.array(centers)
        mask = ~np.isnan(centers)
        curve = pg.PlotCurveItem(x=centers[mask], y=np.array(bad_rates)[mask], pen=pg.mkPen('b', width=2))
        self.bin_plot.addItem(curve)

        for split in splits:
            if np.isinf(split):
                continue
            line = pg.InfiniteLine(pos=split, movable=True, angle=90, pen=pg.mkPen('r', width=2, style=Qt.PenStyle.DashLine))
            line.sigPositionChangeFinished.connect(self.on_split_dragged)
            self.bin_plot.addItem(line)
            self.split_lines.append(line)

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

        # 根据内容自适应最大高度（尽量显示所有行）
        try:
            self.bin_table.resizeRowsToContents()
            header_h = self.bin_table.horizontalHeader().height()
            rows_h = sum(self.bin_table.rowHeight(i) for i in range(self.bin_table.rowCount()))
            margins = 24
            self.bin_table.setMaximumHeight(header_h + rows_h + margins)
        except Exception:
            pass

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
