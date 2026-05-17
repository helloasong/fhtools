"""
过滤规则编辑器主组件

整合模式切换、规则树编辑、效果预览于一体。
支持两种使用场景：
- 全局规则编辑（无 mode_switch，直接编辑规则树）
- 指标级规则编辑（有 mode_switch，三态切换）

关键设计：规则树区域使用 QScrollArea 包裹，
确保条件再多也不会将底部按钮推出可视区域。
"""

from typing import Optional, List, Dict, Any
import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt

from src.data.models import FilterRule, FilterMode, FeatureFilterSetting, FilterLogicNode, FilterCondition
from src.ui.widgets.filter_mode_switch import FilterModeSwitch
from src.ui.widgets.filter_logic_group_widget import FilterLogicGroupWidget
from src.ui.widgets.filter_condition_row import FilterConditionRow
from src.ui.widgets.filter_preview_panel import FilterPreviewPanel
from src.core.filtering.engine import FilterEngine, FilterPreviewResult


class FilterRuleEditor(QWidget):
    """过滤规则编辑器主组件

    Signals:
        rule_changed(FilterRule|None): 规则内容变化时发射
        mode_changed(FilterMode): 模式切换时发射（仅指标级）
        test_requested(FilterRule|None): 用户点击测试按钮时发射
        save_requested(FilterRule|None, FilterMode): 用户点击保存按钮时发射
    """
    rule_changed = pyqtSignal(object)  # FilterRule | None
    mode_changed = pyqtSignal(object)  # FilterMode
    test_requested = pyqtSignal(object)  # FilterRule | None

    def __init__(
        self,
        columns: List[str],
        column_types: Optional[dict] = None,
        column_stats: Optional[Dict[str, Dict[str, Any]]] = None,
        setting: Optional[FeatureFilterSetting] = None,
        global_rule: Optional[FilterRule] = None,
        is_global_editor: bool = False,
        parent=None
    ):
        super().__init__(parent)
        self.columns = columns
        self.column_types = column_types or {}
        self.column_stats = column_stats or {}
        self.global_rule = global_rule
        self.is_global_editor = is_global_editor

        # 内部状态
        self._setting = setting or FeatureFilterSetting()
        self._current_rule = self._resolve_initial_rule()
        self._cached_custom_rule: Optional[FilterRule] = None  # 缓存 CUSTOM 模式下的规则

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        # ===== 头部 =====
        header = QHBoxLayout()
        header.setSpacing(8)

        title = "全局过滤规则" if self.is_global_editor else "过滤规则"
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        header.addWidget(self.lbl_title)

        if not self.is_global_editor:
            self.mode_switch = FilterModeSwitch()
            self.mode_switch.set_mode(self._setting.mode)
            self.mode_switch.mode_changed.connect(self._on_mode_changed)
            header.addWidget(self.mode_switch)
        else:
            self.mode_switch = None

        header.addStretch()
        layout.addLayout(header)

        # ===== 规则树编辑区（用 QScrollArea 包裹，防止溢出） =====
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.tree_container = QWidget()
        self.tree_layout = QVBoxLayout(self.tree_container)
        self.tree_layout.setContentsMargins(0, 0, 0, 0)
        self.tree_layout.setSpacing(8)

        # 根级逻辑组
        self.root_group = FilterLogicGroupWidget(
            columns=self.columns,
            column_types=self.column_types,
            column_stats=self.column_stats,
            is_root=True,
            parent=self.tree_container
        )
        self.root_group.structure_changed.connect(self._on_tree_changed)
        self.tree_layout.addWidget(self.root_group)
        self.tree_layout.addStretch()

        self.scroll.setWidget(self.tree_container)
        layout.addWidget(self.scroll, 1)  # 占据所有剩余空间

        # ===== 全局规则预览（仅指标级，且模式为 GLOBAL 时显示） =====
        self.global_preview = QLabel()
        self.global_preview.setWordWrap(True)
        self.global_preview.setTextFormat(Qt.TextFormat.PlainText)
        self.global_preview.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 12px;
                padding: 8px 10px;
                background: #F8FAFD;
                border: 1px solid #E3E6EA;
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.global_preview)

        # ===== 禁用提示（模式为 DISABLED 时显示） =====
        self.disabled_notice = QLabel("🚫 该指标不参与任何数据过滤，将使用全部样本进行分箱。")
        self.disabled_notice.setWordWrap(True)
        self.disabled_notice.setStyleSheet("""
            QLabel {
                color: #999;
                font-size: 12px;
                padding: 10px 12px;
                background: #FFF3F3;
                border: 1px solid #FFD6D6;
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.disabled_notice)

        # ===== 效果预览面板 =====
        self.preview_panel = FilterPreviewPanel()
        layout.addWidget(self.preview_panel)

        # 注：保存/测试按钮由外部对话框统一提供，编辑器内不再放置按钮

    def _resolve_initial_rule(self) -> Optional[FilterRule]:
        """根据当前 setting 和场景确定初始规则"""
        if self.is_global_editor:
            return self.global_rule

        if self._setting.mode == FilterMode.CUSTOM:
            return self._setting.rule
        return None

    def _on_mode_changed(self, mode: FilterMode):
        # 保存当前规则到缓存（仅在离开 CUSTOM 模式时）
        if self._setting.mode == FilterMode.CUSTOM:
            self._cached_custom_rule = self.get_current_rule()

        self._setting.mode = mode
        self.mode_changed.emit(mode)

        # 切到 CUSTOM 模式时恢复缓存规则
        if mode == FilterMode.CUSTOM:
            rule_to_restore = self._cached_custom_rule or self._setting.rule
            if rule_to_restore:
                self._load_rule_to_ui(rule_to_restore)

        self._refresh_ui_by_mode()

    def _refresh_ui_by_mode(self):
        """根据当前模式刷新 UI 各区域的可见性"""
        if self.is_global_editor:
            self.scroll.setVisible(True)
            self.global_preview.setVisible(False)
            self.disabled_notice.setVisible(False)
            return

        mode = self._setting.mode

        if mode == FilterMode.GLOBAL:
            self.scroll.setVisible(False)
            self.global_preview.setVisible(True)
            self.disabled_notice.setVisible(False)
            self._update_global_preview()

        elif mode == FilterMode.CUSTOM:
            self.scroll.setVisible(True)
            self.global_preview.setVisible(False)
            self.disabled_notice.setVisible(False)

        elif mode == FilterMode.DISABLED:
            self.scroll.setVisible(False)
            self.global_preview.setVisible(False)
            self.disabled_notice.setVisible(True)

        # 调整布局
        self.tree_container.adjustSize()
        self.scroll.updateGeometry()

    def _update_global_preview(self):
        """更新全局规则预览文本"""
        if self.global_rule and self.global_rule.enabled and self.global_rule.root:
            summary = self._format_rule_summary(self.global_rule)
            text = f"🌐 当前使用全局规则:\n{summary}"
        else:
            text = "🌐 当前使用全局规则:\n（全局规则未配置，不过滤任何数据）"
        self.global_preview.setText(text)

    def _format_rule_summary(self, rule: FilterRule, indent: str = "") -> str:
        """格式化规则摘要（递归）"""
        if rule is None or rule.root is None:
            return f"{indent}（无规则）"
        return self._format_node_summary(rule.root, indent)

    def _format_node_summary(self, node, indent: str = "") -> str:
        """递归格式化节点摘要"""
        from src.data.models import FilterCondition, FilterLogicNode

        if isinstance(node, FilterCondition):
            prefix = "NOT " if node.negate else ""
            if node.operator in ('is null', 'is not null'):
                return f"{indent}{prefix}{node.variable} {node.operator}"
            if node.operator in ('in', 'not in') and isinstance(node.value, list):
                values = ', '.join(str(v) for v in node.value)
                return f"{indent}{prefix}{node.variable} {node.operator} [{values}]"
            if node.operator == 'between' and isinstance(node.value, (list, tuple)) and len(node.value) == 2:
                return f"{indent}{prefix}{node.variable} {node.operator} [{node.value[0]}, {node.value[1]}]"
            return f"{indent}{prefix}{node.variable} {node.operator} {node.value}"

        elif isinstance(node, FilterLogicNode):
            lines = [f"{indent}[{node.operator}]"]
            for child in node.children:
                lines.append(self._format_node_summary(child, indent + "  "))
            return '\n'.join(lines)

        return f"{indent}（未知节点）"

    def _on_tree_changed(self):
        """规则树结构变化"""
        self._current_rule = self.get_current_rule()
        self.rule_changed.emit(self._current_rule)

    def do_test(self):
        """触发测试（供外部对话框调用）

        根据当前模式返回正确的测试规则：
        - 全局编辑器: 当前编辑器中的规则
        - 指标级 GLOBAL 模式: 全局规则
        - 指标级 CUSTOM 模式: 当前编辑器中的自定义规则
        - 指标级 DISABLED 模式: None（不过滤）
        """
        if self.is_global_editor:
            rule = self.get_current_rule()
        else:
            if self._setting.mode == FilterMode.GLOBAL:
                rule = self.global_rule
            elif self._setting.mode == FilterMode.CUSTOM:
                rule = self.get_current_rule()
            else:  # DISABLED
                rule = None
        self.test_requested.emit(rule)

    def get_current_rule(self) -> Optional[FilterRule]:
        """获取当前编辑器中的规则（从 UI 构建）"""
        root = self.root_group.to_logic_node()
        return FilterRule(root=root) if root.children else None

    def set_preview_result(self, result: FilterPreviewResult):
        """设置预览结果（由外部调用）"""
        self.preview_panel.set_result(result)

    def load_setting(self, setting: FeatureFilterSetting, global_rule: Optional[FilterRule] = None):
        """加载设置到编辑器"""
        self._setting = setting or FeatureFilterSetting()
        self.global_rule = global_rule or self.global_rule

        if not self.is_global_editor and self.mode_switch:
            self.mode_switch.set_mode(self._setting.mode)

        # 全局编辑器加载 global_rule，指标级加载 setting.rule
        rule_to_load = self.global_rule if self.is_global_editor else self._setting.rule
        self._load_rule_to_ui(rule_to_load)

        self._refresh_ui_by_mode()

    def _load_rule_to_ui(self, rule: Optional[FilterRule]):
        """将规则加载到 UI"""
        # 清除现有子组件
        while self.root_group.child_widgets:
            widget = self.root_group.child_widgets.pop()
            self.root_group.children_layout.removeWidget(widget)
            widget.deleteLater()

        if rule and rule.root:
            if isinstance(rule.root, FilterCondition):
                # 单条件直接添加到根组
                self._add_condition_to_group(self.root_group, rule.root)
            elif isinstance(rule.root, FilterLogicNode):
                self._load_node_to_group(self.root_group, rule.root)

    def _add_condition_to_group(self, group: FilterLogicGroupWidget, condition: FilterCondition):
        """添加单条件到逻辑组"""
        row = FilterConditionRow(
            columns=self.columns,
            column_types=self.column_types,
            column_stats=self.column_stats,
            condition=condition,
            parent=group.children_container
        )
        row.condition_saved.connect(group._on_child_changed)
        row.condition_deleted.connect(lambda r=row: group._remove_child(r))
        row.edit_canceled.connect(group._on_child_changed)
        group.child_widgets.append(row)
        group.children_layout.addWidget(row)

    def _load_node_to_group(self, group: FilterLogicGroupWidget, node: FilterLogicNode):
        """递归加载逻辑节点到逻辑组"""
        group.cmb_operator.setCurrentText(node.operator)
        for child in node.children:
            if isinstance(child, FilterLogicNode):
                sub_group = self._create_group_widget(child, group.nesting_level + 1, parent_group=group)
                group.child_widgets.append(sub_group)
                group.children_layout.addWidget(sub_group)
            elif isinstance(child, FilterCondition):
                self._add_condition_to_group(group, child)

    def _create_group_widget(self, node: FilterLogicNode, nesting_level: int, parent_group: FilterLogicGroupWidget = None) -> FilterLogicGroupWidget:
        """创建并递归填充逻辑组"""
        group = FilterLogicGroupWidget(
            columns=self.columns,
            column_types=self.column_types,
            column_stats=self.column_stats,
            node=node,
            is_root=False,
            nesting_level=nesting_level
        )
        group.structure_changed.connect(self._on_tree_changed)
        if parent_group is not None:
            group.ungroup_requested.connect(parent_group._on_child_ungroup)
        return group

    def get_result(self):
        """获取编辑结果

        Returns:
            全局编辑器: Optional[FilterRule]
            指标级编辑器: FeatureFilterSetting
        """
        if self.is_global_editor:
            return self.get_current_rule()

        # 指标级编辑器：总是保存当前编辑器中的规则（不根据 mode 判断）
        # 这样 GLOBAL/DISABLED 切换回 CUSTOM 时，自定义规则仍然保留
        rule = self.get_current_rule()
        return FeatureFilterSetting(mode=self._setting.mode, rule=rule)
