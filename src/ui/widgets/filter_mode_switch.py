"""
指标过滤模式三态切换组件

三个互斥按钮组成的切换器，类似 QButtonGroup 但视觉更直观。
当前选中项高亮显示，未选中项为普通样式。
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal

from src.data.models import FilterMode


class FilterModeSwitch(QWidget):
    """指标过滤模式三态切换组件

    Signals:
        mode_changed(FilterMode): 用户切换模式时发射
    """
    mode_changed = pyqtSignal(object)  # FilterMode

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_mode = FilterMode.GLOBAL
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        self.btn_global = QPushButton("🌐 使用全局规则")
        self.btn_custom = QPushButton("⚙️ 使用自定义规则")
        self.btn_disabled = QPushButton("🚫 不应用过滤")

        self.btn_global.setCheckable(True)
        self.btn_custom.setCheckable(True)
        self.btn_disabled.setCheckable(True)

        self.btn_global.clicked.connect(lambda: self._on_clicked(FilterMode.GLOBAL))
        self.btn_custom.clicked.connect(lambda: self._on_clicked(FilterMode.CUSTOM))
        self.btn_disabled.clicked.connect(lambda: self._on_clicked(FilterMode.DISABLED))

        layout.addWidget(self.btn_global)
        layout.addWidget(self.btn_custom)
        layout.addWidget(self.btn_disabled)
        layout.addStretch()

        self._update_style()

    def set_mode(self, mode: FilterMode):
        """设置当前模式（不发射信号）"""
        self._current_mode = mode
        self._update_style()

    def get_mode(self) -> FilterMode:
        return self._current_mode

    def _on_clicked(self, mode: FilterMode):
        if self._current_mode != mode:
            self._current_mode = mode
            self._update_style()
            self.mode_changed.emit(mode)

    def _update_style(self):
        """更新按钮样式以反映当前选中状态"""
        buttons = {
            FilterMode.GLOBAL: self.btn_global,
            FilterMode.CUSTOM: self.btn_custom,
            FilterMode.DISABLED: self.btn_disabled,
        }
        for mode, btn in buttons.items():
            checked = (mode == self._current_mode)
            btn.setChecked(checked)
            if checked:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #4A90D9;
                        color: white;
                        border: 1px solid #3A7BC8;
                        border-radius: 8px;
                        padding: 6px 14px;
                        font-size: 12px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: linear-gradient(to bottom, #F4F7FB, #E8EEF6);
                        border: 1px solid #C9D6EA;
                        border-radius: 8px;
                        padding: 6px 14px;
                        color: #666;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background: linear-gradient(to bottom, #E8EEF6, #D9E4F5);
                        color: #333;
                    }
                """)
