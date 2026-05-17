"""
逻辑组容器组件（紧凑美化版）

参考现代 Web Query Builder：
- 左侧彩色竖条标识层级
- 紧凑内边距
- 操作按钮小型文字化
"""

from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QLabel, QFrame
)
from PyQt6.QtCore import pyqtSignal

from src.data.models import FilterLogicNode, FilterCondition
from src.ui.widgets.filter_condition_row import FilterConditionRow


class FilterLogicGroupWidget(QWidget):
    structure_changed = pyqtSignal()
    ungroup_requested = pyqtSignal(object)

    def __init__(
        self,
        columns: List[str],
        column_types: Optional[dict] = None,
        column_stats: Optional[dict] = None,
        node: Optional[FilterLogicNode] = None,
        is_root: bool = False,
        nesting_level: int = 0,
        parent=None
    ):
        super().__init__(parent)
        self.columns = columns
        self.column_types = column_types or {}
        self.column_stats = column_stats or {}
        self.node = node or FilterLogicNode(operator='AND')
        self.is_root = is_root
        self.nesting_level = nesting_level
        self.child_widgets: List[QWidget] = []
        self._setup_ui()

    def _setup_ui(self):
        # 左侧色条颜色（嵌套越深颜色越深）
        bar_colors = ['#4A90D9', '#5BA3E8', '#7BB8F0', '#9CCCF5']
        bg_colors = ['#F8FAFD', '#F1F5FA', '#EAF0F7', '#E3EBF4']
        bar_color = bar_colors[min(self.nesting_level, len(bar_colors) - 1)]
        bg_color = bg_colors[min(self.nesting_level, len(bg_colors) - 1)]

        self.setStyleSheet(f"""
            FilterLogicGroupWidget {{
                background: {bg_color};
                border: 1px solid #DDE3EC;
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 8, 10, 8)

        # 主内容区（带左侧色条）
        content = QHBoxLayout()
        content.setSpacing(0)
        content.setContentsMargins(0, 0, 0, 0)

        # 左侧色条
        bar = QWidget()
        bar.setFixedWidth(3)
        bar.setStyleSheet(f"background: {bar_color}; border-radius: 2px;")
        content.addWidget(bar)
        content.addSpacing(8)

        # 右侧内容
        right = QVBoxLayout()
        right.setSpacing(6)
        right.setContentsMargins(0, 0, 0, 0)

        # 头部
        header = QHBoxLayout()
        header.setSpacing(6)

        self.cmb_operator = QComboBox()
        self.cmb_operator.addItems(['AND', 'OR'])
        self.cmb_operator.setCurrentText(self.node.operator)
        self.cmb_operator.setFixedWidth(60)
        self.cmb_operator.setStyleSheet("""
            QComboBox {
                background: #FFFFFF;
                border: 1px solid #D0D7E0;
                border-radius: 5px;
                padding: 2px 6px;
                min-height: 22px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self.cmb_operator.currentTextChanged.connect(self._on_operator_changed)

        header.addWidget(QLabel("逻辑:"))
        header.addWidget(self.cmb_operator)
        header.addStretch()

        if not self.is_root:
            self.btn_ungroup = QPushButton("取消分组")
            self.btn_ungroup.setToolTip("将子条件提升到父级")
            self.btn_ungroup.setFixedHeight(22)
            self.btn_ungroup.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #888;
                    font-size: 11px;
                    padding: 0 4px;
                }
                QPushButton:hover {
                    color: #4A90D9;
                    text-decoration: underline;
                }
            """)
            self.btn_ungroup.clicked.connect(self._on_ungroup)
            header.addWidget(self.btn_ungroup)

            self.btn_delete_group = QPushButton("删除")
            self.btn_delete_group.setToolTip("删除此逻辑组")
            self.btn_delete_group.setFixedHeight(22)
            self.btn_delete_group.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #888;
                    font-size: 11px;
                    padding: 0 4px;
                }
                QPushButton:hover {
                    color: #E53935;
                    text-decoration: underline;
                }
            """)
            self.btn_delete_group.clicked.connect(self._on_delete_group)
            header.addWidget(self.btn_delete_group)

        right.addLayout(header)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #E3E8F0;")
        right.addWidget(line)

        # 子节点容器
        self.children_container = QWidget()
        self.children_layout = QVBoxLayout(self.children_container)
        self.children_layout.setSpacing(4)
        indent = min(8 + self.nesting_level * 4, 20)
        self.children_layout.setContentsMargins(indent, 4, 0, 4)
        right.addWidget(self.children_container)

        # 操作按钮栏
        actions = QHBoxLayout()
        actions.setSpacing(6)

        self.btn_add_condition = QPushButton("+ 条件")
        self.btn_add_condition.setFixedHeight(24)
        self.btn_add_condition.setStyleSheet("""
            QPushButton {
                background: linear-gradient(to bottom, #E8EEF6, #D9E4F5);
                border: 1px solid #C9D6EA;
                border-radius: 5px;
                padding: 2px 10px;
                font-size: 11px;
                color: #444;
            }
            QPushButton:hover {
                background: linear-gradient(to bottom, #D9E4F5, #C9D6EA);
            }
        """)
        self.btn_add_condition.clicked.connect(self._add_new_condition)

        self.btn_add_and_group = QPushButton("+ AND组")
        self.btn_add_and_group.setFixedHeight(24)
        self.btn_add_and_group.setStyleSheet(self.btn_add_condition.styleSheet())
        self.btn_add_and_group.clicked.connect(lambda: self._add_new_group('AND'))

        self.btn_add_or_group = QPushButton("+ OR组")
        self.btn_add_or_group.setFixedHeight(24)
        self.btn_add_or_group.setStyleSheet(self.btn_add_condition.styleSheet())
        self.btn_add_or_group.clicked.connect(lambda: self._add_new_group('OR'))

        actions.addWidget(self.btn_add_condition)
        actions.addWidget(self.btn_add_and_group)
        actions.addWidget(self.btn_add_or_group)
        actions.addStretch()

        right.addLayout(actions)
        content.addLayout(right, 1)
        layout.addLayout(content)

        self._build_from_node(self.node)

    def _build_from_node(self, node: FilterLogicNode):
        for child in node.children:
            if isinstance(child, FilterLogicNode):
                self._add_group_widget(child)
            elif isinstance(child, FilterCondition):
                self._add_condition_widget(child)

    def _add_new_condition(self):
        row = FilterConditionRow(
            columns=self.columns,
            column_types=self.column_types,
            column_stats=self.column_stats,
            parent=self.children_container
        )
        row.condition_saved.connect(self._on_child_changed)
        row.condition_deleted.connect(lambda: self._remove_child(row))
        row.edit_canceled.connect(self._on_child_changed)
        self.child_widgets.append(row)
        self.children_layout.addWidget(row)
        self.structure_changed.emit()

    def _add_condition_widget(self, condition: FilterCondition):
        row = FilterConditionRow(
            columns=self.columns,
            column_types=self.column_types,
            column_stats=self.column_stats,
            condition=condition,
            parent=self.children_container
        )
        row.condition_saved.connect(self._on_child_changed)
        row.condition_deleted.connect(lambda: self._remove_child(row))
        row.edit_canceled.connect(self._on_child_changed)
        self.child_widgets.append(row)
        self.children_layout.addWidget(row)

    def _add_new_group(self, operator: str):
        node = FilterLogicNode(operator=operator)
        self._add_group_widget(node)
        self.structure_changed.emit()

    def _add_group_widget(self, node: FilterLogicNode):
        group = FilterLogicGroupWidget(
            columns=self.columns,
            column_types=self.column_types,
            column_stats=self.column_stats,
            node=node,
            is_root=False,
            nesting_level=self.nesting_level + 1,
            parent=self.children_container
        )
        group.structure_changed.connect(self._on_child_changed)
        group.ungroup_requested.connect(self._on_child_ungroup)
        self.child_widgets.append(group)
        self.children_layout.addWidget(group)

    def _remove_child(self, widget: QWidget):
        if widget in self.child_widgets:
            self.child_widgets.remove(widget)
        self.children_layout.removeWidget(widget)
        widget.deleteLater()
        self.structure_changed.emit()

    def _on_operator_changed(self, text: str):
        self.node.operator = text
        self.structure_changed.emit()

    def _on_ungroup(self):
        self.ungroup_requested.emit(self)

    def _on_delete_group(self):
        # 从父级 FilterLogicGroupWidget 的 child_widgets 中移除自己
        p = self.parent()
        while p:
            if isinstance(p, FilterLogicGroupWidget):
                if self in p.child_widgets:
                    p.child_widgets.remove(self)
                break
            p = p.parent()
        self.deleteLater()
        self.structure_changed.emit()

    def _on_child_changed(self):
        self.structure_changed.emit()

    def _on_child_ungroup(self, group: 'FilterLogicGroupWidget'):
        if group not in self.child_widgets:
            return

        index = self.child_widgets.index(group)
        group_child_nodes = group.to_logic_node().children

        self.child_widgets.remove(group)
        self.children_layout.removeWidget(group)
        group.deleteLater()

        for i, child_node in enumerate(group_child_nodes):
            if isinstance(child_node, FilterLogicNode):
                self._add_group_widget_at(index + i, child_node)
            elif isinstance(child_node, FilterCondition):
                self._add_condition_widget_at(index + i, child_node)

        self.structure_changed.emit()

    def _add_group_widget_at(self, index: int, node: FilterLogicNode):
        group = FilterLogicGroupWidget(
            columns=self.columns,
            column_types=self.column_types,
            column_stats=self.column_stats,
            node=node,
            is_root=False,
            nesting_level=self.nesting_level + 1,
            parent=self.children_container
        )
        group.structure_changed.connect(self._on_child_changed)
        group.ungroup_requested.connect(self._on_child_ungroup)
        self.child_widgets.insert(index, group)
        self.children_layout.insertWidget(index, group)

    def _add_condition_widget_at(self, index: int, condition: FilterCondition):
        row = FilterConditionRow(
            columns=self.columns,
            column_types=self.column_types,
            column_stats=self.column_stats,
            condition=condition,
            parent=self.children_container
        )
        row.condition_saved.connect(self._on_child_changed)
        row.condition_deleted.connect(lambda: self._remove_child(row))
        row.edit_canceled.connect(self._on_child_changed)
        self.child_widgets.insert(index, row)
        self.children_layout.insertWidget(index, row)

    def to_logic_node(self) -> FilterLogicNode:
        children = []
        for widget in self.child_widgets[:]:
            # 防御：跳过已被 C++ 层删除的 widget
            try:
                if isinstance(widget, FilterConditionRow):
                    cond = widget.get_current_condition()
                    if cond is not None:
                        children.append(cond)
                elif isinstance(widget, FilterLogicGroupWidget):
                    node = widget.to_logic_node()
                    if node.children:
                        children.append(node)
            except RuntimeError:
                continue

        return FilterLogicNode(
            operator=self.cmb_operator.currentText(),
            children=children
        )
