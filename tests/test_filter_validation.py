"""
FilterValidator 单元测试

测试过滤规则的合法性校验，覆盖各种错误场景。
"""

import unittest
import pandas as pd

from src.data.models import FilterRule, FilterCondition, FilterLogicNode
from src.core.filtering.validation import FilterValidator
from src.core.filtering.constants import MAX_NESTING_DEPTH


class TestFilterValidation(unittest.TestCase):
    """测试过滤规则校验器"""

    def setUp(self):
        self.df = pd.DataFrame({
            'age': [18, 25, 30],
            'name': ['Alice', 'Bob', 'Charlie'],
            'score': [100, 200, 300],
        })

    # ========== 通过场景 ==========

    def test_validate_none_rule(self):
        """None 规则应直接通过"""
        errors = FilterValidator.validate(None, self.df)
        self.assertEqual(len(errors), 0)

    def test_validate_disabled_rule(self):
        """禁用规则应直接通过"""
        rule = FilterRule(enabled=False)
        errors = FilterValidator.validate(rule, self.df)
        self.assertEqual(len(errors), 0)

    def test_validate_empty_root(self):
        """空根节点应直接通过"""
        rule = FilterRule(root=None)
        errors = FilterValidator.validate(rule, self.df)
        self.assertEqual(len(errors), 0)

    def test_validate_valid_single_condition(self):
        """合法的单条件应通过"""
        rule = FilterRule(root=FilterCondition('age', '>', 18))
        errors = FilterValidator.validate(rule, self.df)
        self.assertEqual(len(errors), 0)

    def test_validate_valid_logic_node(self):
        """合法的逻辑组合应通过"""
        rule = FilterRule(root=FilterLogicNode(
            operator='AND',
            children=[
                FilterCondition('age', '>', 18),
                FilterCondition('score', '<', 300),
            ]
        ))
        errors = FilterValidator.validate(rule, self.df)
        self.assertEqual(len(errors), 0)

    def test_validate_null_without_value(self):
        """is null 不需要值，应通过"""
        rule = FilterRule(root=FilterCondition('age', 'is null'))
        errors = FilterValidator.validate(rule, self.df)
        self.assertEqual(len(errors), 0)

    def test_validate_valid_between(self):
        """合法的 between 应通过"""
        rule = FilterRule(root=FilterCondition('age', 'between', [18, 30]))
        errors = FilterValidator.validate(rule, self.df)
        self.assertEqual(len(errors), 0)

    def test_validate_without_df(self):
        """不传入 df 时，列存在性检查跳过，其他检查仍进行"""
        rule = FilterRule(root=FilterCondition('age', '>', 18))
        errors = FilterValidator.validate(rule, None)
        self.assertEqual(len(errors), 0)

    # ========== 失败场景 ==========

    def test_validate_empty_variable(self):
        """空变量名应失败"""
        rule = FilterRule(root=FilterCondition('', '>', 18))
        errors = FilterValidator.validate(rule, self.df)
        self.assertIn("条件变量名不能为空", errors)

    def test_validate_whitespace_variable(self):
        """空白变量名应失败"""
        rule = FilterRule(root=FilterCondition('   ', '>', 18))
        errors = FilterValidator.validate(rule, self.df)
        self.assertIn("条件变量名不能为空", errors)

    def test_validate_invalid_column(self):
        """数据集中不存在的列应失败"""
        rule = FilterRule(root=FilterCondition('not_exist_col', '>', 18))
        errors = FilterValidator.validate(rule, self.df)
        self.assertIn("变量 'not_exist_col' 不存在于数据集中", errors)

    def test_validate_unsupported_operator(self):
        """不支持的操作符应失败"""
        rule = FilterRule(root=FilterCondition('age', '~~>', 18))
        errors = FilterValidator.validate(rule, self.df)
        self.assertIn("不支持的操作符: '~~>'", errors)

    def test_validate_missing_value(self):
        """需要值但值为空时应失败"""
        rule = FilterRule(root=FilterCondition('age', '>', None))
        errors = FilterValidator.validate(rule, self.df)
        self.assertIn("操作符 '>' 需要提供比较值", errors)

    def test_validate_between_wrong_value_count(self):
        """between 值不是两个时应失败"""
        rule = FilterRule(root=FilterCondition('age', 'between', [18]))
        errors = FilterValidator.validate(rule, self.df)
        self.assertIn("'between' 操作符需要提供包含两个值的列表", errors)

    def test_validate_between_non_list_value(self):
        """between 值不是列表时应失败"""
        rule = FilterRule(root=FilterCondition('age', 'between', 18))
        errors = FilterValidator.validate(rule, self.df)
        self.assertIn("'between' 操作符需要提供包含两个值的列表", errors)

    def test_validate_unknown_logic_operator(self):
        """未知逻辑操作符应失败"""
        rule = FilterRule(root=FilterLogicNode(
            operator='XOR',
            children=[FilterCondition('age', '>', 18)]
        ))
        errors = FilterValidator.validate(rule, self.df)
        self.assertIn("未知的逻辑操作符: 'XOR'", errors)

    def test_validate_empty_logic_group(self):
        """空逻辑组应产生警告"""
        rule = FilterRule(root=FilterLogicNode(operator='AND', children=[]))
        errors = FilterValidator.validate(rule, self.df)
        self.assertIn("AND 逻辑组不能为空", errors)

    def test_validate_max_nesting_depth(self):
        """超过最大嵌套深度应失败"""
        # 构造超过 MAX_NESTING_DEPTH 的嵌套
        root = FilterLogicNode(operator='AND', children=[])
        current = root
        for _ in range(MAX_NESTING_DEPTH + 1):
            child = FilterLogicNode(operator='AND', children=[])
            current.children.append(child)
            current = child

        rule = FilterRule(root=root)
        errors = FilterValidator.validate(rule, self.df)
        self.assertTrue(
            any("嵌套深度超过最大限制" in e for e in errors),
            f"期望包含嵌套深度错误，实际错误: {errors}"
        )

    def test_validate_multiple_errors(self):
        """多条错误应全部返回"""
        rule = FilterRule(root=FilterLogicNode(
            operator='AND',
            children=[
                FilterCondition('', '>', 18),
                FilterCondition('not_exist', '>', None),
            ]
        ))
        errors = FilterValidator.validate(rule, self.df)
        self.assertGreaterEqual(len(errors), 2)
        self.assertIn("条件变量名不能为空", errors)
        # 变量不存在的条件会在变量名校验后返回，不检查操作符和值
        self.assertIn("变量 'not_exist' 不存在于数据集中", errors)


if __name__ == '__main__':
    unittest.main()
