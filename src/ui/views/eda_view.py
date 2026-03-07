from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
    QTableWidget, QTableWidgetItem, QLabel, QSplitter
)
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import numpy as np
import pandas as pd
from src.controllers.project_controller import ProjectController
from src.data.models import ProjectState, VariableStats
from src.services.recommendation_service import recommend_method, method_to_cn

class EDAView(QWidget):
    """
    EDA 视图：展示变量列表、统计信息和分布图。
    """
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        layout = QHBoxLayout(self)
        
        # 使用 QSplitter 实现左右拖动调整大小
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 1. 左侧：变量列表
        self.feature_list = QListWidget()
        self.feature_list.itemClicked.connect(self.on_feature_selected)
        
        # 2. 右侧：详细信息 + 图表
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 2.1 统计表格
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.stats_table.horizontalHeader().setStretchLastSection(True)
        self.stats_table.setMaximumHeight(200)
        
        # 2.2 分布图 (PyQtGraph)
        self.plot_widget = pg.PlotWidget(title="分布图")
        self.plot_widget.setBackground('w') # 白色背景
        self._setup_bottom_anchor(self.plot_widget)
        
        right_layout.addWidget(QLabel("变量统计"))
        right_layout.addWidget(self.stats_table)
        self.recommend_label = QLabel("")
        right_layout.addWidget(self.recommend_label)
        right_layout.addWidget(QLabel("分布图"))
        right_layout.addWidget(self.plot_widget)
        
        splitter.addWidget(self.feature_list)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 2) # 右侧占更大比例
        
        layout.addWidget(splitter)

    def setup_connections(self):
        self.controller.project_updated.connect(self.on_project_updated)

    def on_project_updated(self, state: ProjectState):
        """项目更新时刷新变量列表"""
        self.feature_list.clear()
        if state.feature_cols:
            self.feature_list.addItems(state.feature_cols)

    def on_feature_selected(self, item):
        """选中变量时刷新右侧详情"""
        feature_name = item.text()
        state = self.controller.state
        if not state or feature_name not in state.variable_stats:
            return
            
        stats = state.variable_stats[feature_name]
        self.update_stats_table(stats)
        self.update_recommendation(feature_name)
        self.update_plot(feature_name)

    def update_stats_table(self, stats: VariableStats):
        """更新统计表"""
        metrics = [
            ("Type", stats.dtype),
            ("Count", str(stats.n_samples)),
            ("Missing", f"{stats.n_missing} ({stats.missing_pct:.2%})"),
            ("Unique", str(stats.n_unique)),
            ("Min", f"{stats.min_val:.4f}" if stats.min_val is not None else "-"),
            ("Max", f"{stats.max_val:.4f}" if stats.max_val is not None else "-"),
            ("Mean", f"{stats.mean_val:.4f}" if stats.mean_val is not None else "-"),
            ("Std", f"{stats.std_val:.4f}" if stats.std_val is not None else "-"),
        ]
        
        self.stats_table.setRowCount(len(metrics))
        for i, (k, v) in enumerate(metrics):
            self.stats_table.setItem(i, 0, QTableWidgetItem(k))
            self.stats_table.setItem(i, 1, QTableWidgetItem(v))

    def update_plot(self, feature_name: str):
        """绘制分布直方图"""
        self.plot_widget.clear()
        df = self.controller.df
        if df is None:
            return
            
        series = df[feature_name].dropna()
        
        # 简单判断数值型还是类别型
        if pd.api.types.is_numeric_dtype(series):
            # 绘制直方图
            y, x = np.histogram(series, bins=20)
            # x 是边界，y 是频数
            # 使用 BarGraphItem
            # x[:-1] 是每个柱子的左边界，width 是宽度
            width = x[1] - x[0]
            # 为了让柱子居中，x_left + width/2
            x_centers = x[:-1] + width/2
            
            bar_item = pg.BarGraphItem(x=x_centers, height=y, width=width * 0.9, brush='b')
            self.plot_widget.addItem(bar_item)
            self.plot_widget.setTitle(f"直方图：{feature_name}")
            try:
                xmin, xmax = float(x.min()), float(x.max())
                ymax = float(y.max()) if y.size else 1.0
                self.plot_widget.getPlotItem().setRange(xRange=(xmin, xmax), yRange=(0, ymax * 1.05), padding=0.0)
            except Exception:
                pass
        else:
            # 类别型：绘制频数条形图
            counts = series.value_counts().head(20) # 只取前20个
            x = np.arange(len(counts))
            y = counts.values
            
            bar_item = pg.BarGraphItem(x=x, height=y, width=0.6, brush='g')
            self.plot_widget.addItem(bar_item)
            
            # 设置 x 轴标签 (pyqtgraph 处理字符串轴比较麻烦，这里简化处理)
            # 实际商业级需要自定义 AxisItem
            self.plot_widget.setTitle(f"类别分布（Top20）：{feature_name}")
            try:
                n = len(counts)
                ymax = float(counts.values.max()) if n else 1.0
                self.plot_widget.getPlotItem().setRange(xRange=(-0.5, n - 0.5), yRange=(0, ymax * 1.05), padding=0.0)
            except Exception:
                pass

    def update_recommendation(self, feature_name: str):
        target = self.controller.df[self.controller.state.target_col] if self.controller.state and self.controller.state.target_col else None
        rec = recommend_method(self.controller.df[feature_name], target)
        self.recommend_label.setText(f"分箱建议：{method_to_cn(rec)}")

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
