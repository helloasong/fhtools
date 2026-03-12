"""求解状态显示组件

提供求解状态指示器和信息面板，支持多种状态显示和详细信息展示。
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGridLayout, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from typing import Dict, Any, Optional


class SolveStatusIndicator(QLabel):
    """简洁状态指示器 (仅图标和文字)
    
    用于显示当前求解状态的简洁指示器，包含状态图标和文字描述。
    
    Attributes:
        STATUS_COLORS: 状态颜色映射表
        STATUS_ICONS: 状态图标映射表 (Unicode)
        STATUS_TEXTS: 状态文本映射表
    """
    
    STATUS_COLORS = {
        'solving': '#f39c12',
        'optimal': '#27ae60',
        'feasible': '#3498db',
        'infeasible': '#e74c3c',
        'timeout': '#95a5a6',
        'unknown': '#bdc3c7',
    }
    
    STATUS_ICONS = {
        'solving': '🟡',
        'optimal': '🟢',
        'feasible': '🔵',
        'infeasible': '🔴',
        'timeout': '⚫',
        'unknown': '⚪',
    }
    
    STATUS_TEXTS = {
        'solving': '求解中...',
        'optimal': '最优解',
        'feasible': '可行解',
        'infeasible': '无解',
        'timeout': '超时',
        'unknown': '未知',
    }
    
    def __init__(self, parent=None):
        """初始化状态指示器
        
        Args:
            parent: 父窗口部件
        """
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_status('unknown')
        
    def set_status(self, status: str, message: str = None):
        """设置状态
        
        更新状态指示器的图标、文字和颜色。
        
        Args:
            status: 状态常量，必须是 STATUS_COLORS 中的键
            message: 自定义消息 (可选)，如果提供则覆盖默认文本
        """
        icon = self.STATUS_ICONS.get(status, '⚪')
        text = message or self.STATUS_TEXTS.get(status, '未知')
        color = self.STATUS_COLORS.get(status, '#bdc3c7')
        
        self.setText(f"{icon} {text}")
        self.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px;")


class SolveStatusWidget(QFrame):
    """完整状态显示组件 (带信息面板)
    
    提供完整的求解状态显示，包括状态指示器和详细信息面板。
    支持简洁模式和详细模式切换。
    
    Attributes:
        SOLVING: 求解中状态常量
        OPTIMAL: 最优解状态常量
        FEASIBLE: 可行解状态常量
        INFEASIBLE: 无解状态常量
        TIMEOUT: 超时状态常量
        UNKNOWN: 未知状态常量
        
        STATUS_COLORS: 状态颜色映射表
        STATUS_ICONS: 状态图标映射表 (Unicode)
        STATUS_TEXTS: 状态文本映射表
        
        INFO_LABELS: 信息字段显示标签映射表
    """
    
    # 状态常量
    SOLVING = 'solving'
    OPTIMAL = 'optimal'
    FEASIBLE = 'feasible'
    INFEASIBLE = 'infeasible'
    TIMEOUT = 'timeout'
    UNKNOWN = 'unknown'
    
    # 状态颜色
    STATUS_COLORS = {
        'solving': '#f39c12',
        'optimal': '#27ae60',
        'feasible': '#3498db',
        'infeasible': '#e74c3c',
        'timeout': '#95a5a6',
        'unknown': '#bdc3c7',
    }
    
    # 状态图标 (Unicode)
    STATUS_ICONS = {
        'solving': '🟡',
        'optimal': '🟢',
        'feasible': '🔵',
        'infeasible': '🔴',
        'timeout': '⚫',
        'unknown': '⚪',
    }
    
    # 状态文本
    STATUS_TEXTS = {
        'solving': '求解中...',
        'optimal': '最优解',
        'feasible': '可行解',
        'infeasible': '无解',
        'timeout': '超时',
        'unknown': '未知',
    }
    
    # 信息字段显示标签
    INFO_LABELS = {
        'solve_time': '求解时间',
        'objective_value': '目标函数值',
        'n_iterations': '迭代次数',
        'n_constraints_violated': '约束违反',
    }
    
    # 样式表
    WIDGET_STYLE = """
        SolveStatusWidget {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 10px;
        }
    """
    
    def __init__(self, parent=None, detailed: bool = True):
        """初始化状态显示组件
        
        Args:
            parent: 父窗口部件
            detailed: 是否显示详细信息面板，默认为 True
        """
        super().__init__(parent)
        self.detailed = detailed
        self._current_status = self.UNKNOWN
        self._current_info = {}
        self._init_ui()
        
        # 初始状态为 UNKNOWN，隐藏组件
        self.setVisible(False)
        
    def _init_ui(self):
        """初始化界面"""
        # 设置样式
        self.setStyleSheet(self.WIDGET_STYLE)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)
        
        # ===== 状态指示器区域 =====
        status_layout = QHBoxLayout()
        status_layout.setSpacing(8)
        
        # 状态标签标题
        status_title = QLabel("求解状态")
        status_title.setStyleSheet("font-weight: bold; color: #495057;")
        status_layout.addWidget(status_title)
        
        # 状态指示器
        self.status_indicator = SolveStatusIndicator()
        status_layout.addWidget(self.status_indicator)
        status_layout.addStretch()
        
        main_layout.addLayout(status_layout)
        
        # ===== 详细信息面板 (可选) =====
        if self.detailed:
            # 分隔线
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setStyleSheet("color: #dee2e6;")
            main_layout.addWidget(separator)
            
            # 信息面板布局
            info_layout = QGridLayout()
            info_layout.setSpacing(8)
            info_layout.setColumnStretch(1, 1)
            
            # 创建信息标签
            self.info_labels = {}
            self.info_values = {}
            
            row = 0
            for key, label_text in self.INFO_LABELS.items():
                # 标签名
                label = QLabel(f"{label_text}:")
                label.setStyleSheet("color: #6c757d; font-size: 12px;")
                info_layout.addWidget(label, row, 0)
                
                # 值标签
                value_label = QLabel("-")
                value_label.setStyleSheet("color: #212529; font-size: 12px;")
                info_layout.addWidget(value_label, row, 1)
                
                self.info_labels[key] = label
                self.info_values[key] = value_label
                row += 1
            
            main_layout.addLayout(info_layout)
        
        main_layout.addStretch()
        
    def set_status(self, status: str, message: str = None):
        """设置求解状态
        
        更新状态指示器的显示，并保存当前状态。
        根据状态自动显示或隐藏组件：
        - UNKNOWN 状态：隐藏组件（不占用空间）
        - 其他状态：显示组件
        
        Args:
            status: 状态常量，必须是类中定义的状态常量之一
            message: 自定义消息 (可选)，如果提供则覆盖默认文本
        """
        self._current_status = status
        self.status_indicator.set_status(status, message)
        
        # 根据状态自动显示/隐藏
        if status == self.UNKNOWN:
            self.setVisible(False)  # 未知状态隐藏
        else:
            self.setVisible(True)   # 其他状态显示
        
    def set_info(self, info: Dict[str, Any]):
        """设置求解信息
        
        更新详细信息面板的显示内容。
        
        Args:
            info: 包含以下字段的字典:
                - solve_time: 求解时间(秒)
                - objective_value: 目标函数值
                - n_iterations: 迭代次数
                - n_constraints_violated: 约束违反数
                或其他自定义字段
        """
        if not self.detailed:
            return
            
        self._current_info.update(info)
        
        # 格式化并显示各个字段
        for key, value in info.items():
            if key in self.info_values:
                formatted_value = self._format_value(key, value)
                self.info_values[key].setText(formatted_value)
                
    def _format_value(self, key: str, value: Any) -> str:
        """格式化值显示
        
        根据字段类型格式化值，使其更易读。
        
        Args:
            key: 字段名
            value: 字段值
            
        Returns:
            格式化后的字符串
        """
        if value is None:
            return "-"
            
        if key == 'solve_time':
            # 求解时间显示为秒，保留2位小数
            return f"{value:.2f} 秒"
        elif key == 'objective_value':
            # 目标函数值保留3位小数
            return f"{value:.3f} (IV)"
        elif key in ['n_iterations', 'n_constraints_violated']:
            # 整数类型直接显示
            return str(int(value))
        else:
            # 其他类型直接转为字符串
            return str(value)
            
    def clear(self):
        """清空状态
        
        将状态重置为未知，并清空所有信息字段。
        """
        self._current_status = self.UNKNOWN
        self._current_info = {}
        self.status_indicator.set_status(self.UNKNOWN)
        
        if self.detailed:
            for value_label in self.info_values.values():
                value_label.setText("-")
                
    def get_status(self) -> str:
        """获取当前状态
        
        Returns:
            当前状态常量字符串
        """
        return self._current_status
        
    def get_info(self) -> Dict[str, Any]:
        """获取当前信息
        
        Returns:
            当前信息字典的副本
        """
        return self._current_info.copy()
        
    def is_solving(self) -> bool:
        """检查是否正在求解中
        
        Returns:
            如果状态为求解中返回 True，否则返回 False
        """
        return self._current_status == self.SOLVING
        
    def is_completed(self) -> bool:
        """检查是否已完成求解
        
        Returns:
            如果状态为最优解、可行解或超时而求解完成返回 True，
            否则返回 False
        """
        return self._current_status in [
            self.OPTIMAL, 
            self.FEASIBLE, 
            self.TIMEOUT
        ]
        
    def is_failed(self) -> bool:
        """检查是否求解失败
        
        Returns:
            如果状态为无解返回 True，否则返回 False
        """
        return self._current_status == self.INFEASIBLE
