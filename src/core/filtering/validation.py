"""
过滤规则合法性校验器

在保存/执行规则前进行完整性校验，避免运行时错误。
"""

from typing import List, Optional, Set
import pandas as pd

from src.data.models import FilterRule, FilterCondition, FilterLogicNode, FilterNode
from src.core.filtering.constants import SUPPORTED_OPERATORS, MAX_NESTING_DEPTH


class FilterValidationError(Exception):
    """规则校验错误"""
    pass


class FilterValidator:
    """过滤规则合法性校验器"""

    @staticmethod
    def validate(rule: Optional[FilterRule], df: Optional[pd.DataFrame] = None) -> List[str]:
        """校验规则合法性

        Args:
            rule: 待校验的过滤规则
            df: 可选的数据集，用于校验变量名是否存在

        Returns:
            错误信息列表，为空表示校验通过
        """
        errors = []

        if rule is None or not rule.enabled or rule.root is None:
            return errors  # 空规则无需校验

        seen_vars: Set[str] = set()
        FilterValidator._validate_node(rule.root, df, errors, seen_vars, depth=0)

        return errors

    @staticmethod
    def _validate_node(
        node: FilterNode,
        df: Optional[pd.DataFrame],
        errors: List[str],
        seen_vars: Set[str],
        depth: int
    ) -> None:
        """递归校验节点"""
        if depth > MAX_NESTING_DEPTH:
            errors.append(f"规则嵌套深度超过最大限制 {MAX_NESTING_DEPTH}")
            return

        if isinstance(node, FilterCondition):
            FilterValidator._validate_condition(node, df, errors, seen_vars)
        elif isinstance(node, FilterLogicNode):
            FilterValidator._validate_logic(node, df, errors, seen_vars, depth)

    @staticmethod
    def _validate_condition(
        cond: FilterCondition,
        df: Optional[pd.DataFrame],
        errors: List[str],
        seen_vars: Set[str]
    ) -> None:
        """校验原子条件"""
        # 校验变量名
        if not cond.variable or not cond.variable.strip():
            errors.append("条件变量名不能为空")
            return

        if df is not None and cond.variable not in df.columns:
            errors.append(f"变量 '{cond.variable}' 不存在于数据集中")
            return

        seen_vars.add(cond.variable)

        # 校验操作符
        if cond.operator not in SUPPORTED_OPERATORS:
            errors.append(f"不支持的操作符: '{cond.operator}'")
            return

        # 校验值（is null / is not null 不需要值）
        if cond.operator in ('is null', 'is not null'):
            return

        if cond.value is None:
            errors.append(f"操作符 '{cond.operator}' 需要提供比较值")
            return

        # 校验 between 需要两个值
        if cond.operator == 'between':
            if not isinstance(cond.value, (list, tuple)) or len(cond.value) != 2:
                errors.append("'between' 操作符需要提供包含两个值的列表")

    @staticmethod
    def _validate_logic(
        node: FilterLogicNode,
        df: Optional[pd.DataFrame],
        errors: List[str],
        seen_vars: Set[str],
        depth: int
    ) -> None:
        """校验逻辑节点"""
        if node.operator not in ('AND', 'OR'):
            errors.append(f"未知的逻辑操作符: '{node.operator}'")

        if not node.children:
            errors.append(f"{node.operator} 逻辑组不能为空")

        for child in node.children:
            FilterValidator._validate_node(child, df, errors, seen_vars, depth + 1)
