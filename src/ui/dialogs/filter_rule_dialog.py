"""
过滤规则配置对话框

底部按钮统一为：测试规则 | 取消 | 保存并关闭
"""

from typing import Optional, List
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt

from src.data.models import FilterRule, FeatureFilterSetting, FilterMode
from src.ui.widgets.filter_rule_editor import FilterRuleEditor
from src.core.filtering.engine import FilterEngine, FilterPreviewResult


class FilterRuleDialog(QDialog):
    """过滤规则配置对话框

    Signals:
        rule_saved(object): 用户保存时发射
            全局规则: FilterRule | None
            指标级规则: FeatureFilterSetting
    """
    rule_saved = pyqtSignal(object)

    def __init__(
        self,
        df=None,
        columns: Optional[List[str]] = None,
        column_types: Optional[dict] = None,
        setting: Optional[FeatureFilterSetting] = None,
        global_rule: Optional[FilterRule] = None,
        feature_name: Optional[str] = None,
        parent=None
    ):
        super().__init__(parent)
        self.df = df
        self.columns = columns or []
        self.column_types = column_types or {}
        self.feature_name = feature_name
        self.is_global = feature_name is None

        title = "全局过滤规则配置" if self.is_global else f"过滤规则 - {feature_name}"
        self.setWindowTitle(title)
        self.setMinimumSize(720, 520)
        self.setModal(True)

        # 窗口居中
        if parent:
            geo = parent.geometry()
            self.move(
                geo.center().x() - self.width() // 2,
                geo.center().y() - self.height() // 2
            )

        self._setup_ui()

        # 加载数据
        self.editor.load_setting(
            setting or FeatureFilterSetting(),
            global_rule
        )

    def _compute_column_stats(self) -> dict:
        """计算每列的统计信息，用于条件编辑时提示"""
        if self.df is None or self.df.empty:
            return {}

        stats = {}
        for col in self.columns:
            if col not in self.df.columns:
                continue
            s = self.df[col]
            col_type = self.column_types.get(col, 'object')
            stat = {'type': col_type}

            if col_type == 'numeric':
                stat['min'] = s.min()
                stat['max'] = s.max()
                stat['mean'] = s.mean()
            else:
                stat['n_unique'] = s.nunique()
                stat['top_values'] = s.value_counts().head(3).index.tolist()

            missing_count = s.isna().sum()
            stat['missing_pct'] = missing_count / len(s) if len(s) > 0 else 0.0
            stats[col] = stat
        return stats

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # 计算列统计信息
        column_stats = self._compute_column_stats()

        # 编辑器
        self.editor = FilterRuleEditor(
            columns=self.columns,
            column_types=self.column_types,
            column_stats=column_stats,
            is_global_editor=self.is_global
        )
        self.editor.test_requested.connect(self._on_test_rule)
        layout.addWidget(self.editor, 1)

        # 底部按钮：测试规则 | 取消 | 保存并关闭
        footer = QHBoxLayout()
        footer.setSpacing(10)

        self.btn_test = QPushButton("🧪 测试规则")
        self.btn_test.setToolTip("预览当前规则的过滤效果")
        self.btn_test.setStyleSheet("""
            QPushButton {
                background: linear-gradient(to bottom, #E8EEF6, #D9E4F5);
                border: 1px solid #C9D6EA;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: linear-gradient(to bottom, #D9E4F5, #C9D6EA);
            }
        """)
        self.btn_test.clicked.connect(self.editor.do_test)

        btn_cancel = QPushButton("取消")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: linear-gradient(to bottom, #F4F7FB, #E8EEF6);
                border: 1px solid #C9D6EA;
                border-radius: 6px;
                padding: 6px 18px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: linear-gradient(to bottom, #E8EEF6, #D9E4F5);
            }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("✓ 保存并关闭")
        btn_save.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 18px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #43A047;
            }
        """)
        btn_save.clicked.connect(self._on_save)

        footer.addWidget(self.btn_test)
        footer.addStretch()
        footer.addWidget(btn_cancel)
        footer.addWidget(btn_save)
        layout.addLayout(footer)

    def _on_test_rule(self, rule: Optional[FilterRule]):
        """测试规则效果"""
        if self.df is None or self.df.empty:
            self.editor.set_preview_result(
                FilterPreviewResult(0, 0, 0, 0.0)
            )
            return

        try:
            result = FilterEngine.preview(self.df, rule)
            self.editor.set_preview_result(result)
        except Exception as e:
            self.editor.preview_panel.lbl_total.setText(f"测试出错: {str(e)[:50]}")

    def _on_save(self):
        """保存并关闭"""
        result = self.editor.get_result()
        self.rule_saved.emit(result)
        self.accept()

    def set_columns(self, columns: List[str], column_types: Optional[dict] = None):
        """设置可用列（延迟初始化时使用）"""
        self.editor.columns = columns
        self.editor.column_types = column_types or {}
        self.editor.root_group.columns = columns
        self.editor.root_group.column_types = self.editor.column_types
