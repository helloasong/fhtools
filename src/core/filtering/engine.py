"""
过滤规则执行引擎

负责将 FilterRule 转换为 pandas boolean mask 并应用到 DataFrame。
所有操作均为向量化，不逐行迭代。
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd

from src.data.models import FilterRule, FilterCondition, FilterLogicNode, FilterNode


@dataclass
class FilterPreviewResult:
    """过滤预览结果"""
    total_samples: int
    filtered_samples: int
    removed_samples: int
    removal_ratio: float


class FilterEngine:
    """过滤规则执行引擎"""

    @staticmethod
    def apply(df: pd.DataFrame, rule: Optional[FilterRule]) -> pd.DataFrame:
        """对 DataFrame 应用过滤规则

        Args:
            df: 原始数据
            rule: 过滤规则，为 None 或 disabled 时返回原数据

        Returns:
            过滤后的 DataFrame 子集
        """
        if rule is None or not rule.enabled or rule.root is None:
            return df.copy()

        mask = FilterEngine._eval_node(df, rule.root)
        return df[mask].copy()

    @staticmethod
    def preview(df: pd.DataFrame, rule: Optional[FilterRule]) -> FilterPreviewResult:
        """计算过滤规则的预览统计信息

        Args:
            df: 原始数据
            rule: 过滤规则

        Returns:
            FilterPreviewResult 包含过滤前后样本数等信息
        """
        total = len(df)

        if rule is None or not rule.enabled or rule.root is None:
            return FilterPreviewResult(
                total_samples=total,
                filtered_samples=total,
                removed_samples=0,
                removal_ratio=0.0
            )

        mask = FilterEngine._eval_node(df, rule.root)
        filtered = int(mask.sum())
        removed = total - filtered

        return FilterPreviewResult(
            total_samples=total,
            filtered_samples=filtered,
            removed_samples=removed,
            removal_ratio=removed / total if total > 0 else 0.0
        )

    # ============= 私有递归求值方法 =============

    @staticmethod
    def _eval_node(df: pd.DataFrame, node: FilterNode) -> pd.Series:
        """递归计算规则节点的布尔掩码 Series"""
        if isinstance(node, FilterCondition):
            mask = FilterEngine._eval_condition(df, node)
        elif isinstance(node, FilterLogicNode):
            mask = FilterEngine._eval_logic(df, node)
        else:
            raise TypeError(f"Unknown filter node type: {type(node)}")

        return mask

    @staticmethod
    def _eval_condition(df: pd.DataFrame, cond: FilterCondition) -> pd.Series:
        """计算原子条件的布尔掩码"""
        col = df[cond.variable]
        op = cond.operator
        val = cond.value

        # 根据操作符计算基础掩码
        if op == '==':
            mask = col == val
        elif op == '!=':
            mask = col != val
        elif op == '>':
            mask = col > val
        elif op == '>=':
            mask = col >= val
        elif op == '<':
            mask = col < val
        elif op == '<=':
            mask = col <= val
        elif op == 'in':
            mask = col.isin(val if isinstance(val, list) else [val])
        elif op == 'not in':
            mask = ~col.isin(val if isinstance(val, list) else [val])
        elif op == 'between':
            if isinstance(val, (list, tuple)) and len(val) == 2:
                mask = (col >= val[0]) & (col <= val[1])
            else:
                raise ValueError(f"'between' requires a list/tuple of 2 values, got {val}")
        elif op == 'like':
            pattern = str(val).replace('%', '.*')
            mask = col.astype(str).str.contains(pattern, regex=True, na=False)
        elif op == 'is null':
            mask = col.isna()
        elif op == 'is not null':
            mask = col.notna()
        else:
            raise ValueError(f"Unsupported operator: {op}")

        # 应用 NOT 取反
        if cond.negate:
            mask = ~mask

        return mask

    @staticmethod
    def _eval_logic(df: pd.DataFrame, node: FilterLogicNode) -> pd.Series:
        """计算逻辑组合节点的布尔掩码"""
        if not node.children:
            # 空逻辑组：AND 返回全 True，OR 返回全 False
            if node.operator == 'AND':
                return pd.Series(True, index=df.index)
            else:
                return pd.Series(False, index=df.index)

        masks = [FilterEngine._eval_node(df, child) for child in node.children]

        if node.operator == 'AND':
            result = masks[0]
            for m in masks[1:]:
                result = result & m
            return result
        elif node.operator == 'OR':
            result = masks[0]
            for m in masks[1:]:
                result = result | m
            return result
        else:
            raise ValueError(f"Unknown logic operator: {node.operator}")
