import pyqtgraph as pg
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt


class CrossBinningHeatmap(QWidget):
    """二维决策矩阵热力图组件

    使用 PyQtGraph 的 ImageItem 实现，支持鼠标悬停提示。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 标题
        self.title_label = QLabel("二维决策矩阵")
        self.title_label.setStyleSheet("font-weight: bold; color: #333;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # 热力图
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("w")
        self.plot_widget.setMinimumHeight(280)
        self.plot_widget.setMaximumHeight(400)
        self.plot_widget.getPlotItem().layout.setContentsMargins(0, 0, 0, 0)

        self.image_item = pg.ImageItem()
        self.plot_widget.addItem(self.image_item)

        # 颜色条
        self.color_bar = pg.ColorBarItem(
            values=(0, 1),
            colorMap=pg.colormap.get("CET-D1"),
        )
        self.color_bar.setImageItem(self.image_item)

        layout.addWidget(self.plot_widget)

        # 提示标签
        self.hint_label = QLabel("鼠标悬停查看详细数据")
        self.hint_label.setStyleSheet("color: #888; font-size: 11px;")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.hint_label)

    def set_data(self, heatmap_data):
        """设置热力图数据

        Args:
            heatmap_data: CrossBinningHeatmapData
        """
        self._data = heatmap_data
        matrix = heatmap_data.bad_rate_matrix.values.astype(float)

        # 用 NaN 填充缺失值
        matrix = np.nan_to_num(matrix, nan=0.0)

        # 归一化到 0-1 范围用于颜色映射
        vmax = np.nanmax(matrix) if np.nanmax(matrix) > 0 else 1.0
        vmin = np.nanmin(matrix) if np.nanmin(matrix) < vmax else 0.0
        if vmax == vmin:
            normalized = np.zeros_like(matrix)
        else:
            normalized = (matrix - vmin) / (vmax - vmin)

        self.image_item.setImage(
            normalized,
            levels=(0, 1),
        )

        # 更新标题
        self.title_label.setText(
            f"决策矩阵: {heatmap_data.feature_y} × {heatmap_data.feature_x}"
        )

        # 设置坐标轴标签（显示箱标签）
        nx = len(heatmap_data.x_labels)
        ny = len(heatmap_data.y_labels)

        self.plot_widget.getAxis("bottom").setTicks(
            [[(i + 0.5, label) for i, label in enumerate(heatmap_data.x_labels)]]
        )
        self.plot_widget.getAxis("left").setTicks(
            [[(i + 0.5, label) for i, label in enumerate(heatmap_data.y_labels)]]
        )

        self.plot_widget.setXRange(0, nx)
        self.plot_widget.setYRange(0, ny)

        # 隐藏默认的自动缩放
        self.plot_widget.getViewBox().setAspectLocked(False)

        # 颜色条范围
        self.color_bar.setLevels((vmin, vmax))
