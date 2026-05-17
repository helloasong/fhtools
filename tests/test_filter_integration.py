"""
过滤引擎集成测试

测试过滤规则与控制器、数据模型的集成，
包括全局规则生效、自定义规则覆盖、DISABLED 模式、持久化兼容等场景。
"""

import unittest
import tempfile
import os
import pickle
import pandas as pd
import numpy as np

from PyQt6.QtWidgets import QApplication

from src.data.models import (
    ProjectState, BinningConfig, FilterRule, FilterCondition,
    FilterLogicNode, FilterMode, FeatureFilterSetting,
)
from src.controllers.project_controller import ProjectController

# 确保只有一个 QApplication 实例
_app = None

def get_app():
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


class TestFilterIntegration(unittest.TestCase):
    """过滤引擎集成测试"""

    def setUp(self):
        """准备测试环境"""
        self.controller = ProjectController()
        self.df = pd.DataFrame({
            'feature_a': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            'feature_b': [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
            'target': [0, 0, 0, 0, 1, 1, 1, 1, 1, 1],
        })
        self.controller.df = self.df
        self.controller.state = ProjectState(
            project_name="test_project",
            feature_cols=['feature_a', 'feature_b'],
            target_col='target',
        )

    def test_global_filter_applied(self):
        """全局规则在分箱时生效"""
        # 设置全局规则：feature_a > 3
        global_rule = FilterRule(
            root=FilterCondition('feature_a', '>', 3)
        )
        self.controller.save_global_filter_rule(global_rule)

        # 获取过滤后的数据
        filtered = self.controller.get_filtered_data_for_feature('feature_a')
        self.assertEqual(len(filtered), 7)  # 4,5,6,7,8,9,10
        self.assertEqual(filtered['feature_a'].min(), 4)

    def test_custom_filter_overrides_global(self):
        """自定义规则覆盖全局规则"""
        # 设置全局规则：feature_a > 3
        global_rule = FilterRule(
            root=FilterCondition('feature_a', '>', 3)
        )
        self.controller.save_global_filter_rule(global_rule)

        # 设置 feature_a 的自定义规则：feature_a > 7（更严格）
        custom_rule = FilterRule(
            root=FilterCondition('feature_a', '>', 7)
        )
        setting = FeatureFilterSetting(mode=FilterMode.CUSTOM, rule=custom_rule)
        self.controller.save_feature_filter_setting('feature_a', setting)

        # 获取过滤后的数据（应使用自定义规则）
        filtered = self.controller.get_filtered_data_for_feature('feature_a')
        self.assertEqual(len(filtered), 3)  # 8,9,10

        # feature_b 没有自定义规则，应使用全局规则
        filtered_b = self.controller.get_filtered_data_for_feature('feature_b')
        self.assertEqual(len(filtered_b), 7)  # 使用全局规则

    def test_disabled_skips_all_filters(self):
        """DISABLED 模式跳过所有过滤"""
        # 设置全局规则
        global_rule = FilterRule(
            root=FilterCondition('feature_a', '>', 3)
        )
        self.controller.save_global_filter_rule(global_rule)

        # 设置 feature_a 为 DISABLED
        setting = FeatureFilterSetting(mode=FilterMode.DISABLED)
        self.controller.save_feature_filter_setting('feature_a', setting)

        # feature_a 应不过滤
        filtered = self.controller.get_filtered_data_for_feature('feature_a')
        self.assertEqual(len(filtered), 10)  # 全部数据

    def test_filter_preview(self):
        """过滤预览功能正常"""
        rule = FilterRule(root=FilterCondition('feature_a', '>', 5))
        preview = self.controller.get_filter_preview(rule)

        self.assertEqual(preview['total_samples'], 10)
        self.assertEqual(preview['filtered_samples'], 5)  # 6,7,8,9,10
        self.assertEqual(preview['removed_samples'], 5)
        self.assertAlmostEqual(preview['removal_ratio'], 0.5)

    def test_filter_rule_validation(self):
        """规则校验功能正常"""
        # 有效规则
        valid_rule = FilterRule(root=FilterCondition('feature_a', '>', 5))
        errors = self.controller.validate_filter_rule(valid_rule)
        self.assertEqual(len(errors), 0)

        # 无效规则（列不存在）
        invalid_rule = FilterRule(root=FilterCondition('not_exist', '>', 5))
        errors = self.controller.validate_filter_rule(invalid_rule)
        self.assertGreater(len(errors), 0)

    def test_get_effective_filter_rule_priority(self):
        """规则优先级：CUSTOM > GLOBAL > DISABLED"""
        global_rule = FilterRule(root=FilterCondition('feature_a', '>', 3))
        self.controller.save_global_filter_rule(global_rule)

        # 无设置时，使用全局规则
        rule = self.controller.get_effective_filter_rule('feature_a')
        self.assertIsNotNone(rule)

        # DISABLED 时，无规则
        setting = FeatureFilterSetting(mode=FilterMode.DISABLED)
        self.controller.save_feature_filter_setting('feature_a', setting)
        rule = self.controller.get_effective_filter_rule('feature_a')
        self.assertIsNone(rule)

        # CUSTOM 时，使用自定义规则（即使全局规则存在）
        custom_rule = FilterRule(root=FilterCondition('feature_a', '>', 7))
        setting = FeatureFilterSetting(mode=FilterMode.CUSTOM, rule=custom_rule)
        self.controller.save_feature_filter_setting('feature_a', setting)
        rule = self.controller.get_effective_filter_rule('feature_a')
        self.assertIsNotNone(rule)
        # 验证是自定义规则（通过检查内部条件）
        self.assertEqual(rule.root.variable, 'feature_a')
        self.assertEqual(rule.root.value, 7)

    def test_pickle_compatibility(self):
        """ProjectState 可正确 pickle 序列化和反序列化"""
        state = ProjectState(
            project_name="test",
            feature_cols=['a', 'b'],
            target_col='y',
        )
        # 设置过滤规则
        state.global_filter_rule = FilterRule(
            root=FilterCondition('a', '>', 5)
        )
        state.feature_filter_settings['a'] = FeatureFilterSetting(
            mode=FilterMode.CUSTOM,
            rule=FilterRule(root=FilterCondition('b', '==', 'test'))
        )

        # pickle 序列化/反序列化
        data = pickle.dumps(state)
        restored = pickle.loads(data)

        self.assertEqual(restored.project_name, "test")
        self.assertIsNotNone(restored.global_filter_rule)
        self.assertEqual(restored.global_filter_rule.root.variable, 'a')
        self.assertIn('a', restored.feature_filter_settings)
        self.assertEqual(
            restored.feature_filter_settings['a'].mode,
            FilterMode.CUSTOM
        )

    def test_old_project_backward_compat(self):
        """旧项目文件（无过滤字段）加载后不报错"""
        # 模拟旧项目状态（无过滤字段）
        old_state_dict = {
            'project_name': 'old_project',
            'created_at': __import__('datetime').datetime.now(),
            'last_modified': __import__('datetime').datetime.now(),
            'project_dir': '',
            'raw_data_path': '',
            'target_col': 'target',
            'feature_cols': ['a', 'b'],
            'target_mapping': {},
            'variable_stats': {},
            'binning_configs': {},
            'binning_results': {},
            # 注意：没有 global_filter_rule 和 feature_filter_settings
        }

        # 直接用 __init__ 创建（dataclass 会自动使用默认值）
        state = ProjectState(**old_state_dict)

        # 新字段应有默认值
        self.assertIsNone(state.global_filter_rule)
        self.assertEqual(state.feature_filter_settings, {})

    def test_empty_filter_df_handling(self):
        """过滤后数据为空时正确处理"""
        # 设置一个会导致空结果的规则
        rule = FilterRule(root=FilterCondition('feature_a', '>', 999))
        self.controller.save_global_filter_rule(rule)

        filtered = self.controller.get_filtered_data_for_feature('feature_a')
        self.assertTrue(filtered.empty)

    def test_global_filter_save_and_reload(self):
        """全局规则保存后能从 state 中正确读取"""
        # 1. 构建一个复杂的全局规则
        rule = FilterRule(
            root=FilterLogicNode(
                operator='AND',
                children=[
                    FilterCondition('feature_a', '>', 5),
                    FilterCondition('feature_b', '<', 100),
                ]
            )
        )

        # 2. 保存到控制器
        self.controller.save_global_filter_rule(rule)

        # 3. 验证 state 中已保存
        self.assertIsNotNone(self.controller.state.global_filter_rule)
        saved_rule = self.controller.state.global_filter_rule

        # 4. 验证规则内容正确
        self.assertIsInstance(saved_rule.root, FilterLogicNode)
        self.assertEqual(saved_rule.root.operator, 'AND')
        self.assertEqual(len(saved_rule.root.children), 2)
        self.assertEqual(saved_rule.root.children[0].variable, 'feature_a')
        self.assertEqual(saved_rule.root.children[0].value, 5)
        self.assertEqual(saved_rule.root.children[1].variable, 'feature_b')
        self.assertEqual(saved_rule.root.children[1].value, 100)

        # 5. 模拟重新打开对话框：用 saved_rule 创建新的 editor
        get_app()  # 确保 QApplication 存在
        from src.ui.widgets.filter_rule_editor import FilterRuleEditor
        editor = FilterRuleEditor(
            columns=['feature_a', 'feature_b', 'target'],
            is_global_editor=True
        )
        # 第一次加载：空设置 + 全局规则
        editor.load_setting(FeatureFilterSetting(), saved_rule)

        # 6. 验证编辑器能正确返回规则
        result = editor.get_result()
        self.assertIsInstance(result, FilterRule)
        self.assertIsInstance(result.root, FilterLogicNode)
        self.assertEqual(result.root.operator, 'AND')

        # 7. 再次保存并验证
        self.controller.save_global_filter_rule(result)
        reloaded = self.controller.state.global_filter_rule
        self.assertIsNotNone(reloaded)
        self.assertEqual(reloaded.root.children[0].variable, 'feature_a')

    def test_feature_filter_save_and_reload(self):
        """指标级自定义规则保存后能从 state 中正确读取"""
        rule = FilterRule(root=FilterCondition('feature_a', '==', 'test'))
        setting = FeatureFilterSetting(mode=FilterMode.CUSTOM, rule=rule)

        # 保存
        self.controller.save_feature_filter_setting('feature_a', setting)

        # 读取
        saved = self.controller.state.feature_filter_settings['feature_a']
        self.assertEqual(saved.mode, FilterMode.CUSTOM)
        self.assertIsNotNone(saved.rule)
        self.assertEqual(saved.rule.root.variable, 'feature_a')

        # 模拟重新打开对话框
        get_app()  # 确保 QApplication 存在
        from src.ui.widgets.filter_rule_editor import FilterRuleEditor
        editor = FilterRuleEditor(
            columns=['feature_a', 'feature_b', 'target'],
            is_global_editor=False
        )
        editor.load_setting(saved)

        result = editor.get_result()
        self.assertIsInstance(result, FeatureFilterSetting)
        self.assertEqual(result.mode, FilterMode.CUSTOM)
        self.assertIsNotNone(result.rule)
        # UI 加载后会包装在 FilterLogicNode 中
        self.assertIsInstance(result.rule.root, FilterLogicNode)
        self.assertEqual(len(result.rule.root.children), 1)
        self.assertEqual(result.rule.root.children[0].variable, 'feature_a')


if __name__ == '__main__':
    unittest.main()
