"""
FilterEngine 单元测试

TDD 流程：先写测试（红），再实现引擎（绿），最后重构。
测试覆盖所有操作符、逻辑组合、NOT 取反、边界情况。
"""

import unittest
import pandas as pd
import numpy as np

from src.data.models import FilterRule, FilterCondition, FilterLogicNode
from src.core.filtering.engine import FilterEngine


class TestFilterEngine(unittest.TestCase):
    """测试过滤引擎的核心功能"""

    def setUp(self):
        """准备测试数据"""
        self.df = pd.DataFrame({
            'age': [18, 25, 30, 45, 60, None, 120],
            'gender': ['M', 'F', 'M', 'F', 'M', 'F', None],
            'score': [500, 600, 700, 800, 900, 550, 650],
            'city': ['北京', '上海', '广州', '北京', '深圳', '上海', '北京'],
            'status': ['active', 'active', 'inactive', 'deleted', 'active', 'inactive', 'active'],
        })
        # 注意：pandas 默认 None 转为 NaN，gender 列因为有 None 会变成 object 类型

    # ========== 空规则场景 ==========

    def test_apply_none_rule(self):
        """None 规则应返回原数据"""
        result = FilterEngine.apply(self.df, None)
        self.assertEqual(len(result), len(self.df))

    def test_apply_disabled_rule(self):
        """禁用规则应返回原数据"""
        rule = FilterRule(enabled=False)
        result = FilterEngine.apply(self.df, rule)
        self.assertEqual(len(result), len(self.df))

    def test_apply_empty_root(self):
        """空根节点应返回原数据"""
        rule = FilterRule(root=None)
        result = FilterEngine.apply(self.df, rule)
        self.assertEqual(len(result), len(self.df))

    # ========== 原子条件：比较操作符 ==========

    def test_apply_eq(self):
        """== 等于"""
        rule = FilterRule(root=FilterCondition('gender', '==', 'M'))
        result = FilterEngine.apply(self.df, rule)
        self.assertEqual(len(result), 3)
        self.assertListEqual(result['gender'].tolist(), ['M', 'M', 'M'])

    def test_apply_ne(self):
        """!= 不等于"""
        rule = FilterRule(root=FilterCondition('status', '!=', 'active'))
        result = FilterEngine.apply(self.df, rule)
        # inactive, deleted, inactive = 3 行
        self.assertEqual(len(result), 3)
        self.assertListEqual(result['status'].tolist(), ['inactive', 'deleted', 'inactive'])

    def test_apply_gt(self):
        """> 大于"""
        rule = FilterRule(root=FilterCondition('age', '>', 30))
        result = FilterEngine.apply(self.df, rule)
        # 注意 NaN 不满足 > 30，所以结果是 45, 60, 120
        self.assertEqual(len(result), 3)
        self.assertListEqual(result['age'].dropna().tolist(), [45.0, 60.0, 120.0])

    def test_apply_ge(self):
        """>= 大于等于"""
        rule = FilterRule(root=FilterCondition('score', '>=', 700))
        result = FilterEngine.apply(self.df, rule)
        self.assertEqual(len(result), 3)
        self.assertListEqual(result['score'].tolist(), [700, 800, 900])

    def test_apply_lt(self):
        """< 小于"""
        rule = FilterRule(root=FilterCondition('age', '<', 30))
        result = FilterEngine.apply(self.df, rule)
        # 18, 25 (NaN 不满足 < 30)
        self.assertEqual(len(result), 2)
        self.assertListEqual(result['age'].dropna().tolist(), [18.0, 25.0])

    def test_apply_le(self):
        """<= 小于等于"""
        rule = FilterRule(root=FilterCondition('score', '<=', 600))
        result = FilterEngine.apply(self.df, rule)
        self.assertEqual(len(result), 3)
        self.assertListEqual(result['score'].tolist(), [500, 600, 550])

    # ========== 集合操作符 ==========

    def test_apply_in(self):
        """in 在列表中"""
        rule = FilterRule(root=FilterCondition('city', 'in', ['北京', '上海']))
        result = FilterEngine.apply(self.df, rule)
        self.assertEqual(len(result), 5)

    def test_apply_not_in(self):
        """not in 不在列表中"""
        rule = FilterRule(root=FilterCondition('city', 'not in', ['北京']))
        result = FilterEngine.apply(self.df, rule)
        self.assertEqual(len(result), 4)
        self.assertNotIn('北京', result['city'].tolist())

    def test_apply_between(self):
        """between 区间（闭区间）"""
        rule = FilterRule(root=FilterCondition('age', 'between', [25, 60]))
        result = FilterEngine.apply(self.df, rule)
        # 25, 30, 45, 60 (NaN 不满足)
        self.assertEqual(len(result), 4)
        ages = result['age'].dropna().tolist()
        self.assertListEqual(ages, [25.0, 30.0, 45.0, 60.0])

    def test_apply_between_invalid_value(self):
        """between 值格式错误应抛出异常"""
        rule = FilterRule(root=FilterCondition('age', 'between', [25]))
        with self.assertRaises(ValueError):
            FilterEngine.apply(self.df, rule)

    # ========== 特殊操作符 ==========

    def test_apply_like(self):
        """like 模糊匹配"""
        rule = FilterRule(root=FilterCondition('city', 'like', '北%'))
        result = FilterEngine.apply(self.df, rule)
        self.assertEqual(len(result), 3)
        self.assertTrue(all(c == '北京' for c in result['city'].tolist()))

    def test_apply_is_null(self):
        """is null 为空"""
        rule = FilterRule(root=FilterCondition('age', 'is null'))
        result = FilterEngine.apply(self.df, rule)
        self.assertEqual(len(result), 1)
        self.assertTrue(pd.isna(result['age'].iloc[0]))

    def test_apply_is_not_null(self):
        """is not null 不为空"""
        rule = FilterRule(root=FilterCondition('gender', 'is not null'))
        result = FilterEngine.apply(self.df, rule)
        self.assertEqual(len(result), 6)

    # ========== NOT 取反 ==========

    def test_apply_negate(self):
        """NOT 取反条件"""
        rule = FilterRule(root=FilterCondition('gender', '==', 'M', negate=True))
        result = FilterEngine.apply(self.df, rule)
        # 不等于 'M' 的行（含 NaN）
        self.assertEqual(len(result), 4)

    def test_apply_negate_null(self):
        """NOT + is null = is not null"""
        rule = FilterRule(root=FilterCondition('age', 'is null', negate=True))
        result = FilterEngine.apply(self.df, rule)
        self.assertEqual(len(result), 6)  # 所有非空 age

    # ========== 逻辑组合 ==========

    def test_apply_and(self):
        """AND 逻辑组合"""
        rule = FilterRule(root=FilterLogicNode(
            operator='AND',
            children=[
                FilterCondition('age', '>', 20),
                FilterCondition('score', '>=', 600),
            ]
        ))
        result = FilterEngine.apply(self.df, rule)
        # age > 20: 25, 30, 45, 60, 120 (NaN 不满足)
        # score >= 600: 600, 700, 800, 900, 650
        # 交集: 25/600, 30/700, 45/800, 60/900, 120/650
        self.assertEqual(len(result), 5)

    def test_apply_or(self):
        """OR 逻辑组合"""
        rule = FilterRule(root=FilterLogicNode(
            operator='OR',
            children=[
                FilterCondition('age', '<', 25),
                FilterCondition('score', '>', 800),
            ]
        ))
        result = FilterEngine.apply(self.df, rule)
        # age < 25: 18
        # score > 800: 900
        # 并集: 18, 900 所在行
        self.assertEqual(len(result), 2)

    def test_apply_empty_and_group(self):
        """空的 AND 组应返回全 True（不过滤）"""
        rule = FilterRule(root=FilterLogicNode(operator='AND', children=[]))
        result = FilterEngine.apply(self.df, rule)
        self.assertEqual(len(result), len(self.df))

    def test_apply_empty_or_group(self):
        """空的 OR 组应返回全 False（过滤全部）"""
        rule = FilterRule(root=FilterLogicNode(operator='OR', children=[]))
        result = FilterEngine.apply(self.df, rule)
        self.assertEqual(len(result), 0)

    # ========== 嵌套逻辑 ==========

    def test_apply_nested_logic(self):
        """嵌套 AND/OR 组合"""
        rule = FilterRule(root=FilterLogicNode(
            operator='AND',
            children=[
                FilterCondition('status', '==', 'active'),
                FilterLogicNode(
                    operator='OR',
                    children=[
                        FilterCondition('age', '<', 30),
                        FilterCondition('score', '>', 800),
                    ]
                ),
            ]
        ))
        result = FilterEngine.apply(self.df, rule)
        # status == active: 第0,1,4,6行
        # OR(age<30, score>800): age<30 是第0行(18)和第1行(25), score>800 是第4行(900)
        # 交集: 第0行(18/active), 第1行(25/active), 第4行(60/active/900)
        self.assertEqual(len(result), 3)
        self.assertListEqual(result['age'].dropna().tolist(), [18.0, 25.0, 60.0])

    # ========== 预览方法 ==========

    def test_preview_no_filter(self):
        """无过滤时预览应返回原数据量"""
        result = FilterEngine.preview(self.df, None)
        self.assertEqual(result.total_samples, 7)
        self.assertEqual(result.filtered_samples, 7)
        self.assertEqual(result.removed_samples, 0)
        self.assertEqual(result.removal_ratio, 0.0)

    def test_preview_with_filter(self):
        """有过滤时预览应返回正确统计"""
        rule = FilterRule(root=FilterCondition('age', '>', 30))
        result = FilterEngine.preview(self.df, rule)
        self.assertEqual(result.total_samples, 7)
        self.assertEqual(result.filtered_samples, 3)
        self.assertEqual(result.removed_samples, 4)
        self.assertAlmostEqual(result.removal_ratio, 4 / 7, places=5)

    def test_preview_empty_result(self):
        """过滤结果为空时的预览"""
        rule = FilterRule(root=FilterCondition('age', '>', 999))
        result = FilterEngine.preview(self.df, rule)
        self.assertEqual(result.total_samples, 7)
        self.assertEqual(result.filtered_samples, 0)
        self.assertEqual(result.removed_samples, 7)
        self.assertAlmostEqual(result.removal_ratio, 1.0, places=5)


if __name__ == '__main__':
    unittest.main()
