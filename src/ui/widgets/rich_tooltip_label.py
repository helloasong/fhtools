"""富文本参数提示组件

提供带图标的富文本提示标签，支持延迟显示和 HTML 格式内容。
"""
from PyQt6.QtWidgets import QLabel, QWidget, QHBoxLayout, QApplication
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QFont, QHelpEvent


# 参数提示模板库
PARAM_TOOLTIPS = {
    'solver': """
        <h4>📘 求解器 (solver)</h4>
        <p>选择优化求解器类型：</p>
        <ul>
            <li><b>CP</b>: 约束编程，平衡速度和质量(推荐)</li>
            <li><b>MIP</b>: 混合整数规划，精确但较慢</li>
            <li><b>LS</b>: LocalSolver，适合大数据</li>
        </ul>
    """,
    'divergence': """
        <h4>📘 优化目标 (divergence)</h4>
        <p>选择散度度量优化目标：</p>
        <ul>
            <li><b>IV</b>: 信息值，风控领域最常用</li>
            <li><b>JS</b>: Jensen-Shannon，更平滑</li>
            <li><b>Hellinger</b>: 对尾部更敏感</li>
            <li><b>Triangular</b>: 计算最快</li>
        </ul>
    """,
    'min_bin_size': """
        <h4>📘 最小箱大小 (min_bin_size)</h4>
        <p>每箱最小样本占比，防止过拟合。</p>
        <p><b>📊 推荐值：</b></p>
        <ul>
            <li>大数据(&gt;10万): 0.02 (2%)</li>
            <li>中小数据: 0.05 (5%)</li>
        </ul>
        <p style='color:#e74c3c;'>⚠️ 设置过大可能导致无解</p>
    """,
    'max_n_prebins': """
        <h4>📘 预分箱数 (max_n_prebins)</h4>
        <p>预分箱阶段的最大箱数</p>
        <p>值越大精度越高但求解越慢</p>
        <p><b>📊 推荐值：</b> 10-50</p>
    """,
    'min_prebin_size': """
        <h4>📘 最小预分箱大小 (min_prebin_size)</h4>
        <p>预分箱阶段每箱最小样本占比</p>
        <p>用于控制预分箱的粒度</p>
    """,
    'monotonic_trend': """
        <h4>📘 单调性约束 (monotonic_trend)</h4>
        <p>强制分箱结果满足单调趋势：</p>
        <ul>
            <li><b>auto</b>: 自动检测趋势方向</li>
            <li><b>ascending</b>: 强制单调递增</li>
            <li><b>descending</b>: 强制单调递减</li>
            <li><b>peak</b>: 允许先增后减（凸形）</li>
            <li><b>valley</b>: 允许先减后增（凹形）</li>
            <li><b>none</b>: 无约束</li>
        </ul>
    """,
    'max_pvalue': """
        <h4>📘 最大P值 (max_pvalue)</h4>
        <p>统计检验的最大P值阈值</p>
        <p>用于合并相似箱，值越大合并越激进</p>
        <p><b>📊 推荐值：</b> 0.05 或 0.10</p>
    """,
    'max_pvalue_policy': """
        <h4>📘 P值策略 (max_pvalue_policy)</h4>
        <p>选择P值计算策略：</p>
        <ul>
            <li><b>all</b>: 考虑所有箱对</li>
            <li><b>consecutive</b>: 仅考虑相邻箱</li>
        </ul>
    """,
    'gamma': """
        <h4>📘 正则化参数 (gamma)</h4>
        <p>控制分箱复杂度的正则化系数</p>
        <p>值越大，倾向于使用更少的箱数</p>
        <p><b>📊 推荐值：</b> 0.001 - 0.1</p>
    """,
    'special_codes': """
        <h4>📘 特殊值 (special_codes)</h4>
        <p>指定需要单独分箱的特殊值</p>
        <p>如：-9999, 9999 等缺失值标记</p>
    """,
    'max_n_bins': """
        <h4>📘 最大箱数 (max_n_bins)</h4>
        <p>最终分箱结果的最大箱数</p>
        <p>包括特殊值箱和缺失值箱</p>
        <p><b>📊 推荐值：</b> 3-10</p>
    """,
}


def get_param_tooltip(param_name: str) -> str:
    """获取参数提示 HTML
    
    Args:
        param_name: 参数名称
        
    Returns:
        HTML 格式的提示内容，如果不存在则返回空字符串
    """
    return PARAM_TOOLTIPS.get(param_name, "")


class RichTooltipLabel(QLabel):
    """带图标的富文本提示标签
    
    显示 "文本 [?]" 格式，鼠标悬停 500ms 后显示 HTML 格式的提示框
    
    Attributes:
        TOOLTIP_STYLE: 提示框的样式表
        DEFAULT_DELAY: 延迟显示时间（毫秒）
    """
    
    TOOLTIP_STYLE = """
    QToolTip {
        background-color: #2c3e50;
        color: white;
        border: 1px solid #34495e;
        border-radius: 6px;
        padding: 10px;
        font-size: 12px;
        max-width: 400px;
        opacity: 255;
    }
    """
    
    LABEL_STYLE = """
    RichTooltipLabel {
        color: #333333;
    }
    RichTooltipLabel:hover {
        color: #2980b9;
    }
    """
    
    ICON_STYLE = """
    QLabel#tooltipIcon {
        color: #3498db;
        font-weight: bold;
        font-size: 11px;
        padding: 0 3px;
    }
    QLabel#tooltipIcon:hover {
        color: #2980b9;
        background-color: #ecf0f1;
        border-radius: 3px;
    }
    """
    
    DEFAULT_DELAY = 500  # 默认延迟 500ms
    
    def __init__(self, text: str, tooltip_html: str, parent=None, delay_ms: int = None):
        """初始化富文本提示标签
        
        Args:
            text: 显示文本
            tooltip_html: 提示内容 (HTML格式)
            parent: 父控件
            delay_ms: 延迟显示时间（毫秒），默认 500ms
        """
        super().__init__(parent)
        
        self._tooltip_html = tooltip_html
        self._delay_ms = delay_ms if delay_ms is not None else self.DEFAULT_DELAY
        self._tooltip_timer = None
        self._is_tooltip_visible = False
        
        # 设置显示文本（包含 [?] 图标）
        self._setup_display_text(text)
        
        # 设置样式
        self.setStyleSheet(self.LABEL_STYLE)
        
        # 设置提示属性
        self.setToolTipDuration(0)  # 不自动消失
        
        # 设置鼠标跟踪
        self.setMouseTracking(True)
        
        # 安装事件过滤器以支持富文本提示
        self._setup_tooltip()
    
    def _setup_display_text(self, text: str):
        """设置显示文本，包含 [?] 图标"""
        # 使用富文本格式显示文本和图标
        html = f'{text} <span style="color:#3498db;font-weight:bold;">[?]</span>'
        self.setText(html)
        self.setTextFormat(Qt.TextFormat.RichText)
    
    def _setup_tooltip(self):
        """设置富文本提示"""
        # 设置工具提示为 HTML 格式
        self.setToolTip(self._tooltip_html)
        
        # 初始化延迟计时器
        self._tooltip_timer = QTimer(self)
        self._tooltip_timer.setSingleShot(True)
        self._tooltip_timer.timeout.connect(self._show_tooltip)
        self._tooltip_timer.setInterval(self._delay_ms)
    
    def _show_tooltip(self):
        """显示提示框"""
        if self._tooltip_html:
            # 获取全局光标位置
            pos = QCursor.pos()
            # 在光标位置显示提示
            QToolTip.showText(pos, self._tooltip_html, self)
            self._is_tooltip_visible = True
    
    def enterEvent(self, event):
        """鼠标进入事件"""
        # 启动延迟计时器
        if self._tooltip_timer and not self._is_tooltip_visible:
            self._tooltip_timer.start()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        # 停止计时器
        if self._tooltip_timer:
            self._tooltip_timer.stop()
        
        # 隐藏提示
        if self._is_tooltip_visible:
            QToolTip.hideText()
            self._is_tooltip_visible = False
        
        super().leaveEvent(event)
    
    def set_tooltip_html(self, tooltip_html: str):
        """设置新的提示内容
        
        Args:
            tooltip_html: 新的 HTML 格式提示内容
        """
        self._tooltip_html = tooltip_html
        self.setToolTip(tooltip_html)


class RichTooltipHelper(QLabel):
    """辅助图标类
    
    只显示 [?] 图标，用于为其他控件添加富文本提示。
    可以单独使用，也可以与目标控件放在同一布局中。
    
    使用示例:
        >>> spinbox = QSpinBox()
        >>> helper = RichTooltipHelper(get_param_tooltip('max_n_bins'))
        >>> layout = QHBoxLayout()
        >>> layout.addWidget(spinbox)
        >>> layout.addWidget(helper)
    """
    
    ICON_STYLE = """
    RichTooltipHelper {
        color: #3498db;
        font-weight: bold;
        font-size: 11px;
        padding: 2px 5px;
        border-radius: 3px;
    }
    RichTooltipHelper:hover {
        color: #2980b9;
        background-color: #ecf0f1;
    }
    """
    
    TOOLTIP_STYLE = """
    QToolTip {
        background-color: #2c3e50;
        color: white;
        border: 1px solid #34495e;
        border-radius: 6px;
        padding: 10px;
        font-size: 12px;
        max-width: 400px;
    }
    """
    
    DEFAULT_DELAY = 500  # 默认延迟 500ms
    
    def __init__(self, tooltip_html: str, parent=None, delay_ms: int = None):
        """初始化辅助图标
        
        Args:
            tooltip_html: 提示内容 (HTML格式)
            parent: 父控件
            delay_ms: 延迟显示时间（毫秒），默认 500ms
        """
        super().__init__("[?]", parent)
        
        self._tooltip_html = tooltip_html
        self._delay_ms = delay_ms if delay_ms is not None else self.DEFAULT_DELAY
        self._tooltip_timer = None
        self._is_tooltip_visible = False
        
        # 设置样式
        self.setStyleSheet(self.ICON_STYLE)
        
        # 设置固定大小
        self.setFixedWidth(24)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 设置光标样式
        self.setCursor(Qt.CursorShape.WhatsThisCursor)
        
        # 设置鼠标跟踪
        self.setMouseTracking(True)
        
        # 安装提示
        self._setup_tooltip()
    
    def _setup_tooltip(self):
        """设置富文本提示"""
        # 设置工具提示
        self.setToolTip(self._tooltip_html)
        self.setToolTipDuration(0)
        
        # 初始化延迟计时器
        self._tooltip_timer = QTimer(self)
        self._tooltip_timer.setSingleShot(True)
        self._tooltip_timer.timeout.connect(self._show_tooltip)
        self._tooltip_timer.setInterval(self._delay_ms)
    
    def _show_tooltip(self):
        """显示提示框"""
        if self._tooltip_html:
            # 获取控件下方的位置
            pos = self.mapToGlobal(self.rect().bottomLeft())
            # 稍微向下偏移，避免遮挡图标
            pos.setY(pos.y() + 5)
            QToolTip.showText(pos, self._tooltip_html, self)
            self._is_tooltip_visible = True
    
    def enterEvent(self, event):
        """鼠标进入事件"""
        if self._tooltip_timer and not self._is_tooltip_visible:
            self._tooltip_timer.start()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        if self._tooltip_timer:
            self._tooltip_timer.stop()
        
        if self._is_tooltip_visible:
            QToolTip.hideText()
            self._is_tooltip_visible = False
        
        super().leaveEvent(event)
    
    def set_tooltip_html(self, tooltip_html: str):
        """设置新的提示内容
        
        Args:
            tooltip_html: 新的 HTML 格式提示内容
        """
        self._tooltip_html = tooltip_html
        self.setToolTip(tooltip_html)


class RichTooltipWrapper(QWidget):
    """包装器类：将任意控件与富文本提示组合
    
    将目标控件和提示图标水平排列，自动处理布局
    
    使用示例:
        >>> spinbox = QSpinBox()
        >>> wrapper = RichTooltipWrapper(
        ...     spinbox,
        ...     get_param_tooltip('max_n_bins')
        ... )
        >>> layout.addWidget(wrapper)  # 而不是直接添加 spinbox
    """
    
    def __init__(self, widget: QWidget, tooltip_html: str, 
                 label_text: str = None, spacing: int = 5, parent=None):
        """初始化包装器
        
        Args:
            widget: 需要添加提示的目标控件
            tooltip_html: 提示内容 (HTML格式)
            label_text: 如果提供，则在控件前添加标签文本
            spacing: 控件之间的间距
            parent: 父控件
        """
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(spacing)
        
        # 添加标签（可选）
        if label_text:
            label = QLabel(label_text)
            layout.addWidget(label)
        
        # 添加目标控件
        layout.addWidget(widget)
        
        # 添加提示图标
        helper = RichTooltipHelper(tooltip_html)
        layout.addWidget(helper)
        
        # 添加弹性空间
        layout.addStretch()
        
        # 保存引用
        self._widget = widget
        self._helper = helper
    
    def widget(self) -> QWidget:
        """获取被包装的目标控件"""
        return self._widget
    
    def helper(self) -> RichTooltipHelper:
        """获取提示图标控件"""
        return self._helper


# 便捷函数
def create_labeled_widget(widget: QWidget, tooltip_key: str, 
                          label_text: str = None) -> RichTooltipWrapper:
    """创建带标签和提示的控件包装器
    
    Args:
        widget: 目标控件
        tooltip_key: 参数名称，用于从模板库获取提示内容
        label_text: 标签文本，如果为 None 则使用 tooltip_key
        
    Returns:
        RichTooltipWrapper 实例
    """
    if label_text is None:
        label_text = tooltip_key
    
    tooltip_html = get_param_tooltip(tooltip_key)
    return RichTooltipWrapper(widget, tooltip_html, label_text)


def add_tooltip_to_widget(widget: QWidget, tooltip_html: str, 
                          layout: QHBoxLayout = None) -> RichTooltipHelper:
    """为现有控件添加提示图标
    
    Args:
        widget: 目标控件
        tooltip_html: 提示内容 (HTML格式)
        layout: 如果提供，则自动将图标添加到布局中
        
    Returns:
        RichTooltipHelper 实例
    """
    helper = RichTooltipHelper(tooltip_html)
    
    if layout is not None:
        # 找到 widget 在布局中的位置，在其后插入 helper
        index = layout.indexOf(widget)
        if index >= 0:
            layout.insertWidget(index + 1, helper)
        else:
            layout.addWidget(helper)
    
    return helper


# 为了兼容性，保留旧名称
TooltipLabel = RichTooltipLabel
TooltipHelper = RichTooltipHelper
