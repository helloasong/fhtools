"""
单条件行编辑器（紧凑美化版）

参考现代 Web Query Builder 设计：
- 紧凑内边距，减少留白
- Unicode 符号替代 emoji，避免显示异常
- 变量选择后实时显示列统计信息，辅助填写条件值
- 左侧色条标识条件类型
"""

from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QComboBox, QLineEdit, QPushButton,
    QCheckBox, QLabel, QStackedWidget, QCompleter
)
from PyQt6.QtCore import pyqtSignal, Qt

from src.data.models import FilterCondition
from src.core.filtering.constants import OPERATORS_BY_TYPE


class FilterConditionRow(QWidget):
    """单条件行编辑器（紧凑版）"""

    condition_saved = pyqtSignal(object)
    condition_deleted = pyqtSignal()
    edit_canceled = pyqtSignal()

    def __init__(
        self,
        columns: List[str],
        column_types: Optional[Dict[str, str]] = None,
        column_stats: Optional[Dict[str, Dict[str, Any]]] = None,
        condition: Optional[FilterCondition] = None,
        parent=None
    ):
        super().__init__(parent)
        self.columns = columns
        self.column_types = column_types or {}
        self.column_stats = column_stats or {}
        self.condition = condition
        self._is_editing = condition is None
        self._setup_ui()
        if self.condition:
            self._refresh_display_text()

    def _setup_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(8, 4, 8, 4)
        self.main_layout.setSpacing(6)

        # 左侧蓝色标识条
        self.left_bar = QWidget(self)
        self.left_bar.setFixedWidth(3)
        self.left_bar.setStyleSheet("background: #4A90D9; border-radius: 2px;")
        self.main_layout.addWidget(self.left_bar)

        # 双模式切换
        self.stack = QStackedWidget()

        self.display_widget = self._build_display_widget()
        self.stack.addWidget(self.display_widget)

        self.edit_widget = self._build_edit_widget()
        self.stack.addWidget(self.edit_widget)

        self.main_layout.addWidget(self.stack, 1)
        self._refresh_mode()

    def _build_display_widget(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.lbl_display = QLabel()
        self.lbl_display.setStyleSheet("color: #333; font-size: 13px;")

        # 编辑按钮（小型文字按钮）
        self.btn_edit = QPushButton("编辑")
        self.btn_edit.setToolTip("编辑条件")
        self.btn_edit.setFixedSize(36, 22)
        self.btn_edit.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #4A90D9;
                font-size: 11px;
                padding: 0;
            }
            QPushButton:hover {
                color: #2E5A8C;
                text-decoration: underline;
            }
        """)
        self.btn_edit.clicked.connect(self._enter_edit_mode)

        # 删除按钮
        self.btn_delete = QPushButton("删除")
        self.btn_delete.setToolTip("删除条件")
        self.btn_delete.setFixedSize(36, 22)
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #999;
                font-size: 11px;
                padding: 0;
            }
            QPushButton:hover {
                color: #E53935;
                text-decoration: underline;
            }
        """)
        self.btn_delete.clicked.connect(self.condition_deleted.emit)

        layout.addWidget(self.lbl_display)
        layout.addStretch()
        layout.addWidget(self.btn_edit)
        layout.addWidget(self.btn_delete)

        return w

    def _build_edit_widget(self) -> QWidget:
        """构建编辑模式 UI（垂直布局：条件行 + 统计信息行）"""
        w = QWidget()
        main_layout = QVBoxLayout(w)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # ===== 第1行：条件编辑控件 =====
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        # NOT
        self.chk_negate = QCheckBox("NOT")
        self.chk_negate.setToolTip("取反")
        self.chk_negate.setStyleSheet("color: #666; font-size: 11px;")

        # 变量下拉（紧凑）
        self.cmb_variable = QComboBox()
        self.cmb_variable.setEditable(True)
        self.cmb_variable.setFixedWidth(140)
        self.cmb_variable.addItems(self.columns)

        self.variable_completer = QCompleter(self.columns, self)
        self.variable_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.variable_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.variable_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.cmb_variable.setCompleter(self.variable_completer)

        self.cmb_variable.setStyleSheet("""
            QComboBox {
                background: #FFFFFF;
                border: 1px solid #D0D7E0;
                border-radius: 5px;
                padding: 2px 6px;
                min-height: 22px;
                font-size: 12px;
            }
            QComboBox:focus { border-color: #4A90D9; }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView {
                background: #FFFFFF;
                border: 1px solid #D0D7E0;
                border-radius: 5px;
                selection-background-color: #E8EEF6;
                font-size: 12px;
            }
        """)
        self.cmb_variable.currentTextChanged.connect(self._on_variable_changed)

        # 操作符
        self.cmb_operator = QComboBox()
        self.cmb_operator.setFixedWidth(90)
        self.cmb_operator.setStyleSheet(self.cmb_variable.styleSheet())
        self.cmb_operator.currentTextChanged.connect(self._on_operator_changed)

        # 值输入区
        self.value_stack = QStackedWidget()
        self.value_stack.setFixedHeight(26)

        self.edit_single = QLineEdit()
        self.edit_single.setPlaceholderText("值")
        self.edit_single.setFixedWidth(100)
        self.edit_single.setStyleSheet("""
            QLineEdit {
                background: #FFFFFF;
                border: 1px solid #D0D7E0;
                border-radius: 5px;
                padding: 2px 6px;
                min-height: 22px;
                font-size: 12px;
            }
            QLineEdit:focus { border-color: #4A90D9; }
        """)
        self.value_stack.addWidget(self.edit_single)

        self.edit_multi = QLineEdit()
        self.edit_multi.setPlaceholderText("a, b, c")
        self.edit_multi.setFixedWidth(140)
        self.edit_multi.setStyleSheet(self.edit_single.styleSheet())
        self.value_stack.addWidget(self.edit_multi)

        self.range_widget = QWidget()
        range_layout = QHBoxLayout(self.range_widget)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.setSpacing(3)
        self.edit_range_min = QLineEdit()
        self.edit_range_min.setPlaceholderText("min")
        self.edit_range_min.setFixedWidth(55)
        self.edit_range_min.setStyleSheet(self.edit_single.styleSheet())
        self.edit_range_max = QLineEdit()
        self.edit_range_max.setPlaceholderText("max")
        self.edit_range_max.setFixedWidth(55)
        self.edit_range_max.setStyleSheet(self.edit_single.styleSheet())
        range_layout.addWidget(self.edit_range_min)
        range_layout.addWidget(QLabel("~"))
        range_layout.addWidget(self.edit_range_max)
        range_layout.addStretch()
        self.value_stack.addWidget(self.range_widget)

        self.lbl_no_value = QLabel("—")
        self.lbl_no_value.setStyleSheet("color: #BBB; font-size: 12px; padding: 2px;")
        self.value_stack.addWidget(self.lbl_no_value)

        # 确认/取消
        self.btn_confirm = QPushButton("确认")
        self.btn_confirm.setToolTip("确认")
        self.btn_confirm.setFixedSize(36, 22)
        self.btn_confirm.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                padding: 0;
            }
            QPushButton:hover { background: #43A047; }
        """)
        self.btn_confirm.clicked.connect(self._save_condition)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setToolTip("取消")
        self.btn_cancel.setFixedSize(36, 22)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background: #E0E0E0;
                color: #666;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                padding: 0;
            }
            QPushButton:hover { background: #D0D0D0; }
        """)
        self.btn_cancel.clicked.connect(self._cancel_edit)

        row1.addWidget(self.chk_negate)
        row1.addWidget(self.cmb_variable)
        row1.addWidget(self.cmb_operator)
        row1.addWidget(self.value_stack, 1)
        row1.addWidget(self.btn_confirm)
        row1.addWidget(self.btn_cancel)
        main_layout.addLayout(row1)

        # ===== 第2行：变量统计信息 =====
        self.lbl_stats = QLabel("")
        self.lbl_stats.setStyleSheet("""
            QLabel {
                color: #888;
                font-size: 11px;
                padding: 2px 0px 2px 24px;
            }
        """)
        self.lbl_stats.setVisible(False)  # 默认隐藏，有统计信息时显示
        main_layout.addWidget(self.lbl_stats)

        self._on_variable_changed(self.cmb_variable.currentText())
        return w

    def _update_stats_display(self, col_name: str):
        """更新统计信息显示"""
        stats = self.column_stats.get(col_name)
        if not stats:
            self.lbl_stats.setVisible(False)
            return

        import math

        def _is_valid_num(v):
            return v is not None and not (isinstance(v, float) and math.isnan(v))

        parts = []
        col_type = stats.get('type', 'unknown')
        parts.append(f"类型: {col_type}")

        if col_type == 'numeric':
            if _is_valid_num(stats.get('min')):
                parts.append(f"最小: {stats['min']:.2f}")
            if _is_valid_num(stats.get('max')):
                parts.append(f"最大: {stats['max']:.2f}")
            if _is_valid_num(stats.get('mean')):
                parts.append(f"均值: {stats['mean']:.2f}")
        elif col_type == 'string':
            n_unique = stats.get('n_unique')
            if n_unique is not None:
                parts.append(f"唯一值: {n_unique}")
            top_values = stats.get('top_values')
            if top_values:
                top = ', '.join(str(v) for v in top_values[:3])
                parts.append(f"常见: {top}")

        missing_pct = stats.get('missing_pct')
        if missing_pct is not None:
            parts.append(f"缺失: {missing_pct:.1%}")

        self.lbl_stats.setText('  |  '.join(parts))
        self.lbl_stats.setVisible(True)

    def _enter_edit_mode(self):
        self._is_editing = True
        self._load_condition_to_edit()
        self._refresh_mode()

    def _save_condition(self):
        try:
            cond = self._build_condition_from_ui()
            self.condition = cond
            self._is_editing = False
            self._refresh_display_text()
            self._refresh_mode()
            self.condition_saved.emit(cond)
        except ValueError as e:
            self.edit_single.setPlaceholderText(str(e))

    def _cancel_edit(self):
        if self.condition is None:
            self.condition_deleted.emit()
        else:
            self._is_editing = False
            self._refresh_mode()
            self.edit_canceled.emit()

    def get_current_condition(self) -> Optional[FilterCondition]:
        """获取当前条件（包括编辑模式下从 UI 实时构建）"""
        if not self._is_editing:
            return self.condition
        try:
            return self._build_condition_from_ui()
        except ValueError:
            return None

    def _build_condition_from_ui(self) -> FilterCondition:
        variable = self.cmb_variable.currentText().strip()
        operator = self.cmb_operator.currentText()
        negate = self.chk_negate.isChecked()

        if not variable:
            raise ValueError("变量名不能为空")
        if not operator:
            raise ValueError("操作符不能为空")

        value = self._get_value_from_ui(operator)
        return FilterCondition(variable=variable, operator=operator, value=value, negate=negate)

    def _get_value_from_ui(self, operator: str):
        if operator in ('is null', 'is not null'):
            return None

        if operator == 'between':
            min_val = self.edit_range_min.text().strip()
            max_val = self.edit_range_max.text().strip()
            if not min_val or not max_val:
                raise ValueError("区间需要最小值和最大值")
            try:
                return [float(min_val), float(max_val)]
            except ValueError:
                return [min_val, max_val]
        elif operator in ('in', 'not in'):
            text = self.edit_multi.text().strip()
            values = [v.strip() for v in text.split(',') if v.strip()]
            if not values:
                raise ValueError("请至少输入一个值")
            return values
        else:
            text = self.edit_single.text().strip()
            if not text:
                raise ValueError("请输入比较值")
            try:
                return float(text) if '.' in text else int(text)
            except ValueError:
                return text

    def _on_variable_changed(self, text: str):
        """变量改变时，更新操作符列表和统计信息"""
        col_type = self.column_types.get(text, 'object')
        ops = OPERATORS_BY_TYPE.get(col_type, OPERATORS_BY_TYPE['object'])

        current_op = self.cmb_operator.currentText()
        self.cmb_operator.clear()
        self.cmb_operator.addItems(ops)

        idx = self.cmb_operator.findText(current_op)
        if idx >= 0:
            self.cmb_operator.setCurrentIndex(idx)
        else:
            for i in range(self.cmb_operator.count()):
                if self.cmb_operator.itemText(i) not in ('is null', 'is not null'):
                    self.cmb_operator.setCurrentIndex(i)
                    break

        # 更新统计信息
        self._update_stats_display(text)

    def _on_operator_changed(self, text: str):
        if text in ('is null', 'is not null'):
            self.value_stack.setCurrentIndex(3)
        elif text == 'between':
            self.value_stack.setCurrentIndex(2)
        elif text in ('in', 'not in'):
            self.value_stack.setCurrentIndex(1)
        else:
            self.value_stack.setCurrentIndex(0)

    def _refresh_mode(self):
        self.stack.setCurrentIndex(1 if self._is_editing else 0)

    def _refresh_display_text(self):
        if self.condition:
            self.lbl_display.setText(self._format_condition(self.condition))

    def _format_condition(self, cond: FilterCondition) -> str:
        """格式化条件为富文本显示（需转义 HTML 特殊字符防止被解析为标签）"""
        prefix = "NOT " if cond.negate else ""

        def escape_html(text: str) -> str:
            return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        var = f"<b>{escape_html(cond.variable)}</b>"
        op = escape_html(cond.operator)

        if cond.operator in ('is null', 'is not null'):
            return f"{prefix}{var} {op}"

        if cond.operator in ('in', 'not in') and isinstance(cond.value, list):
            values = ', '.join(escape_html(str(v)) for v in cond.value)
            return f"{prefix}{var} {op} [{values}]"

        if cond.operator == 'between' and isinstance(cond.value, (list, tuple)) and len(cond.value) == 2:
            return f"{prefix}{var} {op} [{escape_html(str(cond.value[0]))}, {escape_html(str(cond.value[1]))}]"

        return f"{prefix}{var} {op} {escape_html(str(cond.value))}"

    def _load_condition_to_edit(self):
        if not self.condition:
            return
        self.cmb_variable.setCurrentText(self.condition.variable)
        self.cmb_operator.setCurrentText(self.condition.operator)
        self.chk_negate.setChecked(self.condition.negate)
        op = self.condition.operator
        val = self.condition.value

        if op in ('is null', 'is not null'):
            pass
        elif op == 'between' and isinstance(val, (list, tuple)) and len(val) == 2:
            self.edit_range_min.setText(str(val[0]))
            self.edit_range_max.setText(str(val[1]))
        elif op in ('in', 'not in') and isinstance(val, list):
            self.edit_multi.setText(', '.join(str(v) for v in val))
        elif val is not None:
            self.edit_single.setText(str(val))

        self._on_operator_changed(op)

    def keyPressEvent(self, event):
        if self._is_editing:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._save_condition()
                return
            elif event.key() == Qt.Key.Key_Escape:
                self._cancel_edit()
                return
        super().keyPressEvent(event)
